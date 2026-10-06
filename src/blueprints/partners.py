from flask import Blueprint, request
from blueprints.orders import getOrderTotalCost, getOrdersTotalCost, prepareOrder
from src.config import CONFIG
from src.connections import DB
from src.constants import HTTP_INTERNAL_ERROR, HTTP_NO_PERMISSIONS, HTTP_INVALID_DATA, HTTP_NOT_FOUND
from src.database.SQLRequests import orders as SQLOrders
from src.database.SQLRequests import qualities as SQLQualities
from src.database.SQLRequests import globals as SQLGlobals
from src.database.SQLRequests import partnerBonusesHistory as SQLPartnersBonusesHistory
from src.database.SQLRequests import partners as SQLPartners
from src.database.databaseUtils import insertHistory
from src.utils.access import login_required, login_and_can_edit_partners_required
from src.utils.utils import jsonResponse

app = Blueprint('partners', __name__)


def convertCostToBonuses(cost):
    globals = DB.execute(SQLGlobals.selectGlobals, [])
    if globals['moneyforbonuses'] == 0:
        raise TypeError(f"На сервере установлен курс бонусов к стоимости заказов 0. Сначала его нужно изменить")
    return cost / globals['moneyforbonuses']

def addBonusesToReferrersByOrderData(orderData):
    # Получаем стоимость заказа в баллах
    orderTotalCost = getOrderTotalCost(orderData)
    orderBonuses = convertCostToBonuses(orderTotalCost)

    # Получаем максимальную глубину вложенности, которую надо пройти вверх
    qualities = DB.execute(SQLQualities.selectAllQualities, [])
    maxQualityDeep = 0
    for quality in qualities:
        maxQualityDeep = max(maxQualityDeep, quality['branchdeepforquality'] or 0)

    # Проходимся по каждой ветке вверх по очереди
    currentUserId = orderData['userid']
    for qualityDeep in range(1, maxQualityDeep + 1):
        # Получаем реферала. Если его нет - останавливаемся
        referrerPartnerData = DB.execute(SQLPartners.selectPartnerReferrerByUserid, [currentUserId])
        if referrerPartnerData is None:
            break

        # Собираем бонусы всех квалификации на текущем уровне вложенности (если вдруг их несколько)
        totalQualityPercents = 0
        for quality in qualities:
            if quality['branchdeepforquality'] == qualityDeep:
                totalQualityPercents += quality['percentforquality']
        # Добавляем "Бонус Новичка"
        if referrerPartnerData['newbiebonusperiodsleft'] > 0 and qualityDeep <= CONFIG.newbie_bonus_max_deep:
            totalQualityPercents += CONFIG.newbie_bonus_value
        # Добавляем "Бонус Чёрной Икры"
        if qualityDeep <= 1:
            blackPearlBonuses = orderBonuses * (CONFIG.black_pearl_bonus_value / 100)
            DB.execute(SQLPartners.updatePartnerAddBlackPearlBonusesByUserId, [blackPearlBonuses, referrerPartnerData['id']])

        totalCurrentBonuses = orderBonuses * (totalQualityPercents / 100)

        # Обновляем оборот ветки реферала
        if orderBonuses > 0:
            DB.execute(SQLPartners.updatePartnerAddBranchTotalBonusesByUserId, [orderBonuses, referrerPartnerData['id']])

        # Выдаем рефералу групповые бонусы если он активен
        if totalCurrentBonuses > 0 and referrerPartnerData['isactive']:
            DB.execute(SQLPartners.updatePartnerAddGroupBonusesByUserId, [totalCurrentBonuses, referrerPartnerData['id']])
            DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [referrerPartnerData['id'], currentUserId, totalCurrentBonuses, orderData['id'], f'Глубина {qualityDeep}, {totalQualityPercents}%'])

        # Делаем реферала новым текущим и идем дальше
        currentUserId = referrerPartnerData['userid']


# -------------- Partners

@app.route("/", methods=["GET"])
@login_required
def getPartner(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditpartners']:
        return jsonResponse("Нет прав на просмотр партнерской информации другого пользователя", HTTP_NO_PERMISSIONS)

    partner = DB.execute(SQLPartners.selectPartnerByUserid, [userId])

    return jsonResponse(partner)

@app.route("/all", methods=["GET"])
@login_and_can_edit_partners_required
def getPartners(userData):
    try:
        req = request.args
        isActive = req.get('isActive')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    if isActive is None:
        partners = DB.execute(SQLPartners.selectAllPartners, [], manyResults=True)
    else:
        partners = DB.execute(SQLPartners.selectPartnersByActive, [isActive], manyResults=True)

    return jsonResponse({"partners": partners})

@app.route("/", methods=["POST"])
@login_and_can_edit_partners_required
def createPartner(userData):
    try:
        req = request.json
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    # Конвертируем суммы за все его заказы за месяц в его баллы
    orders = DB.execute(SQLOrders.selectUserOrdersMonthlyByUserId, [userId], manyResults=True)
    ordersTotalValueForMonth = getOrdersTotalCost(orders)
    bonusesForMonth = convertCostToBonuses(ordersTotalValueForMonth)

    # Создаем партнера с его бонусами
    partner = DB.execute(SQLPartners.insertPartner, [userId, CONFIG.newbie_bonus_periods_default, bonusesForMonth])
    return jsonResponse(partner)

@app.route("/", methods=["PUT"])
@login_and_can_edit_partners_required
def updatePartner(userData):
    try:
        req = request.json
        userId = req['userId']
        isActive = req.get('isActive')
        newbieBonusPeriodsLeft = req.get('newbieBonusPeriodsLeft')
        blackPearlBonuses = req.get('blackPearlBonuses')
        bonusBigTeamPeriods = req.get('bonusBigTeamPeriods')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    partner = DB.execute(SQLPartners.selectPartnerByUserid, [userId])
    if not partner:
        return jsonResponse(f"Партнер не зарегистрирован: {str(err)}", HTTP_NOT_FOUND)

    isActive = isActive if isActive is not None else partner['isactive']
    newbieBonusPeriodsLeft = newbieBonusPeriodsLeft if newbieBonusPeriodsLeft is not None else partner['newbiebonusperiodsleft']
    blackPearlBonuses = blackPearlBonuses if blackPearlBonuses is not None else partner['blackpearlbonuses']
    bonusBigTeamPeriods = bonusBigTeamPeriods if bonusBigTeamPeriods is not None else partner['bonusbigteamperiods']

    partner = DB.execute(SQLPartners.updatePartnerByUserid, [isActive, newbieBonusPeriodsLeft, blackPearlBonuses, bonusBigTeamPeriods, userId], manyResults=True)

    return jsonResponse(partner)


# -------------- Partners history

@app.route("/history", methods=["GET"])
@login_required
def getUserBonusesHistory(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

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
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

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
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

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
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)


    DB.execute(SQLPartners.updatePartnerAddTotalBonusesByUserId, [value, userId])
    history = DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [userId, fromUserId, value, orderId, comment])

    return jsonResponse(history)
