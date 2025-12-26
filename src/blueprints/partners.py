from flask import Blueprint, request
from src.connections import DB
from src.constants import ORDER_COST_PERCENT_TO_REFERRER_BONUSES, ORDER_COST_PERCENT_TO_REFERRER_AHEAD_1_BONUSES, \
    HTTP_NO_PERMISSIONS, HTTP_INVALID_DATA
from src.database.SQLRequests import orders as SQLOrders
from src.database.SQLRequests import user as SQLUser
from src.database.SQLRequests import partnerBonusesHistory as SQLPartnersBonusesHistory
from src.database.databaseUtils import insertHistory
from src.utils.access import login_required, login_and_can_edit_partners_required
from src.utils.utils import jsonResponse

app = Blueprint('partners', __name__)


def getOrderTotalCost(orderData):
    totalCost = 0
    orderGoods = DB.execute(SQLOrders.selectOrderGoodsByOrderId, [orderData['id']], manyResults=True)
    for goods in orderGoods:
        totalCost += goods['amount'] * goods['cost']
    return totalCost

def addBonusesToReferrersByOrderData(orderData):
    # Add bonus for referrer 1
    print("OWNER ORDER", orderData['userid'])
    orderUserReferrerData = DB.execute(SQLUser.selectUserReferrerById, [orderData['userid']])
    print("REFERRER", orderUserReferrerData)
    if not orderUserReferrerData:
        return
    totalCost = getOrderTotalCost(orderData)
    bonusesToReferrer = totalCost * ORDER_COST_PERCENT_TO_REFERRER_BONUSES
    DB.execute(SQLUser.updateUserAddPartnerBonusesById, [bonusesToReferrer, orderUserReferrerData['id']])
    DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [orderUserReferrerData['id'], orderData['userid'], bonusesToReferrer, orderData['id'], 'Lvl 0'])
    insertHistory(
        orderUserReferrerData['id'],
        'bonus',
        f'Gets {ORDER_COST_PERCENT_TO_REFERRER_BONUSES}% ({bonusesToReferrer}) from order :{orderData["number"]} #{orderData["id"]}'
    )

    # Add bonus for referrer 2
    orderUserReferrerData2 = DB.execute(SQLUser.selectUserReferrerById, [orderUserReferrerData['id']])
    if not orderUserReferrerData2:
        return
    bonusesToReferrer = totalCost * ORDER_COST_PERCENT_TO_REFERRER_AHEAD_1_BONUSES
    DB.execute(SQLUser.updateUserAddPartnerBonusesById, [bonusesToReferrer, orderUserReferrerData2['id']])
    DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [orderUserReferrerData2['id'], orderUserReferrerData['id'], bonusesToReferrer, orderData['id'], 'Lvl 1'])
    insertHistory(
        orderUserReferrerData2['id'],
        'bonus',
        f'Gets {ORDER_COST_PERCENT_TO_REFERRER_BONUSES}% ({bonusesToReferrer}) in tree lvl1 from order :{orderData["number"]} #{orderData["id"]}'
    )


@app.route("/history", methods=["GET"])
@login_required
def getUserBonusesHistory(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditpartners']:
        return jsonResponse("Нет прав на просмотр партнерских бонусов другого пользователя", HTTP_NO_PERMISSIONS)

    history = DB.execute(SQLPartnersBonusesHistory.selectPartnerBonusesHistoryByUserId, [userId], manyResults=True)

    return jsonResponse({'history': history})

@app.route("/history/monthly", methods=["GET"])
@login_required
def getUserBonusesHistoryMonthly(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditpartners']:
        return jsonResponse("Нет прав на просмотр партнерских бонусов другого пользователя", HTTP_NO_PERMISSIONS)

    history = DB.execute(SQLPartnersBonusesHistory.selectPartnerBonusesHistoryByUserIdForLastMonth, [userId], manyResults=True)

    return jsonResponse({'history': history})

@app.route("/users/bonuses/monthly", methods=["GET"])
@login_required
def getAllPartnerUsers(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditpartners']:
        return jsonResponse("Нет прав на просмотр партнерских бонусов другого пользователя", HTTP_NO_PERMISSIONS)

    partners = DB.execute(SQLPartnersBonusesHistory.selectPartnersAndBonusesByUserIdForLastMonth, [userId], manyResults=True)

    return jsonResponse({'partners': partners})

@app.route("/history", methods=["POST"])
@login_and_can_edit_partners_required
def addHistoryRecord(userData):
    try:
        req = request.json
        userId = req['userId']
        value = req['value']
        fromUserId = req.get('fromUserId')
        orderId = req.get('orderId')
        comment = req.get('comment')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)


    DB.execute(SQLUser.updateUserAddPartnerBonusesById, [value, userId])
    history = DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [userId, fromUserId, value, orderId, comment])

    return jsonResponse(history)
