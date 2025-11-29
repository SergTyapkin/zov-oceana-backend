import random
import string

from flask import Blueprint

from src.TgBot.TgBot import TgBotMessageTexts, TgBot
from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import orders as SQLOrders
from src.database.SQLRequests import addresses as SQLAddresses
from src.database.SQLRequests import goods as SQLGoods

app = Blueprint('orders', __name__)


@app.route("", methods=["GET"])
@login_required
def getOrder(userData):
    try:
        req = request.args
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    order = DB.execute(SQLOrders.selectOrderById, [orderId])
    if order is None:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)
    if str(order['userid']) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на просмотр заказов другого пользователя", HTTP_NO_PERMISSIONS)

    print(order)
    return jsonResponse(order)

@app.route("/user", methods=["GET"])
@login_required
def getUserOrders(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на просмотр заказов другого пользователя", HTTP_NO_PERMISSIONS)

    orders = DB.execute(SQLOrders.selectUserOrdersByUserId, [userId], manyResults=True)
    print(orders)

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
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    try:
        for goodsOne in goods:
            if \
                'id' not in goodsOne or \
                'amount' not in goodsOne:
                return jsonResponse(f"Не удалось сериализовать json: не хватает полей в одном из goods", HTTP_INVALID_DATA)
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if (str(userId) != str(userData['id'])) and (not userData['caneditorders']):
        return jsonResponse("Нет прав на создание заказов для другого пользователя", HTTP_NO_PERMISSIONS)

    address = DB.execute(SQLAddresses.selectAddressById, [addressId])
    if not address:
        return jsonResponse("Адрес не найден", HTTP_NOT_FOUND)
    if str(address['userid']) != str(userId):
        return jsonResponse("Нельзя заказать на чужой адрес", HTTP_INVALID_DATA)

    symbols = string.digits
    randomSecretCode = ''.join(random.choice(symbols) for _ in range(ORDER_SECRET_CODE_GENERATE_LEN))
    maxOrderNumber = DB.execute(SQLOrders.selectMaxOrderNumber, [])
    maxOrderNumber = maxOrderNumber['maxnumber']
    orderData = DB.execute(SQLOrders.insertOrder, [maxOrderNumber + 1, userId, addressId, randomSecretCode])
    if orderData is None:
        return jsonResponse("Не удалось создать заказ", HTTP_INTERNAL_ERROR)

    goodsArrayInfoText = ""
    for goodsOne in goods:
        goodsOneData = DB.execute(SQLGoods.selectGoodsById, [goodsOne['id']])
        if goodsOneData is None:
            return jsonResponse(f"Товар #{goodsOne['id']} не найден", HTTP_NOT_FOUND)

        goodsInOrderData = DB.execute(SQLOrders.insertOrderGoods, [orderData['id'], goodsOne['id'], goodsOneData['cost'], goodsOne['amount']])
        if goodsInOrderData is None:
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
@login_and_can_edit_goods_required
def updateOrderData(userData):
    try:
        req = request.json
        id = req['id']
        addressId = req.get('addressId')
        status = req.get('status')
        trackingCode = req.get('trackingCode')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    orderData = DB.execute(SQLOrders.selectOrderById, [id])
    if orderData is None:
        return jsonResponse("Заказ не найден", HTTP_NOT_FOUND)

    if addressId is None: addressId = orderData['addressid']
    if status is None: status = orderData['status']
    if trackingCode is None: trackingCode = orderData['trackingcode']

    try:
        response = DB.execute(SQLOrders.updateOrderById, [addressId, status, trackingCode, id])
    except Exception as err:
        return jsonResponse(f"Не удалось изменить заказ {err.__repr__()}", HTTP_INVALID_DATA)

    insertHistory(
        userData['id'],
        'order',
        f'Update order: {orderData["number"]} #{orderData["id"]} {json.dumps(req)}'
    )

    try:
        fullUserData = DB.execute(SQLUser.selectUserById, [orderData['userid']])
        messageText = "Статус заказа изменён на какой-то другой (???)"
        if status == OrderStatuses.created:
            messageText = TgBotMessageTexts.orderStatusToCreated
        elif status == OrderStatuses.paid:
            messageText = TgBotMessageTexts.orderStatusToPaid
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

    return jsonResponse(response)


@app.route("", methods=["DELETE"])
@login_and_can_edit_orders_required
def deleteOrder(userData):
    try:
        req = request.json
        orderId = req['orderId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

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

