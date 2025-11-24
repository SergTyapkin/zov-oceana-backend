import hashlib
import hmac
from functools import wraps

from flask import request

import src.database.SQLRequests.user as SQLUser
from src.connections import DB
from src.constants import *
from src.utils.utils import *


def sha256(string: str) -> str:
    hash = hashlib.sha256(string.encode())
    return hash.hexdigest()
def hmac_sha256(key: str, string: str) -> str:
    h = hmac.new(key.encode("UTF-8"), string.encode(), hashlib.sha256)
    return h.hexdigest()


def compare_user_session_ip(dbSession):
    # print(dbSession['ip'], request.environ['IP_ADDRESS'])
    if dbSession['ip'] == request.environ['IP_ADDRESS']:
        return None  # ok
    return jsonResponse('IP адрес не совпаадет с IP адресом, с которого была открыта сессия', HTTP_INVALID_AUTH_DATA)


def get_logined_userid() -> dict | None:
    token = request.cookies.get('session_token')
    if not token:
        return None
    result = DB.execute(SQLUser.selectUserIdBySessionToken, [token])
    if len(result) == 0:
        return None
    result['session_token'] = token
    return result


def get_logined_user() -> dict | None:
    token = request.cookies.get('session_token')
    if not token:
        return None
    result = DB.execute(SQLUser.selectUserDataBySessionToken, [token])
    if len(result) == 0:
        return None
    result['session_token'] = token
    return result


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        userData = get_logined_user()
        if not userData:
            return jsonResponse("Не авторизован", HTTP_INVALID_AUTH_DATA)
        ipCompareRes = compare_user_session_ip(userData)
        if ipCompareRes:
            return ipCompareRes
        return f(*args, userData, **kwargs)

    return wrapper


def __login_and_property_required(propertyName, denyMessage):
    userData = get_logined_user()
    if not userData:
        return userData, jsonResponse("Не авторизован", HTTP_INVALID_AUTH_DATA)
    ipCompareRes = compare_user_session_ip(userData)
    if ipCompareRes:
        return ipCompareRes
    if not userData[propertyName]:
        return userData, jsonResponse(denyMessage, HTTP_NO_PERMISSIONS)
    return userData, None

def login_and_can_edit_orders_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        (userData, res) = __login_and_property_required('caneditorders', "Нет прав на изменение заказов")
        return res or f(*args, userData, **kwargs)
    return wrapper
def login_and_can_edit_users_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        (userData, res) = __login_and_property_required('caneditusers', "Нет прав на изменение пользователей")
        return res or f(*args, userData, **kwargs)
    return wrapper
def login_and_can_edit_goods_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        (userData, res) = __login_and_property_required('caneditgoods', "Нет прав на изменение товаров")
        return res or f(*args, userData, **kwargs)
    return wrapper
def login_and_can_execute_sql_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        (userData, res) = __login_and_property_required('canexecutesql', "Нет прав на выполнение произвольных SQL-запросов")
        return res or f(*args, userData, **kwargs)
    return wrapper
def login_and_can_edit_history_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        (userData, res) = __login_and_property_required('canedithistory', "Нет прав на изменение и просмотр истории")
        return res or f(*args, userData, **kwargs)
    return wrapper
def login_and_can_edit_globals_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        (userData, res) = __login_and_property_required('caneditglobals', "Нет прав на изменение глобальных настроек")
        return res or f(*args, userData, **kwargs)
    return wrapper

def login_required_return_id(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        userData = get_logined_user()
        if not userData:
            return jsonResponse("Не авторизован", HTTP_INVALID_AUTH_DATA)
        ipCompareRes = compare_user_session_ip(userData)
        if ipCompareRes:
            return ipCompareRes
        return f(*args, userData['id'], **kwargs)

    return wrapper


def login_or_none(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        userData = get_logined_user()
        if not userData or compare_user_session_ip(userData):
            userData = None
        return f(*args, userData, **kwargs)

    return wrapper


def login_or_none_return_id(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        session = get_logined_userid()
        if session is None or compare_user_session_ip(session):
            userId = None
        else:
            userId = session['userid']
        return f(*args, userId, **kwargs)

    return wrapper
