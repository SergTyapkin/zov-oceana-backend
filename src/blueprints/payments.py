from flask import Blueprint

from src.TgBot.TgBot import TgBot, TgBotMessageTexts
from src.database.databaseUtils import insertHistory
from src.blueprints.orders import getOrderGoods, getOrderTotalCostX100
from src.utils.access import *
from src.utils.utils import *

from src.payments.types import PaymentStatuses
from src.payments.polling import startPollingForPayment
from src.payments.requests import addCard, getCardsList, getPaymentQRHref, initPayment
from src.payments.webhook import paymentsWebhook

from src.database.SQLRequests import orders as SQLOrders

app = Blueprint('payments', __name__)


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


# Инициализация платежа при любом типе оплаты (и одно, и двух-стадийной)
@app.route("", methods=["POST"])
@login_required
def createPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # Получаем данные заказа и юзера
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if str(order['userid']) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на создание оплаты заказа другого пользователя", HTTP_NO_PERMISSIONS)
    
    user = DB.execute(SQLUser.selectUserById, [order['userid']])

    # Отправляем запросы в банк
    try:
        payment = initPayment(
            getOrderTotalCostX100(order),
            order, user, 
            getOrderGoods(order)
        )
            
        # Проверяем статус оплаты
        if payment.status != PaymentStatuses.NEW:
            return jsonResponse(f"Ошибка создания платежа: статус созданного платежа не NEW, а {res.status}", HTTP_INTERNAL_ERROR)
        
        # Кидаем запрос для получения ссылки для отображения QR
        qrResponse = getPaymentQRHref(payment.id)
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)
    
    # Обновляем статус оплаты заказа
    try:
        order = DB.execute(SQLOrders.updateOrderPaymentIdUrlStatusQrdataById, [payment.id, payment.paymentUrl, OrderPaymentStatuses.new, qrResponse.qrData, payment.orderId])
    except:
        return jsonResponse("По id заказа в ответе от тинькоффа заказ в базе не найден", HTTP_INTERNAL_ERROR)
    
    insertHistory(
        user['id'],
        'payment',
        f'Created payment for order #{orderId}, paymentId: {payment.id}, status: {payment.status}, success: {payment.success}'
    )
    
    # Запускаем поллинг для того, чтобы узнать когда пройдет оплата, если вебхук не сработает
    startPollingForPayment(
        order,
        user,
        lambda payment: DB.execute(SQLOrders.updateOrderPaymentRouteSourceById, [payment.route, payment.source, order['id']]),
        processChangingPaymentStatus,
        [
            PaymentStatuses.AUTHORIZED,
            PaymentStatuses.CONFIRMED,
            PaymentStatuses.REJECTED,
            PaymentStatuses.CANCELLED,
            PaymentStatuses.DEADLINE_EXPIRED,
        ]
    )
        
    # Возвращаем фронту данные заказа и в них url и qr для оплаты
    return jsonResponse(order)


@app.route("/confirm", methods=["POST"])
@login_and_can_edit_orders_required
def confirmPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
        amount = req.get('amount')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # 0. Получаем данные заказа
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if order['paymentid'] is None:
        return jsonResponse("Оплата для заказа ещё не была создана", HTTP_INTERNAL_ERROR)
    if order['paymentstatus'] != OrderPaymentStatuses.authorized:
        return jsonResponse("Платёж ещё не был авторизован (средства клиента ещё не заморожены)", HTTP_DATA_CONFLICT)
        
    # Отправляем запрос в банк
    try:
        payment = confirmPayment(order['paymentid'], order, amount)
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    # Проверяем статус оплаты в ответе
    if payment.status != PaymentStatuses.CONFIRMED:
        return jsonResponse(f"Ошибка создания платежа: статус платежа на стороне тинькофф не {PaymentStatuses.CONFIRMED}, а {payment.status}", HTTP_INTERNAL_ERROR)
    
    insertHistory(
        userData['id'],
        'payment',
        f'Confirm payment for order #{orderId}, paymentId: {payment.id}, status: {payment.status}, success: {payment.success}'
    )
    
    # Запускаем поллинг для того, чтобы узнать когда пройдет оплата, если вебхук не сработает
    startPollingForPayment(
        order,
        userData,
        [
            PaymentStatuses.CANCELLED, # из NEW
            PaymentStatuses.REVERSED, # из AUTHORIZED
            PaymentStatuses.PARTIAL_REVERSED, # из AUTHORIZED
            PaymentStatuses.REFUNDED, # из CONFIRMED
            PaymentStatuses.PARTIAL_REFUNDED, # из CONFIRMED
        ],
    )
    
    # Отвечаем что всё ок
    return jsonResponse(f"Оплата подтверждена")

@app.route("/cancel", methods=["POST"])
@login_and_can_edit_orders_required
def cancelPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
        amount = req.get('amount')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
    # 0. Получаем данные заказа
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if order['paymentid'] is None:
        return jsonResponse("Оплата для заказа ещё не была создана", HTTP_INTERNAL_ERROR)
    if order['paymentstatus'] != OrderPaymentStatuses.authorized:
        return jsonResponse("Платёж ещё не был авторизован (средства клиента ещё не заморожены)", HTTP_DATA_CONFLICT)
        
    # Отправляем запрос в банк
    try:
        payment = confirmPayment(order['paymentid'], order, amount)
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    # Проверяем статус оплаты в ответе
    if payment.status != PaymentStatuses.CONFIRMED:
        return jsonResponse(f"Ошибка создания платежа: статус платежа на стороне тинькофф не {PaymentStatuses.CONFIRMED}, а {payment.status}", HTTP_INTERNAL_ERROR)
    
    insertHistory(
        userData['id'],
        'payment',
        f'Confirm payment for order #{orderId}, paymentId: {payment.id}, status: {payment.status}, success: {payment.success}'
    )
    
    # Запускаем поллинг для того, чтобы узнать когда пройдет оплата, если вебхук не сработает
    startPollingForPayment(
        order,
        userData,
        [PaymentStatuses.CONFIRMED],
    )
    
    # Отвечаем что всё ок
    return jsonResponse(f"Оплата подтверждена")

@app.route("/cancel", methods=["POST"])
@login_and_can_edit_orders_required
def cancelPayment(userData):
    try:
        req = request.json
        orderId = req['orderId']
        amount = req.get('amount')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    # 0. Получаем данные заказа
    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if order['paymentid'] is None:
        return jsonResponse("Оплата для заказа ещё не была создана", HTTP_INTERNAL_ERROR)
        
    # Отправляем запрос в банк
    try:
        payment = cancelPayment(order['paymentid'], amount)
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    # Проверяем статус оплаты в ответе
    if order['paymentstatus'] == OrderPaymentStatuses.authorized:
        targetStatus = PaymentStatuses.REVERSED
    elif order['paymentstatus'] == OrderPaymentStatuses.confirmed:
        targetStatus = PaymentStatuses.REFUNDED
    elif order['paymentstatus'] == OrderPaymentStatuses.new:
        targetStatus = PaymentStatuses.CANCELLED
    else:
        return jsonResponse(f"Попытка вернуть платёж в состоянии не AUTHORIZED / CONFIRMED / NEW, а {order['paymentstatus']}", HTTP_INTERNAL_ERROR)
    if payment.status != targetStatus:
        return jsonResponse(f"Ошибка отмены платежа: статус платежа на стороне тинькофф не {targetStatus}, а {payment.status}", HTTP_INTERNAL_ERROR)
    
    insertHistory(
        userData['id'],
        'payment',
        f'Cancelled payment for order #{orderId}, paymentId: {payment.id}, status: {payment.status}, success: {payment.success}'
    )
    
    # Запускаем поллинг для того, чтобы узнать когда пройдет оплата, если вебхук не сработает
    startPollingForPayment(
        order,
        userData,
        [
            PaymentStatuses.CANCELLED, # из NEW
            PaymentStatuses.REVERSED, # из AUTHORIZED
            PaymentStatuses.PARTIAL_REVERSED, # из AUTHORIZED
            PaymentStatuses.REFUNDED, # из CONFIRMED
            PaymentStatuses.PARTIAL_REFUNDED, # из CONFIRMED
        ],
    )
    
    # Отвечаем что всё ок
    return jsonResponse(f"Оплата отменена")


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
        payment = getPaymentState(order['paymentid'])
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    return jsonResponse({
        'id': payment.id,
        'orderId': payment.orderId,
        'success': payment.success,
        'errorCode': payment.errorCode,
        'message': payment.message,
        'details': payment.details,
        'status': payment.status,
        'amount': payment.amount,
        'route': payment.route,
        'source': payment.source,
    })


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payment = paymentsWebhook(request)
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)
    
    # Получаем информацию о заказе
    order = DB.execute(SQLOrders.selectOrderById, [payment.orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    
    # Получаем информацию о владельце заказа
    user = DB.execute(SQLUser.selectUserById, [order['userid']])
    if not user:
        return jsonResponse("Владелец заказа не найден", HTTP_NOT_FOUND)

    insertHistory(
        user['id'],
        'payment',
        f'Webhook update order: #{payment.orderId}, paymentId: {payment.paymentId}, status: {payment.status}'
    )
    
    # Обновляем статус заказа
    # Если статус в базе уже такой, то пропускаем обработку смены статуса
    if payment.status == order['paymentstatus']:
        return make_response("OK", HTTP_OK)
    processChangingPaymentStatus(payment.status, order, user)
    
    return make_response("OK", HTTP_OK)



# ============== Cards =============
# @app.route("/card", methods=["POST"])
# @login_required
# def addCard(userData):
#     try:
#         payment = addCard(userData)
#     except Exception as err:
#         return jsonResponse(str(err), HTTP_INTERNAL_ERROR)
    
#     # Инициируем привязку карты. В ответе придёт paymentUrl,
#     # на который нужно перенаправить клиента для ввода данных карты.

#     return jsonResponse({
#         'paymentUrl': payment.paymentUrl,   # ссылка для привязки карты
#         'requestKey': payment.requestKey,   # ключ запроса на привязку
#     })

# @app.route("/cards", methods=["GET"])
# @login_required
# def getCards(userData):
#     try:
#         req = request.args
#         userId = req['userId']
#     except Exception as err:
#         return jsonResponse(f"Не удаgлось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    
#     if str(userId) != str(userData['id']) and not userData['caneditorders']:
#         return jsonResponse("Нет прав на просмотр карт другого пользователя", HTTP_NO_PERMISSIONS)
    
#     try:
#         res = getCardsList(userId)
#     except Exception as err:
#         return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

#     return jsonResponse({'cards': res.cards or []})
