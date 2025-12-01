from flask import Blueprint

from src.blueprints.goods import prepareGoodsData
from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import carts as SQLCarts


app = Blueprint('carts', __name__)


@app.route("")
@login_required
def cartsGet(userData):
    try:
        req = request.args
        userId = req['userId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userData['id']) != str(userId) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав читать корзину другого пользователя', HTTP_NO_PERMISSIONS)

    # get all goods in cart list
    goods = DB.execute(SQLCarts.selectGoodsInCartByUserId, [userId], manyResults=True)
    for goodsOne in goods:
        prepareGoodsData(goodsOne, False, False)

    return jsonResponse({"goods": goods})


@app.route("/goods", methods=["POST"])
@login_required
def addGoodsToCart(userData):
    try:
        req = request.json
        userId = req['userId']
        goodsId = req['goodsId']
        amount = req['amount']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userData['id']) != str(userId) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав добавлять товары в корзину другого пользователя', HTTP_NO_PERMISSIONS)

    try:
        cart = DB.execute(SQLCarts.insertGoodsInCart, [goodsId, userId, amount])
    except Exception as err:
        return jsonResponse(f"Не удалось добавить товар. Скорее всего он уже добавлен: {err.__repr__()}", HTTP_DATA_CONFLICT)

    insertHistory(
        userData['id'],
        'cart',
        f'Added goods to cart: User: #{userId}, Goods: #{goodsId}, #{cart["id"]}'
    )

    return jsonResponse(cart)

@app.route("/goods/set", methods=["POST"])
@login_required
def setGoodsInCart(userData):
    try:
        req = request.json
        userId = req['userId']
        goods = req['goods']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    try:
        for goodsOne in goods:
            if \
                'id' not in goodsOne or \
                'amount' not in goodsOne:
                return jsonResponse(f"Не удалось сериализовать json: не хватает полей в одном из goods", HTTP_INVALID_DATA)
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userData['id']) != str(userId) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав добавлять товары в корзину другого пользователя', HTTP_NO_PERMISSIONS)

    DB.execute(SQLCarts.deleteAllGoodsInCartsByUserId, [userId])
    for goodsOne in goods:
        try:
            DB.execute(SQLCarts.insertGoodsInCart, [goodsOne['id'], userId, goodsOne['amount']])
        except Exception as err:
            print(f"(Warning) Не удалось добавить товар. Скорее всего он уже добавлен: {err.__repr__()}")

    insertHistory(
        userData['id'],
        'cart',
        f'Set all goods in cart: User: #{userId}, Goods: {goods}'
    )

    return jsonResponse("Корзина перезаписана")


@app.route("/goods", methods=["PUT"])
@login_required
def updateGoodsInCartAmount(userData):
    try:
        req = request.json
        userId = req['userId']
        goodsId = req['goodsId']
        amount = req['amount']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    goods = DB.execute(SQLCarts.selectGoodsInCartByUserIdGoodsId, [userId, goodsId])
    if goods is None:
        return jsonResponse("Товар в корзине не найден", HTTP_NOT_FOUND)

    if str(userId) != str(userData['id']) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав менять товары в корзине другого пользователя', HTTP_NO_PERMISSIONS)

    cart = DB.execute(SQLCarts.updateGoodsInCartAmountByUserIdGoodsId, [amount, userId, goodsId])

    insertHistory(
        userData['id'],
        'cart',
        f'Update goods in cart amount: User: #{userId}, Goods: #{goods["id"]} {goods["title"]}: {amount}, #{cart["id"]}'
    )

    return jsonResponse(cart)


@app.route("/goods/many", methods=["DELETE"])
@login_required
def deleteGoodsFromCart(userData):
    try:
        req = request.json
        userId = req['userId']
        goodsIds = req['goodsIds']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    if str(userId) != str(userData['id']) and userData['caneditusers'] is None:
        return jsonResponse('Нет прав менять корзину другого пользователя', HTTP_NO_PERMISSIONS)

    for goodsId in goodsIds:
        DB.execute(SQLCarts.deleteGoodsInCartsByUserIdGoodsId, [userId, goodsId])

    insertHistory(
        userData['id'],
        'cart',
        f'Delete goods from cart: User #{userId}, Goods ids #{goodsIds}'
    )

    return jsonResponse("Товар удален из корзины")
