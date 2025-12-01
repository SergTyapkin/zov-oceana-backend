# -----------------------
# -- Default user part --
# -----------------------
import json

_userPublicColumns = "users.id, users.avatarUrl, users.givenName, users.familyName, users.joinedDate"

# ----- INSERTS -----
insertUser = \
    "INSERT INTO users (tgId, tgUsername, avatarUrl, email, tel, familyName, givenName, middleName, password) " \
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) " \
    "RETURNING *"

insertSession = \
    "INSERT INTO sessions (userId, token, expires, ip, browser, os, geolocation) " \
    "VALUES (%s, %s, NOW() + interval '1 week' * %s, %s, %s, %s, %s) " \
    "RETURNING *"

insertSecretCode = \
    "INSERT INTO secretCodes (userId, code, type, meta, expires) " \
    "VALUES (%s, %s, %s, %s, NOW() + interval '7 days' * %s)" \
    "RETURNING *"

# ----- SELECTS -----
selectUserIdByTgId = \
    f"SELECT id FROM users " \
    "WHERE tgId = %s"

selectUserByTgUsernameOrTgId = \
    f"SELECT * FROM users " \
    "WHERE LOWER(tgUsername) = LOWER(%s) OR " \
    "tgId = %s"

selectUserById = \
    "SELECT * FROM users " \
    "WHERE id = %s"

selectAnotherUserById = \
    f"SELECT {_userPublicColumns} FROM users " \
    "WHERE id = %s"

selectUserByUserIdPassword = \
    f"SELECT * FROM users " \
    "WHERE id = %s " \
    "AND password = %s"

selectUserByEmail = \
    "SELECT * FROM users " \
    "WHERE email = %s"

selectUserByEmailTelTgusernameTgid = \
    "SELECT * FROM users " \
    "WHERE email = %s " \
    "OR tel = %s " \
    "OR tgUsername = %s " \
    "OR tgId = %s"

selectUserByEmailOrTel = \
    "SELECT * FROM users " \
    "WHERE email = %s " \
    "OR tel = %s"

selectUserByEmailOrTelPassword = \
    "SELECT * FROM users " \
    "WHERE (email = %s " \
    "OR tel = %s) " \
    "AND password = %s"

selectUserIdBySessionToken = \
    "SELECT userId, ip FROM sessions " \
    "WHERE token = %s"

selectSessionByUserId = \
    "SELECT * FROM sessions " \
    "WHERE userId = %s " \
    "LIMIT 1"

selectAllUserSessions = \
    "SELECT * FROM sessions " \
    "WHERE userId = %s"

selectUserDataBySessionToken = \
    "SELECT users.*, ip FROM sessions " \
    "JOIN users ON sessions.userId = users.id " \
    "WHERE token = %s"

def selectUsersByFilters(filters):
    search = filters.get('search', '').lower()
    ordering = json.loads(filters.get('ordering')) if filters.get('ordering') else []

    return \
            f"SELECT {_userPublicColumns} FROM users " \
            "WHERE " + \
            (f"LOWER(familyName || ' ' || givenName ' ' || middleName || ' ' || id) LIKE '%%{search}%%' AND " if 'search' in filters else "") + \
            "1 = 1 " \
            "ORDER BY " + f"{', '.join(ordering + ['id'])}"

selectSecretCodeByUserIdType = \
    "SELECT * FROM secretCodes " \
    "WHERE userId = %s AND " \
    "type = %s AND " \
    "expires > NOW()"

selectSecretCodeByCodeType = \
    "SELECT * FROM secretCodes " \
    "WHERE code = %s AND " \
    "type = %s AND " \
    "expires > NOW()"

# ----- UPDATES -----
updateUserTgDataById = \
    "UPDATE users SET " \
    "tgId = %s, " \
    "tgUsername = %s, " \
    "avatarUrl = %s " \
    "WHERE id = %s " \
    "RETURNING *"

updateUserTgDataWithoutAvatarUrlById = \
    "UPDATE users SET " \
    "tgId = %s, " \
    "tgUsername = %s " \
    "WHERE id = %s " \
    "RETURNING *"

updateUserById = \
    "UPDATE users SET " \
    "givenName = %s, " \
    "familyName = %s, " \
    "middleName = %s, " \
    "email = %s, " \
    "tel = %s, " \
    "isEmailNotificationsOn = %s, " \
    "avatarUrl = %s " \
    "WHERE id = %s " \
    "RETURNING *"

adminUpdateUserById = \
    "UPDATE users SET " \
    "tgUsername = %s, " \
    "tgId = %s, " \
    "givenName = %s, " \
    "familyName = %s, " \
    "middleName = %s, " \
    "email = %s, " \
    "tel = %s, " \
    "isEmailNotificationsOn = %s, " \
    "avatarUrl = %s, " \
    "canEditOrders = %s, " \
    "canEditUsers = %s, " \
    "canEditGoods = %s, " \
    "canEditHistory = %s, " \
    "canExecuteSQL = %s, " \
    "canEditGlobals = %s " \
    "WHERE id = %s " \
    "RETURNING *"

updateUserConfirmationBySecretcodeType = \
    "UPDATE users " \
    "SET isConfirmedEmail = True " \
    "FROM secretCodes " \
    "WHERE secretCodes.userId = CAST(users.id as TEXT) AND " \
    "secretCodes.code = %s AND " \
    "secretCodes.type = %s " \
    "RETURNING users.*"

updateUserRevokeEmailConfirmationByUserId = \
    "UPDATE users " \
    "SET isConfirmedEmail = False " \
    "WHERE id = %s " \
    "RETURNING *"

updateUserPasswordById = \
    "UPDATE users " \
    "SET password = %s " \
    "WHERE id = %s " \
    "RETURNING *"

# ----- DELETES -----
deleteExpiredSessions = \
    "DELETE FROM sessions " \
    "WHERE expires <= NOW()"

deleteUserById = \
    "DELETE FROM users " \
    "WHERE id = %s"

deleteSessionByToken = \
    "DELETE FROM sessions " \
    "WHERE token = %s"

deleteAllUserSessionsWithoutCurrent = \
    "DELETE FROM sessions " \
    "WHERE userId = %s AND " \
    "token != %s"

deleteExpiredSecretCodes = \
    "DELETE FROM secretCodes " \
    "WHERE expires <= NOW()"

deleteSecretCodeByUseridCode = \
    "DELETE FROM secretCodes " \
    "WHERE userId = %s AND " \
    "code = %s"

deleteSecretCodeByCodeType = \
    "DELETE FROM secretCodes " \
    "WHERE code = %s AND " \
    "type = %s"
