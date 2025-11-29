from flask import Blueprint

from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import addresses as SQLAddresses


app = Blueprint('addresses', __name__)


@app.route("")
@login_and_can_edit_users_required
def addressGet(userData):
    try:
        req = request.args
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    addressData = DB.execute(SQLAddresses.selectAddressById, [id])
    return jsonResponse(addressData)


@app.route("/user")
@login_required
def addressesUserGet(userData):
    try:
        req = request.args
        userId = req['userId']
        search = req.get('search')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userData['id']) != str(userId) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав читать адреса другого пользователя', HTTP_NO_PERMISSIONS)

    if search is None: search = ''

    # get all addresses list
    addresses = DB.execute(SQLAddresses.selectAddressByUserIdSearch(userId, search), [], manyResults=True)
    return jsonResponse({"addresses": addresses})


@app.route("", methods=["POST"])
@login_required
def addressCreate(userData):
    try:
        req = request.json
        title = req['title']
        city = req.get('city')
        street = req.get('street')
        house = req.get('house')
        entrance = req.get('entrance')
        code = req.get('code')
        comment = req.get('comment')
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userData['id']) != str(userId) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав читать адреса другого пользователя', HTTP_NO_PERMISSIONS)

    address = DB.execute(SQLAddresses.insertAddress, [userId, title, city, street, house, entrance, code, comment])

    insertHistory(
        userData['id'],
        'address',
        f'Creates address: "{address["title"]}" #{address["id"]}'
    )

    return jsonResponse(address)


@app.route("", methods=["PUT"])
@login_required
def addressUpdate(userData):
    try:
        req = request.json
        id = req['id']
        title = req.get('title')
        city = req.get('city')
        street = req.get('street')
        house = req.get('house')
        entrance = req.get('entrance')
        code = req.get('code')
        comment = req.get('comment')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    addressData = DB.execute(SQLAddresses.selectAddressById, [id])
    if addressData is None:
        return jsonResponse("Адрес не найден", HTTP_NOT_FOUND)

    if str(addressData['userid']) != str(userData['id']) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав менять адрес другого пользователя', HTTP_NO_PERMISSIONS)

    if title is None: title = addressData['title']
    if city is None: city = addressData['city']
    if street is None: street = addressData['street']
    if house is None: house = addressData['house']
    if entrance is None: entrance = addressData['entrance']
    if code is None: code = addressData['code']
    if comment is None: comment = addressData['comment']

    address = DB.execute(SQLAddresses.updateAddressById, [title, city, street, house, entrance, code, comment])

    insertHistory(
        userData['id'],
        'address',
        f'Update address: {json.dumps(req)}'
    )

    return jsonResponse(address)


@app.route("", methods=["DELETE"])
@login_required
def addressDelete(userData):
    try:
        req = request.json
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    addressData = DB.execute(SQLAddresses.selectAddressById, [id])
    if addressData is None:
        return jsonResponse("Адрес не найден", HTTP_NOT_FOUND)

    if str(addressData['userid']) != str(userData['id']) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав менять адрес другого пользователя', HTTP_NO_PERMISSIONS)

    DB.execute(SQLAddresses.deleteAddressById, [id])

    insertHistory(
        userData['id'],
        'address',
        f'Delete address: #{id}'
    )

    return jsonResponse("Адрес удален")
