from flask import Blueprint

from config import CONFIG
from payments.types import PayoutStatuses
from src.payments.requestsPayouts import getSbpBanks, initPayoutSbp, makePayoutSbp
from src.database.databaseUtils import insertHistory
from src.utils.access import *
from src.utils.utils import *

from src.database.SQLRequests import globals as SQLGlobals
from src.database.SQLRequests import partners as SQLPartners

app = Blueprint('payouts', __name__)


@app.route("/banks", methods=["GET"])
@login_required
def getBanks(userData):
    try:
        res = getSbpBanks()
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    return jsonResponse({'banks': res.members or []})


@app.route("/init", methods=["POST"])
@login_required
def initPayout(userData):
    try:
        req = request.args
        userId = req['userId']
        tel = req['tel']
        spbBankId = req['spbBankId']
        amount = req['amount']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and not userData['caneditorders']:
        return jsonResponse("Нет прав на вывод средств для другого пользователя", HTTP_NO_PERMISSIONS)

    # Проверяем, можно ли выводить
    partner = DB.execute(SQLPartners.selectPartnerByUserid, [userId])
    if not partner:
        return jsonResponse("Пользователь не является партнером", HTTP_NOT_FOUND)
    if amount > partner['totalbonuses']:
        return jsonResponse("На счету пользователя не хватает бонусов", HTTP_INVALID_DATA)
    if amount < CONFIG.min_bonuses_to_payout:
        return jsonResponse(f"Нельзя вывести меньше {CONFIG.min_bonuses_to_payout} бонусов", HTTP_INVALID_DATA)

    # Считаем суммы
    globals = DB.execute(SQLGlobals.selectGlobals, [])
    totalAmountX100 = int(amount * globals['moneyforbonuses'] * 100)

    insertHistory(
        userId,
        'payouts',
        f'Payout requested for {totalAmountX100 / 100} ({amount} bonuses)',
    )
    
    # Отправляем запрос на перевод
    try:
        # 1. Отправляем
        payment = initPayoutSbp(userId, tel, spbBankId, totalAmountX100, f'Выплата_партнерских_бонусов_на_{CONFIG.deploy_short_url}')

        # 2. Проверяем статус
        if payment.status != PayoutStatuses.CHECKED:
            raise Exception(f"Ошибка инициализации выплаты. Статус выплаты: {payment.status}")
        
        # 3. Подтверждаем выплату (в течение 180 секунд!)
        res = makePayoutSbp(payment.id)

        if res.status not in [PayoutStatuses.COMPLETING, PayoutStatuses.COMPLETED]:
            raise Exception(f"Ошибка подтверждения выплаты. Статус выплаты: {res.status}")
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

    insertHistory(
        userId,
        'payouts',
        f'Payout done for {totalAmountX100 / 100} ({amount} bonuses)',
    )
    return jsonResponse("Выплата проведена")
