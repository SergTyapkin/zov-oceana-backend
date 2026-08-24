import json
import math
import threading
import time
from flask import Blueprint
import requests
import urllib3

from src.TgBot.TgBot import TgBot, TgBotMessageTexts
from src.database.databaseUtils import insertHistory
from src.config import CONFIG
from src.blueprints.goods import prepareGoodsData
from src.utils.access import *
from src.utils.utils import *

from src.database.SQLRequests import orders as SQLOrders

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Blueprint('payments', __name__)

class PaymentResponse:
    # Default fields for all responses types
    success: bool
    errorCode: str
    message: str | None
    details: str | None
    id: str | None
    orderId: str | None
    
    # Special responses types fields
    status: PaymentStatuses | None # Init, Cancel, Confirm, GetState
    paymentUrl: str | None         # Init
    amount: int | None             # Init, Cancel, Confirm, GetState (если присылалась в запросе)
    # RebillId: str | None         # Confirm, Cancel
    # CardId: str | None           # Confirm, Cancel
    qrData: str | None             # GetQR
    route: str | None              # GetState
    source: str | None             # GetState
    
    def __init__(self, response):
        data = response.json()
        print("> PAYMENT RESPONSE FROM TINKOFF:", data)
        
        self.success = data['Success']
        self.errorCode = data['ErrorCode']
        self.message = data.get('Message') # В случае ошибки
        self.details = data.get('Details') # В случае ошибки
        self.id = data.get('PaymentId') # в случае успеха
        self.orderId = data.get('OrderId', '').split('_')[0] # в случае успеха
        
        # Special responses types fields
        self.status = data.get('Status')
        self.paymentUrl = data.get('PaymentURL')
        self.amount = data.get('Amount')
        self.qrData = data.get('Data')
        
        self.route = None
        self.source = None
        params: list[dict[str, str]] = data.get('Params')
        if params:
            for param in params: # Проходимся по списку параметров
                # Если находим нужный Key, записываем себе его Value
                if param['Key'] == 'Route':
                    self.route = param['Value']
                elif param['Key'] == 'Source':
                    self.source = param['Value']
        

def getOrderGoods(orderData):
    orderGoods = DB.execute(SQLOrders.selectOrderGoodsByOrderId, [orderData['id']], manyResults=True)
    for goods in orderGoods:
        prepareGoodsData(goods, False, False)
    return orderGoods

def generateToken(params):
    tokenParams = []
    for key, value in params.items():
        # Если вдруг токен уже есть - пропускаем его
        if key == 'Token':
            continue
        # Исключаем ВСЕ вложенные объекты (DATA, Receipt и т.д.)
        if isinstance(value, (dict, list)):
            continue
        if value is not None:
            tokenParams.append({key: str(value)})
    
    # Добавляем пароль, сортируем и склеиваем в строку
    tokenParams.append({"Password": CONFIG.tbank.terminal_password})
    tokenParams.sort(key=lambda x: list(x.keys())[0].lower())
    token_string = ''.join(list(param.values())[0] for param in tokenParams)
    
    return hash_sha256(token_string)

def sendPaymentRequest(url, params) -> PaymentResponse:
    params['Token'] = generateToken(params)
    print(f">> Send request to: {url}, params: {params}")
    
    try:
        # Отпрвляем POST запрос на заданный url с заданным телом
        response = requests.post(
            url,
            json=params,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            verify=False,  # Отключаем проверку SSL сертификата
        )
        
        # Логируем ответ
        try:
            print(f"<<< Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"<<< Raw response: {response.text}")
        
        # Проверяем статус
        if response.status_code != 200:
            raise Exception(f"Ошибка HTTP: {response.status_code}")
        
        # Проверяем успешность
        res = PaymentResponse(response)
        if not res.success:
            raise Exception(f"Ошибка Tinkoff: {res.message}; {res.details} (Код: {res.errorCode})")
        
        # Если всё в порядке - возвращаем структуру с данными
        return res
    except requests.exceptions.Timeout as err:
        raise Exception(f"Превышено время ожидания ответа от Tinkoff: {str(err)}")
    except requests.exceptions.RequestException as err:
        raise Exception(f"Ошибка запроса к Tinkoff: {str(err)}")
    except json.JSONDecodeError as err:
        raise Exception(f"Ошибка парсинга ответа Tinkoff: {str(err)}")

def getPaymentStateUsingRequest(paymentId) -> PaymentStatuses:    
    return sendPaymentRequest(
        CONFIG.tbank.get_state_url, 
        {
            'TerminalKey': CONFIG.tbank.terminal_key,
            'PaymentId': paymentId,
        },
    )

def processChangingPaymentStatus(status: PaymentStatuses, order, user):
    # Оплата заказа создана
    if status == PaymentStatuses.NEW:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.new, order['id']])
        print(f"Прилетело измнение статуса оплаты на 'NEW': order #{order['id']}, paymentId: {order['paymentid']}, status: {status}")
    # Деньги для оплаты зарезервированы (только для двухстадийной оплаты)
    elif status == PaymentStatuses.AUTHORIZED:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.authorized, order['id']])
        TgBot.sendMessage(user['tgid'], TgBotMessageTexts.orderPaymentAuthorized, order["number"])
    # Деньги у клиента списаны
    elif status == PaymentStatuses.CONFIRMED:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.confirmed, order['id']])
        TgBot.sendMessage(user['tgid'], TgBotMessageTexts.orderPaymentConfirmed, order["number"])
    # Ошибка при оплате
    elif status == PaymentStatuses.REJECTED:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.rejected, order['id']])
        TgBot.sendMessage(user['tgid'], TgBotMessageTexts.orderPaymentRejected, order["number"], order["id"])
    # Клиент не успел завершить оплату в срок
    elif status == PaymentStatuses.DEADLINE_EXPIRED:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.expired, order['id']])
        TgBot.sendMessage(user['tgid'], TgBotMessageTexts.orderPaymentExpired, order["number"], order["id"])
    # Заказ не подтвержден после AUTHORIZED и оплата не списана (для двухстадийной оплаты) или заказ отменен до авторизации, после INIT (для любого типа оплаты)
    elif status == PaymentStatuses.REVERSED or status == PaymentStatuses.PARTIAL_REVERSED or status == PaymentStatuses.CANCELLED:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.cancelled, order['id']])
        TgBot.sendMessage(user['tgid'], TgBotMessageTexts.orderPaymentCancelled, order["number"])
    # Возврат по заказу успешно произведен
    elif status == PaymentStatuses.REFUNDED or status == PaymentStatuses.PARTIAL_REFUNDED:
        DB.execute(SQLOrders.updateOrderPaymentStatusById, [OrderPaymentStatuses.refunded, order['id']])
        TgBot.sendMessage(user['tgid'], TgBotMessageTexts.orderRefunded, order["number"])


class OrderPollingThreadData:
    thread: threading.Thread
    awaitingForStatuses: list[PaymentStatuses] | None
    stop_flag: threading.Event
    def __init__(self, thread, awaitingForStatuses, stop_flag):
        self.thread = thread
        self.awaitingForStatuses = awaitingForStatuses
        self.stop_flag = stop_flag

ordersPollingThreads: dict[str, OrderPollingThreadData] = {}
def startPollingForPayment(order, user, awaitingForStatuses: list[PaymentStatuses] = None):
    # Если тред для этого заказа уже есть, убиваем его
    existingThread = ordersPollingThreads.get(order['id'])
    if existingThread is not None:
        existingThread.stop_flag.set()  # Устанавливаем флаг остановки
        # existingThread.thread.join()  # Ждем завершения
        del ordersPollingThreads[order['id']]  # Удаляем из словаря
        
    initialStatus = order['paymentstatus']
    
    def poll():
        # Проверяем флаг завершения
        if stop_flag.is_set():
            return False
        
        try:
            payment = getPaymentStateUsingRequest(order['paymentid'])
        except Exception as err:
            print(f"Ошибка при поллинге статуса оплаты #{order['paymentid']} заказа #{order['id']}:", err);
            return False
        
        # Если поменялись Route или Source - сохраняем их в базе
        if order['paymentroute'] != payment.route or order['paymentsource'] != payment.source:
            DB.execute(SQLOrders.updateOrderPaymentRouteSourceById, [payment.route, payment.source, order['id']])
        
        # Если статус не поменялся - выходим
        if payment.status == initialStatus:
            return False
        
        # Если поменялся - проверяем что на один из ожидаемых
        if payment.status not in awaitingForStatuses and awaitingForStatuses is not None:
            print(f"Ошибка: При поллинге статуса оплаты #{order['paymentid']} заказа #{order['id']}, он изменился на {payment.status}, хотя ожидался один из:", awaitingForStatuses);
            return False
        
        # Если изменился на один из ожидаемых - обрабатываем изменение
        print(f"✅ Cтатус оплаты #{order['paymentid']} заказа #{order['id']} изменился на {payment.status}");
        processChangingPaymentStatus(payment.status, order, user)
        return True
    
    def startPollingCycle():
        attempts = 0
        maxAttemts = math.ceil(CONFIG.tbank.max_order_pay_time_sec / CONFIG.tbank.payments_polling_interval_sec)
        while attempts < maxAttemts:
            if stop_flag.is_set():
                print(f"⏹️ Поллинг для платежа #{order['paymentid']} заказа #{order['id']} принудительно остановлен")
                return
            
            if poll():  # Заканчиваем, если мы дождались смены статуса на один из нужных 
                return
            time.sleep(CONFIG.tbank.payments_polling_interval_sec)
            attempts += 1

    stop_flag = threading.Event()
    thread = threading.Thread(target=startPollingCycle, daemon=True)
    thread.start()
    # Сохраняем тред для возможности его отмены
    ordersPollingThreads[order['id']] = OrderPollingThreadData(thread, awaitingForStatuses, stop_flag)
    print(f"♻🚀 Started polling for payment #{order['paymentid']} order #{order['id']}")


# Инициализация платежа при любом типе оплаты (и одно, и двух-стадийной)
@app.route("", methods=["POST"])
@login_required
def createPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # 0. Получаем данные заказа
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if str(order['userid']) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на просмотр заказов другого пользователя", HTTP_NO_PERMISSIONS)

    # 1. Рассчитываем сумму в копейках
    order_goods = getOrderGoods(order)
    total_cost = 0
    for goods in order_goods:
        price = int(goods['cost'] * 100)  # Переводим в копейки
        amount = goods.get('amount', 1)
        total_cost += int(price * amount) # Целое число копеек

    # 2. Формируем параметры запроса
    params = {
        'TerminalKey': CONFIG.tbank.terminal_key,
        'Amount': round(total_cost),
        'OrderId': f'{order["id"]}_{time.ctime().replace(" ", "-")}', # Добвляем к id заказа текущее время после _. В ответах от тинькоффа мы отрезаем время и получаем чистое id
        'Description': f"Оплата заказа №{order['number']} на сайте {CONFIG.deploy_short_url}",
        'CustomerKey': str(userData['id']),
        'Language': 'ru',
        'PayType': 'T' if CONFIG.tbank.use_two_stage_payments else 'O',  # O - одностадийная оплата, 'T' - двухстадийная
        'DATA': {
            "Id": userData.get('id', ''),
            "FamilyName": userData.get('familyname', ''),
            "GivenName": userData.get('givenname', ''),
            "MiddleName": userData.get('middlename', ''),
            "Email": userData.get('email', ''),
            "Phone": userData.get('tel', '')
        }
    }

    # 3. Добавляем чек
    items = []
    for goods in order_goods:
        price = int(goods['cost'] * 100)
        quantity = goods.get('amount', 1)
        amount = int(price * quantity)  # целое число копеек
        items.append({
            'Name': goods['title'][:128],
            'Price': price,
            'Quantity': quantity,
            'Amount': amount,
            'Tax': CONFIG.goods_tax_delicates if goods['isdelicates'] else CONFIG.goods_tax_default,  # Обычная НДС для всех товаров и 22% для деликатесов
            'PaymentMethod': 'full_payment',  # Полная оплата (не частичная и не кредит)
            'PaymentObject': 'commodity' # Говорим что продаем товар, а не услугу и др
        })

    if items:
        params['Receipt'] = {
            'Items': items,
            'Taxation': CONFIG.company_taxation_type,  # УСН доходы
            'Email': userData.get('email', ''),
            'Phone': userData.get('tel', '')
        }

    # 5. Отправляем запрос для создания оплаты в Т-Банк
    try:
        res = sendPaymentRequest(CONFIG.tbank.init_url, params)
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)
        
    # Проверяем статус оплаты
    if res.status != PaymentStatuses.NEW:
        return jsonResponse(f"Ошибка создания платежа: статус созданного платежа не NEW, а {res.status}", HTTP_INTERNAL_ERROR)
    
    # > Кидаем запрос для получения ссылки для отображения QR
    try:
        qrRes = sendPaymentRequest(
            CONFIG.tbank.get_qr_url,
            {
                'TerminalKey': CONFIG.tbank.terminal_key,
                'PaymentId': res.id,
                'DataType': 'PAYLOAD',  # или "IMAGE" для SVG
            },
        )
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)
    
    # Обновляем статус оплаты заказа
    try:
        orderData = DB.execute(SQLOrders.updateOrderPaymentIdUrlStatusQrdataById, [res.id, res.paymentUrl, OrderPaymentStatuses.new, qrRes.qrData, res.orderId])
    except:
        return jsonResponse("По id заказа в ответе от тинькоффа заказ в базе не найден", HTTP_INTERNAL_ERROR)
    
    insertHistory(
        userData['id'],
        'payment',
        f'Creates payment for order #{orderId}, paymentId: {res.id}, status: {res.status}, success: {res.success}'
    )
    
    # 6. Запускаем поллинг для того, чтобы узнать когда пройдет оплата, если вебхук не сработает
    startPollingForPayment(
        orderData,
        userData,
        [
            PaymentStatuses.AUTHORIZED,
            PaymentStatuses.CONFIRMED,
            PaymentStatuses.REJECTED,
            PaymentStatuses.CANCELLED,
            PaymentStatuses.DEADLINE_EXPIRED,
        ]
    )
        
    # 7. Возвращаем фронту данные заказа и в них url и qr для оплаты
    return jsonResponse(orderData)


# Админское подтверждение или отмена списания оплаты при двухстадийных платежах
def confirmOrCancelPayment(userData, orderId, amount: int = None, isCancel=False):
    # 0. Получаем данные заказа
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if order['paymentid'] is None:
        return jsonResponse("Оплата для заказа ещё не была создана", HTTP_INTERNAL_ERROR)
    if not isCancel and order['paymentstatus'] != OrderPaymentStatuses.authorized:
        return jsonResponse("Платёж ещё не был авторизован (средства клиента ещё не заморожены)", HTTP_DATA_CONFLICT)
        

    # 1. Формируем параметры запроса
    params = {
        'TerminalKey': CONFIG.tbank.terminal_key,
        'PaymentId': order['paymentid'],
    }
    if not isCancel: # Добавляем в Confirm поля route и source, если они есть в базе
        if order['paymentroute'] is not None:
            params['Route'] = order['paymentroute']
        if order['paymentsource'] is not None:
            params['Source'] = order['paymentsource']
    if amount is not None:
        params['Amount'] = amount

    # 2. Отправляем запрос в Т-Банк
    try:
        res = sendPaymentRequest(
            CONFIG.tbank.cancel_url if isCancel else CONFIG.tbank.confirm_url, 
            params,
        )
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    # Проверяем статус оплаты в ответе
    if isCancel:
        if order['paymentstatus'] == OrderPaymentStatuses.authorized:
            targetStatus = PaymentStatuses.REVERSED
        elif order['paymentstatus'] == OrderPaymentStatuses.confirmed:
            targetStatus = PaymentStatuses.REFUNDED
        elif order['paymentstatus'] == OrderPaymentStatuses.new:
            targetStatus = PaymentStatuses.CANCELLED
        else:
            return jsonResponse("Попытка вернуть платёж в состоянии не AUTHORIZED / CONFIRMED / NEW", HTTP_INTERNAL_ERROR)
    else:
        targetStatus = PaymentStatuses.CONFIRMED
    if res.status != targetStatus:
        return jsonResponse(f"Ошибка создания платежа: статус платежа на стороне тинькофф не {targetStatus}, а {res.status}", HTTP_INTERNAL_ERROR)
    
    insertHistory(
        userData['id'],
        'payment',
        f'{'Cancel' if isCancel else 'Confirm'} payment for order #{orderId}, paymentId: {res.id}, status: {res.status}, success: {res.success}'
    )
    
    # 3. Запускаем поллинг для того, чтобы узнать когда пройдет оплата, если вебхук не сработает
    startPollingForPayment(
        order,
        userData,
        [
            PaymentStatuses.CANCELLED, # из NEW
            PaymentStatuses.REVERSED, # из AUTHORIZED
            PaymentStatuses.PARTIAL_REVERSED, # из AUTHORIZED
            PaymentStatuses.REFUNDED, # из CONFIRMED
            PaymentStatuses.PARTIAL_REFUNDED, # из CONFIRMED
        ]  if isCancel else [
            PaymentStatuses.CONFIRMED,
        ],
    )
    
    # 4. Отвечаем что всё ок
    return jsonResponse(f"Оплата {'отменена' if isCancel else 'подтверждена'}")

@app.route("/confirm", methods=["POST"])
@login_and_can_edit_orders_required
def confirmPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
        amount = req.get('amount')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    return confirmOrCancelPayment(userData, orderId, amount, False)

@app.route("/cancel", methods=["POST"])
@login_and_can_edit_orders_required
def cancelPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
        amount = req.get('amount')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # Если тред для этого заказа уже есть, убиваем его
    existingThread = ordersPollingThreads.get(orderId)
    if existingThread is not None:
        existingThread.stop_flag.set()  # Устанавливаем флаг остановки
        # existingThread.thread.join()  # Ждем завершения
        del ordersPollingThreads[orderId]  # Удаляем из словаря
    
    return confirmOrCancelPayment(userData, orderId, amount, True)


@app.route("", methods=["GET"])
@login_required
def getPaymentState(userData):
    try:
        req = request.args
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удаgлось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # 0. Получаем данные заказа
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if order['paymentid'] is None:
        return jsonResponse("Оплата для заказа ещё не была создана", HTTP_INTERNAL_ERROR)
    
    # 1. Получаем данные пользователя и проверяем права
    user = DB.execute(SQLUser.selectUserById, [order['userid']])
    if not user:
        return jsonResponse("Владелец зказа не найден", HTTP_NOT_FOUND)
    if user['id'] != userData['id'] and not userData['caneditorders']:
        return jsonResponse("Нет прав для просмотра статуса оплаты другого пользователя", HTTP_NO_PERMISSIONS)
    
    # 2. Отправляем запрос в Т-Банк
    try:
        return getPaymentStateUsingRequest(order['paymentid'])
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)


@app.route("/webhook", methods=["POST"])
def paymentsWebhook():
    try:
        req = request.json
        paymentId = req['PaymentId']
        orderId = req['OrderId']
        status = req['Status']
        token = req['Token']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # 1. Проверяем токен
    myToken = generateToken(req)
    if myToken != token:
        print("ОШИБКА ВЕБХУКА: ТОКЕНЫ В ВЕБХУКЕ НЕ СОВПАДАЮТ")
        return jsonResponse("Токен не прошёл проверку", HTTP_NO_PERMISSIONS)
    
    # 2. Доверяем данным. Получаем информацию о заказе
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    
    # 3. Завершаем потоки поллинга, если таковые были и ждали именно этот статус
    if status != order['paymentstatus']:
        existingThread = ordersPollingThreads.get(order['id'])
        if existingThread is not None and \
            status in existingThread.awaitingForStatuses and \
            existingThread.awaitingForStatuses is not None:
                existingThread.stop_flag.set()  # Устанавливаем флаг остановки
                # existingThread.thread.join()  # Ждем завершения
                del ordersPollingThreads[order['id']]  # Удаляем из словаря
    
    # 4. Получаем информацию о владельце заказа
    user = DB.execute(SQLUser.selectUserById, [order['userid']])
    if not user:
        return jsonResponse("Владелец заказа не найден", HTTP_NOT_FOUND)

    insertHistory(
        user['id'],
        'payment',
        f'Webhook update order: #{orderId}, paymentId: {paymentId}, status: {status}'
    )
    
    # 4. Обновляем статус заказа
    # Если статус в базе уже такой, то пропускаем обработку смены статуса
    if status == order['paymentstatus']:
        return make_response("OK", HTTP_OK)
    processChangingPaymentStatus(status, order, user)
    
    return make_response("OK", HTTP_OK)
