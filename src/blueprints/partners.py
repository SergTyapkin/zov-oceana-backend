import json

from flask import Blueprint, request
from blueprints.orders import getOrderTotalCostX100, getOrdersTotalCostX100
from payments.requests import addCustomer
from src.config import CONFIG
from src.connections import DB
from src.constants import HTTP_INTERNAL_ERROR, HTTP_NO_PERMISSIONS, HTTP_INVALID_DATA, HTTP_NOT_FOUND
from src.database.SQLRequests import orders as SQLOrders
from src.database.SQLRequests import qualities as SQLQualities
from src.database.SQLRequests import user as SQLUser
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
    orderTotalCost = getOrderTotalCostX100(orderData)
    orderBonuses = convertCostToBonuses(orderTotalCost)

    # Добавляем личные бонусы и проверяем, активировался ли партнер от этой попкупки
    partner = DB.execute(SQLPartners.updatePartnerAddPersonalBonusesByUserId, [orderBonuses, orderData['userid']])
    isPartnerActivatedCurrently = partner is not None and partner['personalbonuses'] >= CONFIG.personal_bonuses_to_activation
    if isPartnerActivatedCurrently:
        DB.execute(SQLPartners.updatePartnerSetActiveByUserid, [orderData['userid']])
        insertHistory(
            partner['userid'],
            'partners',
            f'Activated by personal: #{partner['userid']} by order {orderData["number"]} #{orderData["id"]}'
        )

    # Получаем максимальную глубину вложенности, которую надо пройти вверх
    qualities = DB.execute(SQLQualities.selectAllQualities, [])
    maxQualityDeep = 0
    for quality in qualities:
        maxQualityDeep = max(maxQualityDeep, quality['branchdeepforquality'] or 0)

    # Проходимся по каждой ветке вверх по очереди
    currentUserId = orderData['userid']
    for qualityDeep in range(1, maxQualityDeep + 1):
        # Получаем реферера. Если его нет - останавливаемся
        referrerPartnerData = DB.execute(SQLPartners.selectPartnerReferrerByUserid, [currentUserId])
        if referrerPartnerData is None:
            break

        # Если партнер активировался от покупки, то активируем и реферерала только в 1 поколении
        if isPartnerActivatedCurrently and qualityDeep <= 1:
            referrerPartnerData = DB.execute(SQLPartners.updatePartnerSetActiveByUserid, [referrerPartnerData['userid']])
            insertHistory(
                referrerPartnerData['userid'],
                'partners',
                f'Activated by referal: #{partner['userid']} by #{currentUserId}'
            )

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
            DB.execute(SQLPartners.updatePartnerAddBlackPearlBonusesByUserId, [blackPearlBonuses, referrerPartnerData['userid']])

        totalCurrentGroupBonuses = orderBonuses * (totalQualityPercents / 100)

        # Обновляем оборот ветки реферала
        if orderBonuses > 0:
            DB.execute(SQLPartners.updatePartnerAddBranchTotalBonusesByUserId, [orderBonuses, referrerPartnerData['userid']])

        # Выдаем рефералу групповые бонусы если он активен
        if totalCurrentGroupBonuses > 0 and referrerPartnerData['isactive']:
            DB.execute(SQLPartners.updatePartnerAddGroupBonusesByUserId, [totalCurrentGroupBonuses, referrerPartnerData['userid']])
            DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [referrerPartnerData['userid'], currentUserId, totalCurrentGroupBonuses, True, orderData['id'], f'Глубина {qualityDeep}, {totalQualityPercents}%'])

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
    
    # Получаем данные пользователя
    user = DB.execute(SQLUser.selectUserByUserId, [userId])
    if not user:
        return jsonResponse(f"Пользователь не найден", HTTP_NOT_FOUND)
    
    # Получаем квалификации и сразу находим самую низшую
    qualities = DB.execute(SQLQualities.selectAllQualities, [], manyResults=True)
    lowestQuality = None
    for quality in qualities:
        if not lowestQuality or lowestQuality['branchdeepforquality'] < quality['branchdeepforquality']:
            lowestQuality = quality
    if not lowestQuality:
        return jsonResponse(f"На сервере не создана ни одна квалификация", HTTP_INTERNAL_ERROR)

    # Конвертируем суммы за все его заказы за месяц в его баллы
    orders = DB.execute(SQLOrders.selectUserOrdersMonthlyByUserId, [userId], manyResults=True)
    ordersTotalValueForMonth = getOrdersTotalCostX100(orders) / 100
    bonusesForMonth = convertCostToBonuses(ordersTotalValueForMonth)

    # Создаем партнера с его бонусами
    partner = DB.execute(SQLPartners.insertPartner, [userId, CONFIG.newbie_bonus_periods_default, bonusesForMonth, lowestQuality['id']])

    # Регистрируем клиента в банковском API
    try:
        addCustomer(user)
    except Exception as err:
        return jsonResponse(f"Ошибка при регистрации клиента в API банка: {str(err)}", HTTP_INTERNAL_ERROR)

    insertHistory(
        partner['userid'],
        'partners',
        f'Becomes partner by #{userData['id']} with {bonusesForMonth} bonuses'
    )

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

    insertHistory(
        userId,
        'partner',
        f'Updated by user #{userData["id"]}: {json.dumps(req)}'
    )
    return jsonResponse(partner)

@app.route("/", methods=["DELETE"])
@login_and_can_edit_partners_required
def updatePartner(userData):
    try:
        req = request.json
        userId = req['userId']
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

    insertHistory(
        userId,
        'partner',
        f'Updated by user #{userData["id"]}: {json.dumps(req)}'
    )
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
    history = DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [userId, fromUserId, value, False, orderId, comment])

    return jsonResponse(history)
