from config import CONFIG
from connections import DB

from src.database.SQLRequests import globals as SQLGlobals
from src.database.SQLRequests import partners as SQLPartners
from src.database.SQLRequests import qualities as SQLQualities
from src.database.SQLRequests import partnerBonusesHistory as SQLPartnersBonusesHistory

from operator import itemgetter


if __name__ == '__main__':
    # Просто получаем все квалификации
    qualities = DB.execute(SQLQualities.selectAllQualities, [], manyResults=True)
    qualities.sort(key=itemgetter("branchdeepforquality"))
    qualitiesWithBonuses = [q for q in qualities if q['qualitybonusvalue'] is not None]
    qualitiesWithBonusesReversed = qualitiesWithBonuses[::-1]

    # Деактивируем всех партнеров, кто не активировался в этом месяце
    DB.execute(SQLPartners.updatePartnersDeactivateNotActivated)

    # Уменьшаем оставшийся бонус новичка
    DB.execute(SQLPartners.updatePartnersDecreaseNewbieBonusPeriodsLeft)

    # Считаем квалификации
    # Получаем всех оставшихся активных
    partners = DB.execute(SQLPartners.selectPartnersByActive, [True], manyResults=True)
    for partner in partners:
        referals = DB.execute(SQLPartners.selectPartnersReferreredByUserid, [partner['userid']], manyResults=True)
        activeReferals = 0 # Кол-во активных рефералов
        branchTotalBonuses = [] # Объем веток
        for referal in referals:
            branchTotalBonuses += [referal['branchtotalbonuses']]
            activeReferals += 1 if referal['isactive'] else 0
        personalBonuses = partner['personalbonuses'] # Личный объем

        # Определяем квалификацию по всем условиям
        maxQuality = None
        for quality in qualities:
            if (
                    quality['activecountrequirement'] is not None and 
                    activeReferals >= quality['activecountrequirement']
                ) and (
                    quality['totalpersonalbonusesrequirement'] is not None and
                    personalBonuses >= quality['totalpersonalbonusesrequirement']
                ) and (
                    quality['branchescountrequirement'] is not None and quality['branchesvaluesrequirement'] and
                    sum(1 for bVal in branchTotalBonuses if bVal > quality['branchesvaluesrequirement']) >= quality['branchescountrequirement']
                ):
                maxQuality = quality
        
        partner = DB.execute(SQLQualities.updatePartnerQualityIdByUserid, [maxQuality['id'] if maxQuality else None, partner['id']])

        # Считаем бонусы квалификации
        # Проверяем, начиная с самой высшей доступной квалификации с бонусом
        for quality in qualitiesWithBonusesReversed:
            if maxQuality['branchdeepforquality'] > quality['branchdeepforquality']:
                # Категория подходит, надо проверить за неё бонусы
                partnerToQuality = DB.execute(SQLPartners.selectPartnersQualitiesByPartneridQualityid, [partner['id'], quality['id']])
                if partnerToQuality['count'] < quality['qualitybonusmaxcount']:
                    # Выдаем бонус за квалификацию. Создаем запись если надо
                    if partnerToQuality is not None:
                        DB.execute(SQLPartners.increasePartnersQualitiesCountByPartneridQualityid, [partner['id'], quality['id']])
                    else:
                        DB.execute(SQLPartners.insertPartnersQualities, [partner['id'], quality['id']])
                    DB.execute(SQLPartners.updatePartnerAddTotalBonusesByUserId, [quality['qualitybonusvalue'], partner['id']])
                    DB.execute(SQLPartnersBonusesHistory.insertPartnerBonusesHistory, [partner['id'], None, quality['qualitybonusvalue'] or 0, None, f'Бонус квалификации "{quality['title']}"'])
                    break

        
        # TODO: Считаем бонус большой команды

    # - Бонус черной икры считается при заказах

    # Перечисляем суммы баллов за месяц на основной баланс
    DB.execute(SQLPartners.updatePartnersSetMonthlyBonusesToTotal)