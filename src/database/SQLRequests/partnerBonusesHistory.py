from src.database.SQLRequests.user import userPublicColumns

insertPartnerBonusesHistory = \
    "INSERT INTO partnerBonusesHistory (userId, fromUserId, value, orderId, comment) " \
    "VALUES (%s, %s, %s, %s, %s) " \
    "RETURNING *"

# ------------------

selectPartnerBonusesHistoryByUserId = \
    f"SELECT {userPublicColumns}, partnerBonusesHistory.* FROM partnerBonusesHistory " \
    "JOIN users ON partnerBonusesHistory.fromUserId = users.id " \
    "WHERE userId = %s"
selectPartnerBonusesHistoryByUserIdForLastMonth = \
    f"SELECT {userPublicColumns}, partnerBonusesHistory.* FROM partnerBonusesHistory " \
    "JOIN users ON partnerBonusesHistory.fromUserId = users.id " \
    "WHERE userId = %s " \
    "AND date > NOW() - INTERVAL '30 day'"
selectTotalPartnerBonusesHistoryByUserIdForLastMonth = \
    "SELECT SUM(value) as total FROM partnerBonusesHistory " \
    "JOIN users ON partnerBonusesHistory.fromUserId = users.id " \
    "WHERE userId = %s " \
    "AND date > NOW() - INTERVAL '30 day'"


selectAllBonusesByUserIdForLastMonth = \
    f"SELECT {userPublicColumns}, COALESCE(SUM(value), 0) as totalValue FROM partnerBonusesHistory " \
    "RIGHT JOIN users on users.id = partnerBonusesHistory.fromuserid " \
    "WHERE " \
        "userId = %s OR " \
        "( " \
            "users.partnerStatus = true AND " \
            "users.referrerid = %s " \
        ")" \
    "AND (date is null OR date > NOW() - INTERVAL '30 day') " \
    "GROUP BY users.id "

selectPartnersAndBonusesByUserIdForLastMonth = \
    f"SELECT {userPublicColumns}, COALESCE(SUM(value), 0) as totalValue FROM partnerBonusesHistory " \
    "RIGHT JOIN users on users.id = partnerBonusesHistory.fromuserid " \
    "WHERE " \
        "users.partnerStatus = true AND " \
        "users.referrerid = %s " \
    "AND (date is null OR date > NOW() - INTERVAL '30 day') " \
    "GROUP BY users.id "

# ------------------

deletePartnerBonusesHistoryById = \
    "DELETE FROM partnerBonusesHistory " \
    "WHERE id = %s"
