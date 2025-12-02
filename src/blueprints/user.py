import json
import re
import uuid

from flask import Blueprint

from src.connections import config

from src.utils.access import *
from src.constants import *
from src.utils.detectGeoPositionUtils import detectGeoLocation
from src.utils.utils import *
from src.database.databaseUtils import insertHistory, createSecretCode

from src.database.SQLRequests import user as SQLUser
from src.database.SQLRequests import goods as SQLEvents
from src.database.SQLRequests import globals as SQLGlobals

from src import email_templates as emails

app = Blueprint('user', __name__)


def check_tg_auth_hash(id, first_name, last_name, username, photo_url, auth_date, hash):
    data_check_string = \
        (f"auth_date={auth_date}" if auth_date else "") + \
        (f"\nfirst_name={first_name}" if first_name else "") + \
        (f"\nid={id}" if id else "") + \
        (f"\nlast_name={last_name}" if last_name else "") + \
        (f"\nphoto_url={photo_url}" if photo_url else "") + \
        (f"\nusername={username}" if username else "")

    secret_key = hashlib.sha256(config["tg_bot_token"].encode('utf-8')).digest()
    expected_hash = hmac.new(secret_key, bytes(data_check_string, 'utf-8'), hashlib.sha256).hexdigest()

    authTime = datetime.datetime.fromtimestamp(int(auth_date))
    currentTime = datetime.datetime.now()
    return (
            (currentTime - authTime).total_seconds() < 60 * float(config["allow_tg_auth_period_min"]) and
            expected_hash == hash
    )


def new_session(resp: dict, browser: str, osName: str, geolocation: str, ip: str):
    token = str(uuid.uuid4())
    hoursAlive = 24 * 7  # 7 days
    session = DB.execute(SQLUser.insertSession, [resp['id'], token, hoursAlive, ip, browser, osName, geolocation])
    expires = session['expires']

    DB.execute(SQLUser.deleteExpiredSessions)

    resp.pop('password', None)

    res = jsonResponse(resp)
    res.set_cookie("session_token", token, expires=expires, httponly=True, samesite="lax")
    return res


@app.route("/auth/tg", methods=["POST"])
def userAuthByTg():
    try:
        req = request.json
        tgId = req['tgId']
        tgUsername = req.get('tgUsername')
        tgHash = req['tgHash']
        tgAuthDate = req['tgAuthDate']
        tgPhotoUrl = req.get('tgPhotoUrl')
        tgFirstName = req.get('tgFirstName')
        tgLastName = req.get('tgLastName')

        clientBrowser = req.get('clientBrowser', 'Unknown browser')
        clientOS = req.get('clientOS', 'Unknown OS')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if not check_tg_auth_hash(tgId, tgFirstName, tgLastName, tgUsername, tgPhotoUrl, tgAuthDate, tgHash):
        return jsonResponse("Хэш авторизации TG не совпадает с данными", HTTP_INVALID_AUTH_DATA)

    userData = DB.execute(SQLUser.selectUserByTgUsernameOrTgId, [tgUsername, str(tgId)])
    if not userData:
        return jsonResponse(f"Не удалось авторизоваться через TG. Аккаунт не найден", HTTP_NOT_FOUND)

    insertHistory(
        userData['id'],
        'account',
        'Login existing account'
    )

    # Update tg user data to actual
    if tgPhotoUrl is None:
        DB.execute(SQLUser.updateUserTgDataWithoutAvatarUrlById, [str(tgId), tgUsername, userData['id']])
    else:
        DB.execute(SQLUser.updateUserTgDataById, [str(tgId), tgUsername, tgPhotoUrl, userData['id']])

    return new_session(userData, clientBrowser, clientOS, detectGeoLocation(), request.environ['IP_ADDRESS'])


@app.route("/auth", methods=["POST"])
def userAuthByDefault():
    try:
        req = request.json
        emailOrTel = req['emailOrTel']
        password = req['password']

        clientBrowser = req.get('clientBrowser', 'Unknown browser')
        clientOS = req.get('clientOS', 'Unknown OS')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    emailOrTel = emailOrTel.strip().lower()
    password = hash_sha256(password)
    userData = DB.execute(SQLUser.selectUserByEmailOrTelPassword, [emailOrTel, emailOrTel, password])

    if not userData:
        return jsonResponse("Неверные email или пароль", HTTP_INVALID_AUTH_DATA)

    return new_session(userData, clientBrowser, clientOS, detectGeoLocation(), request.environ['IP_ADDRESS'])

@app.route("/auth/code", methods=["POST"])
def userAuthByCodeTg():
    try:
        req = request.json
        secretCode = req['code']
        clientBrowser = req.get('clientBrowser', 'Unknown browser')
        clientOS = req.get('clientOS', 'Unknown OS')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    resp = DB.execute(SQLUser.selectSecretCodeByCodeType, [secretCode, 'auth'])
    if not resp:
        return jsonResponse("Неверный одноразовый код", HTTP_INVALID_AUTH_DATA)
    DB.execute(SQLUser.deleteSecretCodeByUseridCode, [resp['userid'], resp['code']])

    # tgUserData = json.loads(resp['meta'])
    #
    # resp = DB.execute(SQLUser.selectUserByTgUsernameOrTgId, [tgUserData['username'], str(tgUserData['id'])])
    # if not resp:
    #     return jsonResponse("Неверный ", HTTP_INVALID_AUTH_DATA)

    userData = DB.execute(SQLUser.selectUserById, [resp['userid']])
    return new_session(userData, clientBrowser, clientOS, detectGeoLocation(), request.environ['IP_ADDRESS'])


@app.route("", methods=["POST"])
def userRegister():
    try:
        req = request.json
        tgId = req.get('tgId')
        tgUsername = req.get('tgUsername')
        tgHash = req.get('tgHash')
        tgAuthDate = req.get('tgAuthDate')
        tgPhotoUrl = req.get('tgPhotoUrl')
        tgFirstName = req.get('tgFirstName')
        tgLastName = req.get('tgLastName')

        givenName = req['givenName']
        middleName = req['middleName']
        familyName = req['familyName']
        email = req['email']
        tel = req['tel']
        password = req['password']
        clientBrowser = req.get('clientBrowser', 'Unknown browser')
        clientOS = req.get('clientOS', 'Unknown OS')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    email = email.strip().lower()
    tel = re.sub('^8', '+7', tel.strip().lower()).replace('(', '').replace(')', '').replace('-', '')
    password = hash_sha256(password)

    if tgId is not None:
        if not check_tg_auth_hash(tgId, tgFirstName, tgLastName, tgUsername, tgPhotoUrl, tgAuthDate, tgHash):
            return jsonResponse("Хэш авторизации TG не совпадает с данными", HTTP_INVALID_AUTH_DATA)
        resp = DB.execute(SQLUser.selectUserByEmailTelTgusernameTgid, [email, tel, tgUsername, tgId])
    else:
        tgId = None
        tgUsername = None
        resp = DB.execute(SQLUser.selectUserByEmailOrTel, [email, tel])

    if resp:
        return jsonResponse("Email или телефон уже заняты", HTTP_DATA_CONFLICT)

    try:
        print(SQLUser.insertUser, tgId, tgUsername, tgPhotoUrl, email, tel, familyName, givenName, middleName, password)
        userData = DB.execute(SQLUser.insertUser,
                              [tgId, tgUsername, tgPhotoUrl, email, tel, familyName, givenName, middleName, password])
    except Exception as err:
        return jsonResponse(f"Не удалось создать аккаунт. Внутренняя ошибка: {err.__repr__()}", HTTP_INTERNAL_ERROR)

    return new_session(userData, clientBrowser, clientOS, detectGeoLocation(), request.environ['IP_ADDRESS'])


@app.route("/session", methods=["DELETE"])
@login_required
def userSessionDelete(userData):
    try:
        DB.execute(SQLUser.deleteSessionByToken, [userData['session_token']])
    except Exception as err:
        return jsonResponse(f"Сессия не удалена: {err.__repr__()}", HTTP_INTERNAL_ERROR)

    res = jsonResponse("Вы вышли из аккаунта")
    res.set_cookie("session_token", "", max_age=-1, httponly=True, samesite="none", secure=True)

    insertHistory(
        userData['id'],
        'account',
        'Logout'
    )
    return res


@app.route("/sessions/another", methods=["DELETE"])
@login_required
def userAnotherSessionsDelete(userData):
    try:
        DB.execute(SQLUser.deleteAllUserSessionsWithoutCurrent, [userData['id'], userData['session_token']])
    except Exception as err:
        return jsonResponse(f"Сессия не удалена: {err.__repr__()}", HTTP_INTERNAL_ERROR)

    res = jsonResponse("Вы вышли из аккаунта")
    return res


@app.route("/sessions/all")
@login_required
def getAllUserSessions(userData):
    try:
        sessions = DB.execute(SQLUser.selectAllUserSessions, [userData['id']], manyResults=True)
    except:
        return jsonResponse("Не удалось получить список сессий", HTTP_INTERNAL_ERROR)

    for session in sessions:
        if session['token'] == userData['session_token']:
            session['isCurrent'] = True
        else:
            session['isCurrent'] = False
        del session['token']
    return jsonResponse({'sessions': sessions})


@app.route("")
@login_or_none
def userGet(userData):
    try:
        req = request.args
        userId = req.get('id')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if userId is None:  # return self user data
        if userData is None:
            return jsonResponse("Не авторизован", HTTP_INVALID_AUTH_DATA)
        return jsonResponse(userData)

    # get another user data
    if userData['caneditusers']:
        anotherUserData = DB.execute(SQLUser.selectUserById, [userId])
    else:
        anotherUserData = DB.execute(SQLUser.selectAnotherUserById, [userId])
    if not anotherUserData:
        return jsonResponse("Пользователь не найден", HTTP_NOT_FOUND)
    return jsonResponse(anotherUserData)


@app.route("", methods=["PUT"])
@login_required
def userUpdate(userData):
    try:
        req = request.json
        userId = req['id']
        givenName = req.get('givenName')
        familyName = req.get('familyName')
        middleName = req.get('middleName')
        email = req.get('email')
        avatarUrl = req.get('avatarUrl')
        tel = req.get('tel')

        isEmailNotificationsOn = req.get('isEmailNotificationsOn')

        tgUsername = req.get('tgUsername')
        tgId = req.get('tgId')
        canEditOrders = req.get('canEditOrders')
        canEditUsers = req.get('canEditUsers')
        canEditGoods = req.get('canEditGoods')
        canEditHistory = req.get('canEditHistory')
        canExecuteSQL = req.get('canExecuteSQL')
        canEditGlobals = req.get('canEditGlobals')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userData['id']) != str(userId):
        if not userData['caneditusers']:
            return jsonResponse("Недостаточно прав доступа", HTTP_NO_PERMISSIONS)
        userData = DB.execute(SQLUser.selectUserById, [userId])

    if email: email = email.strip().lower()
    if givenName: givenName = givenName.strip()
    if familyName: familyName = familyName.strip()
    if middleName: middleName = middleName.strip()

    isEmailChanged = email != userData['email']

    givenName = givenName or userData['givenname']
    familyName = familyName or userData['familyname']
    middleName = middleName or userData['middlename']
    email = email or userData['email']
    avatarUrl = avatarUrl or userData['avatarurl']
    tel = tel or userData['tel']
    isEmailNotificationsOn = isEmailNotificationsOn if 'isEmailNotificationsOn' in req else userData['isemailnotificationson']
    tgUsername = tgUsername or userData['tgusername']
    tgId = tgId or userData['tgid']
    canEditOrders = canEditOrders or userData['caneditorders']
    canEditUsers = canEditUsers or userData['caneditusers']
    canEditGoods = canEditGoods or userData['caneditgoods']
    canEditHistory = canEditHistory or userData['canedithistory']
    canExecuteSQL = canExecuteSQL or userData['canexecutesql']
    canEditGlobals = canEditGlobals or userData['caneditglobals']

    email = email.strip().lower()
    tel = re.sub('^8', '+7', tel.strip().lower()).replace('(', '').replace(')', '').replace('-', '')

    try:
        if userData['caneditusers']:
            resp = DB.execute(SQLUser.adminUpdateUserById,
                              [tgUsername, tgId, givenName, familyName, middleName, email, tel, isEmailNotificationsOn, avatarUrl,
                               canEditOrders, canEditUsers, canEditGoods,
                               canEditHistory, canExecuteSQL, canEditGlobals, userId])
            if isEmailChanged:
                DB.execute(SQLUser.updateUserRevokeEmailConfirmationByUserId, [userId])
        else:
            resp = DB.execute(SQLUser.updateUserById,
                              [givenName, familyName, middleName, email, tel, isEmailNotificationsOn, avatarUrl, userId])
            if isEmailChanged:
                DB.execute(SQLUser.updateUserRevokeEmailConfirmationByUserId, [userId])
    except Exception as err:
        print(err)
        return jsonResponse("Имя пользователя или email заняты", HTTP_DATA_CONFLICT)

    insertHistory(
        userId,
        'account',
        f'Update by user #{userData["id"]}: {json.dumps(req)}'
    )
    return jsonResponse(resp)


@app.route("", methods=["DELETE"])
@login_required
def userDelete(userData):
    try:
        req = request.json
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if (str(userData['id']) != str(userId)) and (not userData['caneditusers']):
        return jsonResponse("Недостаточно прав доступа", HTTP_NO_PERMISSIONS)

    DB.execute(SQLUser.deleteUserById, [userId])

    insertHistory(
        userId,
        'account',
        f'Delete by user #{userData["id"]}'
    )
    return jsonResponse("Пользователь удален")


@app.route("/all")
def usersGetAll():
    try:
        req = request.args
        search = req.get('search')
        order = req.get('order')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    resp = DB.execute(SQLUser.selectUsersByFilters(req), manyResults=True)
    return jsonResponse({'users': resp})


@app.route("/email/confirmation/send", methods=["POST"])
@login_required
def userConfirmEmailSendMessage(userData):
    email = userData['email']

    userData = DB.execute(SQLUser.selectUserByEmail, [email])
    if not userData:
        return jsonResponse("На этот email не зарегистрирован ни один аккаунт", HTTP_NOT_FOUND)

    secretCode = createSecretCode(userData['id'], "email", hours=24)

    send_email(email,
               f"Подтверждение регистрации на {config['project_name']}",
               emails.confirmEmail(userData['avatarurl'], userData['givenname'] + ' ' + userData['familyname'], secretCode))

    insertHistory(
        userData['id'],
        'account',
        f'Email for confirmation sent'
    )
    return jsonResponse("Ссылка для подтверждения email выслана на почту " + email)


@app.route("/email/confirmation", methods=["POST"])
def userConfirmEmail():
    try:
        req = request.json
        code = req['code']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    resp = DB.execute(SQLUser.updateUserConfirmationBySecretcodeType, [code, "email"])
    if not resp:
        return jsonResponse("Неверный одноразовый код", HTTP_INVALID_AUTH_DATA)

    DB.execute(SQLUser.deleteSecretCodeByCodeType, [code, "email"])

    insertHistory(
        resp['id'],
        'account',
        f'Email confirmed'
    )
    return jsonResponse("Адрес email подтвержден")

@app.route("/password", methods=["PUT"])
@login_required_return_id
def userUpdatePassword(userId):
    try:
        req = request.json
        oldPassword = req['oldPassword']
        newPassword = req['newPassword']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    oldPassword = hash_sha256(oldPassword)
    newPassword = hash_sha256(newPassword)

    resp = DB.execute(SQLUser.selectUserByUserIdPassword, [userId, oldPassword])
    if not resp:
        return jsonResponse("Неверный старый пароль", HTTP_INVALID_AUTH_DATA)

    DB.execute(SQLUser.updateUserPasswordById, [newPassword, userId])

    insertHistory(
        resp['id'],
        'account',
        f'Password changed'
    )
    return jsonResponse("Пароль изменен")
