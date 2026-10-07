insertPartner = \
    "INSERT INTO partners (userId, newbieBonusPeriodsLeft, personalBonuses) " \
    "VALUES (%s, %s, %s) " \
    "RETURNING *"

# ------------------

selectPartnerByUserid = \
    "SELECT * FROM partners " \
    "WHERE userId = %s"
selectAllPartners = \
    "SELECT * FROM partners"
selectPartnersByActive = \
    "SELECT * FROM partners " \
    "WHERE isActive = %s"

selectPartnerReferrerByUserid = \
    "SELECT * FROM partners " \
    "WHERE id = (" \
        "SELECT referrerId " \
        "FROM users " \
        "WHERE id = %s " \
    ")"

selectPartnersReferreredByUserid = \
    "SELECT partners.* FROM partners " \
    "JOIN users ON users.id = partners.userId " \
    "WHERE referrerId = %s"

selectActivePartnersReferreredByUserid = \
    "SELECT partners.* FROM partners " \
    "JOIN users ON users.id = partners.userId " \
    "WHERE referrerId = %s " \
    "AND isActive = %s"

# ------------------

updatePartnerByUserid = \
    "UPDATE partners SET " \
    "isActive = %s, " \
    "newbieBonusPeriodsLeft = %s, " \
    "blackPearlBonuses = %s, " \
    "bonusBigTeamPeriods = %s " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerSetActiveByUserid = \
    "UPDATE partners SET " \
    "isActive = TRUE, " \
    "activatedDate = NOW() " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerSetNotActiveByUserid = \
    "UPDATE partners SET " \
    "isActive = FALSE " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerAddPersonalBonusesByUserId = \
    "UPDATE partners SET " \
    "personalBonuses = personalBonuses + %s " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerAddTotalBonusesByUserId = \
    "UPDATE partners SET " \
    "personalBonuses = personalBonuses + %s " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerAddGroupBonusesByUserId = \
    "UPDATE partners SET " \
    "groupBonuses = groupBonuses + %s " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerAddBlackPearlBonusesByUserId = \
    "UPDATE partners SET " \
    "blackPearlBonuses = blackPearlBonuses + %s " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerAddBranchTotalBonusesByUserId = \
    "UPDATE partners SET " \
    "branchTotalBonuses = branchTotalBonuses + %s " \
    "WHERE userId = %s " \
    "RETURNING *"


updatePartnersDeactivateNotActivated = \
    "UPDATE partners SET " \
    "isActive = FALSE " \
    "WHERE activatedDate < DATE_TRUNC('month', NOW()) " \
    "RETURNING *"
updatePartnersSetMonthlyBonusesToTotal = \
    "UPDATE partners SET " \
    "totalBonuses = totalBonuses + personalBonuses + groupBonuses, " \
    "personalBonuses = 0, " \
    "groupBonuses = 0, " \
    "branchTotalBonuses = 0 " \
    "RETURNING *"
updatePartnersDecreaseNewbieBonusPeriodsLeft = \
    "UPDATE partners SET " \
    "newbieBonusPeriodsLeft = MAX(newbieBonusPeriodsLeft - 1, 0) " \
    "RETURNING *"
updatePartnerQualityIdByUserid = \
    "UPDATE partners SET " \
    "qualityId = %s " \
    "WHERE userId = %s " \
    "RETURNING *"
updatePartnerSetBonusBigTeamPeriods = \
    "UPDATE partners SET " \
    "bonusBigTeamPeriods = %s " \
    "WHERE userId = %s " \
    "RETURNING *"

# ------------------

deletePartnerByUserid = \
    "DELETE FROM partners " \
    "WHERE userId = %s"




# =========== Partners to qualities ===========

insertPartnersQualities = \
    "INSERT INTO partnersQualities (partnerId, qualityId, count) " \
    "VALUES (%s, %s, 1) " \
    "RETURNING *"

selectPartnersQualitiesByPartneridQualityid = \
    "SELECT * FROM partnersQualities " \
    "WHERE partnerId = %s " \
    "AND qualityId = %s"

increasePartnersQualitiesCountByPartneridQualityid = \
    "UPDATE partnersQualities SET " \
    "count = count + 1, " \
    "WHERE partnerId = %s " \
    "AND qualityId = %s " \
    "RETURNING *"

deletePartnersQualitiesByPartneridQualityid = \
    "DELETE FROM partnersQualities " \
    "WHERE partnerId = %s " \
    "AND qualityId = %s"