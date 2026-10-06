insertQuality = \
    "INSERT INTO qualities (title, branchDeepForQuality, percentForQuality, activeCountRequirement, branchesCountRequirement, branchesValuesRequirement, totalPersonalBonusesRequirement, qualityBonusValue, qualityBonusMaxCount) " \
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) " \
    "RETURNING *"

# ------------------

selectQualityById = \
    "SELECT * FROM qualities " \
    "WHERE id = %s"
selectAllQualities = \
    "SELECT * FROM qualities " \
    "ORDER BY branchDeepForQuality"

# ------------------

updateQualityById = \
    "UPDATE qualities SET " \
    "title = %s, " \
    "branchDeepForQuality = %s, " \
    "percentForQuality = %s, " \
    "activeCountRequirement = %s, " \
    "branchesCountRequirement = %s, " \
    "branchesValuesRequirement = %s, " \
    "totalPersonalBonusesRequirement = %s, " \
    "qualityBonusValue = %s, " \
    "qualityBonusMaxCount = %s, " \
    "WHERE id = %s"

# ------------------

deleteQualityById = \
    "DELETE FROM qualities " \
    "WHERE id = %s"
