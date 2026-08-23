import json
import random
import string

from flask import Blueprint

from src.config import CONFIG
from src.TgBot.TgBot import TgBotMessageTexts, TgBot
from src.blueprints.goods import prepareGoodsData
from src.blueprints.partners import addBonusesToReferrersByOrderData
from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import orders as SQLOrders
from src.database.SQLRequests import addresses as SQLAddresses
from src.database.SQLRequests import goods as SQLGoods

app = Blueprint('orders', __name__)


def prepareOrder(orderData, addGoods = True, addAddress = True):
    if addGoods:
        orderGoods = DB.execute(SQLOrders.selectOrderGoodsByOrderId, [orderData['id']], manyResults=True)
        for goods in orderGoods:
            prepareGoodsData(goods, True, False)
        orderData['goods'] = orderGoods
    if addAddress:
        if orderData['addressid']:
            address = DB.execute(SQLAddresses.selectAddressById, [orderData['addressid']])
            orderData['address'] = address or None
        else:
            orderData['address'] = None

@app.route("", methods=["GET"])
@login_required
def getOrder(userData):
    try:
        req = request.args
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not order:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    print("> ORDER:", order)
    if str(order['userid']) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на просмотр заказов другого пользователя", HTTP_NO_PERMISSIONS)

    prepareOrder(order)
    return jsonResponse(order)

@app.route("/all", methods=["GET"])
@login_and_can_edit_orders_required
def getAllOrders(userData):
    try:
        req = request.args
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    orders = DB.execute(SQLOrders.selectAllOrdersWithUsers, [], manyResults=True)
    for order in orders:
        prepareOrder(order, True, False)
    return jsonResponse({'orders': orders})

@app.route("/user", methods=["GET"])
@login_required
def getUserOrders(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на просмотр заказов другого пользователя", HTTP_NO_PERMISSIONS)

    orders = DB.execute(SQLOrders.selectUserOrdersByUserId, [userId], manyResults=True)
    for order in orders:
        prepareOrder(order, True, False)

    return jsonResponse({'orders': orders})


@app.route("", methods=["POST"])
@login_required
def createOrder(userData):
    try:
        req = request.json
        userId = req['userId']
        addressId = req['addressId']
        goods = req['goods']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    try:
        for goodsOne in goods:
            if \
                'id' not in goodsOne or \
                'amount' not in goodsOne:
                return jsonResponse(f"Не удалось сериализовать json: не хватает полей в одном из goods", HTTP_INVALID_DATA)
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    if (str(userId) != str(userData['id'])) and (not userData['caneditorders']):
        return jsonResponse("Нет прав на создание заказов для другого пользователя", HTTP_NO_PERMISSIONS)

    address = DB.execute(SQLAddresses.selectAddressById, [addressId])
    if not address:
        return jsonResponse("Адрес не найден", HTTP_NOT_FOUND)
    if str(address['userid']) != str(userId):
        return jsonResponse("Нельзя заказать на чужой адрес", HTTP_INVALID_DATA)

    symbols = string.digits
    randomSecretCode = ''.join(random.choice(symbols) for _ in range(CONFIG.order_secret_code_generate_len))
    maxOrderId = DB.execute(SQLOrders.selectMaxOrderId, [])
    maxOrderId = maxOrderId['maxid'] if maxOrderId and maxOrderId['maxid'] else 0
    orderNumber = (maxOrderId + 1) * CONFIG.order_number_seed % CONFIG.max_order_number
    addressTextCopy = \
        f"г. {address['city']}" + \
        (f", ул. {address['street']}" if address['street'] else '') + \
        (f", д. {address['house']}" if address['house'] else '') + \
        (f", п. {address['entrance']}" if address['entrance'] else '') + \
        (f", эт. {address['floor']}" if address['floor'] else '') + \
        (f", кв. {address['apartment']}" if address['apartment'] else '') + \
        (f", Код: {address['code']}" if address['code'] else '')
    commentTextCopy = address['comment']
    orderData = DB.execute(SQLOrders.insertOrder, [orderNumber, userId, addressId, addressTextCopy, commentTextCopy, randomSecretCode])
    if not orderData:
        return jsonResponse("Не удалось создать заказ", HTTP_INTERNAL_ERROR)

    goodsArrayInfoText = ""
    for goodsOne in goods:
        goodsOneData = DB.execute(SQLGoods.selectGoodsById, [goodsOne['id']])
        if not goodsOneData:
            return jsonResponse(f"Товар #{goodsOne['id']} не найден", HTTP_NOT_FOUND)

        try:
            goodsInOrderData = DB.execute(SQLOrders.insertOrderGoods, [orderData['id'], goodsOne['id'], goodsOneData['cost'], goodsOne['amount']])
            if not goodsInOrderData:
                return jsonResponse(f"Не удалось добавить товар #{goodsOne['id']} в заказ #{orderData['id']}", HTTP_INVALID_DATA)
        except:
            # Ошибка 409, товар уже добавлен
            print(f"Товар уже есть в заказе! Заказ: #{orderData['id']}, Товар: #{goodsOne['id']} {goodsOne['title']}")

        goodsArrayInfoText += f"*{goodsOneData['title']}*, {goodsOne['amount']}кг\n"

    insertHistory(
        userId,
        'order',
        f'Creates order: {orderData["number"]} #{orderData["id"]}", goods: {goods}'
    )
    
    try:
        fullUserData = DB.execute(SQLUser.selectUserById, [orderData['userid']])
        TgBot.sendMessage(fullUserData['tgid'], TgBotMessageTexts.orderCreated, orderData["number"], goodsArrayInfoText)
    except Exception as err:
        print("Error. Cannot select user and send message by tg bot", err)
        pass

    prepareOrder(orderData, True, True);
    return jsonResponse(orderData)

@app.route("/admin", methods=["POST"])
@login_and_can_edit_orders_required
def createOrderByAdmin(userData):
    try:
        req = request.json
        userId = req['userId']
        goods = req['goods']
        status = req['status']
        trackingCode = req['trackingCode']
        addressTextCopy = req['addressTextCopy']
        commentTextCopy = req['commentTextCopy']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    try:
        for goodsOne in goods:
            if \
                'id' not in goodsOne or \
                'amount' not in goodsOne:
                return jsonResponse(f"Не удалось сериализовать json: не хватает полей в одном из goods", HTTP_INVALID_DATA)
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    symbols = string.digits
    randomSecretCode = ''.join(random.choice(symbols) for _ in range(ORDER_SECRET_CODE_GENERATE_LEN))
    maxOrderId = DB.execute(SQLOrders.selectMaxOrderId, [])
    maxOrderId = maxOrderId['maxid'] if maxOrderId and maxOrderId['maxid'] else 0
    orderNumber = (maxOrderId + 1) * ORDER_NUMBER_SEED % MAX_ORDER_NUMBER
    orderData = DB.execute(SQLOrders.insertOrder, [orderNumber, userId, None, addressTextCopy, commentTextCopy, randomSecretCode])
    if not orderData:
        return jsonResponse("Не удалось создать заказ", HTTP_INTERNAL_ERROR)

    goodsArrayInfoText = ""
    for goodsOne in goods:
        goodsOneData = DB.execute(SQLGoods.selectGoodsById, [goodsOne['id']])
        if not goodsOneData:
            return jsonResponse(f"Товар #{goodsOne['id']} не найден", HTTP_NOT_FOUND)

        goodsInOrderData = DB.execute(SQLOrders.insertOrderGoods, [orderData['id'], goodsOne['id'], goodsOne['cost'], goodsOne['amount']])
        if not goodsInOrderData:
            return jsonResponse(f"Не удалось добавить товар #{goodsOne['id']} в заказ #{orderData['id']}", HTTP_INVALID_DATA)

        goodsArrayInfoText += f"*{goodsOneData['title']}*, {goodsOne['amount']}кг\n"

    insertHistory(
        userId,
        'order',
        f'Creates order: {orderData["number"]} #{orderData["id"]}", goods: {goods}'
    )

    try:
        fullUserData = DB.execute(SQLUser.selectUserById, [orderData['userid']])
        TgBot.sendMessage(fullUserData['tgid'], TgBotMessageTexts.orderCreated, orderData["number"], goodsArrayInfoText)
    except Exception as err:
        print("Error. Cannot select user and send message by tg bot", err)
        pass

    return jsonResponse(orderData)

@app.route("", methods=["PUT"])
@login_and_can_edit_orders_required
def updateOrderData(userData):
    try:
        req = request.json
        id = req.get('id')
        userId = req.get('userId')
        number = req.get('number')
        addressId = req.get('addressId')
        addressTextCopy = req.get('addressTextCopy')
        commentTextCopy = req.get('commentTextCopy')
        status = req.get('status')
        paymentStatus = req.get('paymentStatus')
        paymentId = req.get('paymentId')
        paymentUrl = req.get('paymentUrl')
        paymentQrData = req.get('paymentQrData')
        trackingCode = req.get('trackingCode')
        goods = req.get('goods')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    try:
        for goodsOne in goods:
            if \
                'id' not in goodsOne or \
                'cost' not in goodsOne or \
                'amount' not in goodsOne:
                return jsonResponse(f"Не удалось сериализовать json: не хватает полей в одном из goods", HTTP_INVALID_DATA)
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    orderData = None
    if id is not None:
        orderData = DB.execute(SQLOrders.selectOrderById, [id])
    elif number is not None:
        orderData = DB.execute(SQLOrders.selectOrderByNumber, [number])

    if not orderData:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)

    if userId is None: userId = orderData['userid']
    if addressId is None: addressId = orderData['addressid']
    if addressTextCopy is None: addressTextCopy = orderData['addresstextcopy']
    if commentTextCopy is None: commentTextCopy = orderData['commenttextcopy']
    if status is None: status = orderData['status']
    if paymentStatus is None: paymentStatus = orderData['paymentstatus']
    if paymentId is None: paymentId = orderData['paymentid']
    if paymentUrl is None: paymentUrl = orderData['paymenturl']
    if paymentQrData is None: paymentQrData = orderData['paymentqrdata']
    if trackingCode is None: trackingCode = orderData['trackingcode']

    try:
        if id is not None:
            updatedOrderData = DB.execute(SQLOrders.updateOrderById, [userId, addressId, addressTextCopy, commentTextCopy, status, paymentStatus, paymentUrl, paymentQrData, paymentId, trackingCode, id])
        elif number is not None:
            updatedOrderData = DB.execute(SQLOrders.updateOrderByNumber, [userId, addressId, addressTextCopy, commentTextCopy, status, paymentStatus, paymentUrl, paymentQrData, paymentId, trackingCode, number])
    except Exception as err:
        return jsonResponse(f"Не удалось изменить заказ {str(err)}", HTTP_INVALID_DATA)

    DB.execute(SQLOrders.deleteAllOrderGoodsByOrderId, [updatedOrderData['id']])
    for goodsOne in goods:
        goodsInOrderData = DB.execute(SQLOrders.insertOrderGoods, [orderData['id'], goodsOne['id'], goodsOne['cost'], goodsOne['amount']])
        if not goodsInOrderData:
            return jsonResponse(f"Не удалось добавить товар #{goodsOne['id']} в заказ #{orderData['id']}", HTTP_INVALID_DATA)


    insertHistory(
        userData['id'],
        'order',
        f'Update order: {orderData["number"]} #{orderData["id"]} {json.dumps(req)}'
    )

    # Проверяем, необходимо ли начислить бонусные баллы реферелам за заказ, и начисляем
    if status == OrderStatuses.delivered and orderData['isreferrerbonusesadded'] == False:
        addBonusesToReferrersByOrderData(updatedOrderData)  
    
    # Если изменился статус заказа, высылаем уведомление     
    if orderData['status'] != status: # if status is changed
        try: # send TgBot notification
            fullUserData = DB.execute(SQLUser.selectUserById, [orderData['userid']])
            messageText = "Статус заказа изменён на какой-то неизвестный (???)"
            if status == OrderStatuses.created:
                messageText = TgBotMessageTexts.orderStatusToCreated
            elif status == OrderStatuses.accepted:
                messageText = TgBotMessageTexts.orderStatusToAccepted
            elif status == OrderStatuses.prepared:
                messageText = TgBotMessageTexts.orderStatusToPrepared
            elif status == OrderStatuses.delivered:
                messageText = TgBotMessageTexts.orderStatusToDelivered
            elif status == OrderStatuses.cancelled:
                messageText = TgBotMessageTexts.orderStatusToCancelled
            TgBot.sendMessage(fullUserData['tgid'], messageText, orderData["number"])
        except Exception as err:
            print("Error. Cannot select user and send message by tg bot", err)
            pass
    
    # Если изменился статус оплаты заказа, высылаем уведомление     
    if orderData['paymentstatus'] != paymentStatus: # if payment status is changed
        try: # send TgBot notification
            fullUserData = DB.execute(SQLUser.selectUserById, [orderData['userid']])
            messageText = "Статус оплаты заказа изменён на какой-то неизвестный (???)"
            if paymentStatus == OrderPaymentStatuses.new:
                messageText = TgBotMessageTexts.orderPaymentStatusToNew
            elif paymentStatus == OrderPaymentStatuses.authorized:
                messageText = TgBotMessageTexts.orderPaymentStatusToAuthorized
            elif paymentStatus == OrderPaymentStatuses.confirmed:
                messageText = TgBotMessageTexts.orderPaymentStatusToConfirmed
            elif paymentStatus == OrderPaymentStatuses.expired:
                messageText = TgBotMessageTexts.orderPaymentStatusToExpired
            elif paymentStatus == OrderPaymentStatuses.rejected:
                messageText = TgBotMessageTexts.orderPaymentStatusToRejected
            elif paymentStatus == OrderPaymentStatuses.refunded:
                messageText = TgBotMessageTexts.orderPaymentStatusToRefunded
            elif paymentStatus == OrderPaymentStatuses.cancelled:
                messageText = TgBotMessageTexts.orderPaymentStatusToCancelled
            TgBot.sendMessage(fullUserData['tgid'], messageText, orderData["number"])
        except Exception as err:
            print("Error. Cannot select user and send message by tg bot", err)
            pass

    return jsonResponse(updatedOrderData)


@app.route("", methods=["DELETE"])
@login_and_can_edit_orders_required
def deleteOrder(userData):
    try:
        req = request.json
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    orderData = DB.execute(SQLOrders.selectOrderById, [orderId])
    if not orderData:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)

    DB.execute(SQLOrders.deleteOrderById, [orderId])

    insertHistory(
        userData['id'],
        'order',
        f'Delete order: #{orderId}'
    )

    try:
        fullUserData = DB.execute(SQLUser.selectUserById, [orderData['userid']])
        TgBot.sendMessage(fullUserData['tgid'], TgBotMessageTexts.orderDeleted, orderData["number"])
    except Exception as err:
        print("Error. Cannot select user and send message by tg bot", err)
        pass

    return jsonResponse("Заказ удален")

