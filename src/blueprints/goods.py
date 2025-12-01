import json

from flask import Blueprint

from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import goods as SQLGoods
from src.database.SQLRequests import images as SQLImages

app = Blueprint('goods', __name__)


def prepareGoodsData(goodsData, addImages = True, addCategories = True):
    if addImages:
        imagesData = DB.execute(SQLImages.selectGoodsImagesByGoodsId, [goodsData['id']], manyResults=True)
        goodsData['images'] = imagesData
    if addCategories:
        categoriesData = DB.execute(SQLGoods.selectCategoriesByGoodsId, [goodsData['id']], manyResults=True)
        goodsData['categories'] = categoriesData

    try:
        goodsData['characters'] = json.loads(goodsData['characters'])
    except:
        goodsData['characters'] = None


@app.route("")
def goodsGet():
    try:
        req = request.args
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    goodsData = DB.execute(SQLGoods.selectGoodsById, [id])
    prepareGoodsData(goodsData)

    return jsonResponse(goodsData)

@app.route("/all")
def goodsGetAll():
    try:
        req = request.args
        search = req.get('search')
        categoryId = req.get('categoryId')
        costMin = req.get('costMin')
        costMax = req.get('costMax')
        isOnSale = req.get('isOnSale')
        isWeighed = req.get('isWeighed')
        amountMin = req.get('amountMin')
        fromLocation = req.get('fromLocation')
        limit = req.get('limit')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    goods = DB.execute(SQLGoods.selectGoods(req), [], manyResults=True)
    for goodsOne in goods:
        prepareGoodsData(goodsOne)
    return jsonResponse({'goods': goods})


@app.route("", methods=["POST"])
@login_and_can_edit_goods_required
def goodsCreate(userData):
    try:
        req = request.json
        title = req['title']
        description = req.get('description')
        fromLocation = req['fromLocation']
        amountLeft = req['amountLeft']
        amountStep = req['amountStep']
        amountMin = req['amountMin']
        isWeighed = req['isWeighed']
        cost = req['cost']
        isOnSale = True if req.get('isOnSale') is None else req.get('isOnSale')
        characters = req.get('characters')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    try:
        characters = json.dumps(characters)
    except:
        characters = None
    goods = DB.execute(SQLGoods.insertGoods, [title, description, fromLocation, amountLeft, amountStep, amountMin, cost, isWeighed, isOnSale, characters])

    insertHistory(
        userData["id"],
        'goods',
        f'Create goods: "{goods["title"]}" #{goods["id"]}'
    )

    return jsonResponse(goods)


@app.route("", methods=["POST"])
@login_and_can_edit_goods_required
def addGoodsToCategory(userData):
    try:
        req = request.json
        goodsId = req['goodsId']
        categoryId = req['categoryId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    goods = DB.execute(SQLGoods.insertGoodsCategories, [goodsId, categoryId])

    insertHistory(
        userData["id"],
        'goods',
        f'Goods added to category: "#{goods["id"]}, to #"{categoryId}"'
    )

    return jsonResponse(goods)


@app.route("", methods=["PUT"])
@login_and_can_edit_goods_required
def goodsUpdate(userData):
    try:
        req = request.json
        id = req['id']

        title = req.get('title')
        description = req.get('description')
        fromLocation = req.get('fromLocation')
        amountLeft = req.get('amountLeft')
        amountStep = req.get('amountStep')
        amountMin = req.get('amountMin')
        cost = req.get('cost')
        isWeighed = req.get('isWeighed')
        isOnSale = req.get('isOnSale')
        characters = req.get('characters')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    goodsData = DB.execute(SQLGoods.selectGoodsById, [id])
    if goodsData is None:
        return jsonResponse("Товар не найден", HTTP_NOT_FOUND)

    if title is None: title = goodsData['title']
    if description is None: description = goodsData['description']
    if fromLocation is None: fromLocation = goodsData['fromlocation']
    if amountLeft is None: amountLeft = goodsData['amountleft']
    if amountStep is None: amountStep = goodsData['amountstep']
    if amountMin is None: amountMin = goodsData['amountmin']
    if cost is None: cost = goodsData['cost']
    if isWeighed is None: isWeighed = goodsData['isweighed']
    if isOnSale is None: isOnSale = goodsData['isonsale']
    if characters is None: characters = goodsData['characters']

    goods = DB.execute(SQLGoods.updateGoodsById, [title, description, fromLocation, amountLeft, amountStep, amountMin, cost, isWeighed, isOnSale, characters, id])

    insertHistory(
        userData["id"],
        'goods',
        f'Update goods: {json.dumps(req)}'
    )

    return jsonResponse(goods)


@app.route("", methods=["DELETE"])
@login_and_can_edit_goods_required
def goodsDelete(userData):
    try:
        req = request.json
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    DB.execute(SQLGoods.deleteGoodsById, [id])

    insertHistory(
        userData["id"],
        'goods',
        f'Delete goods: #{id}'
    )

    return jsonResponse("Товар удален")



@app.route("", methods=["DELETE"])
@login_and_can_edit_goods_required
def deleteGoodsFromCategory(userData):
    try:
        req = request.json
        goodsId = req['goodsId']
        categoryId = req['categoryId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    DB.execute(SQLGoods.deleteGoodsCategoriesByGoodsIdCategoryId, [goodsId, categoryId])

    insertHistory(
        userData["id"],
        'goods',
        f'Delete goods from category: #{goodsId} from #{categoryId}'
    )

    return jsonResponse("Товар удален из категории")


