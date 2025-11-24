from flask import Blueprint

from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import categories as SQLCategories


app = Blueprint('categories', __name__)


@app.route("")
def categoriesGet():
    # try:
        # req = request.args
    # except Exception as err:
    #     return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    # get all categories list
    categories = DB.execute(SQLCategories.selectCategoriesAll, [], manyResults=True)
    return jsonResponse({"categories": categories})


@app.route("", methods=["POST"])
@login_and_can_edit_goods_required
def categoryCreate(userData):
    try:
        req = request.json
        title = req['title']
        description = req.get('city')
        imageId = req.get('street')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    category = DB.execute(SQLCategories.insertCategory, [title, description, imageId])

    insertHistory(
        userData['id'],
        'category',
        f'Creates category: "{category["title"]}" #{category["id"]}'
    )

    return jsonResponse(category)


@app.route("", methods=["PUT"])
@login_and_can_edit_goods_required
def categoryUpdate(userData):
    try:
        req = request.json
        id = req['id']
        title = req.get('title')
        description = req.get('description')
        imageId = req.get('imageId')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    categoryData = DB.execute(SQLCategories.selectCategoryById, [id])
    if categoryData is None:
        return jsonResponse("Категория не найдена", HTTP_NOT_FOUND)

    if title is None: title = categoryData['title']
    if description is None: description = categoryData['description']
    if imageId is None and 'imageId' not in req: imageId = categoryData['imageId']

    category = DB.execute(SQLCategories.updateCategoryById, [title, description, imageId, id])

    insertHistory(
        userData['id'],
        'category',
        f'Update category: {json.dumps(req)}'
    )

    return jsonResponse(category)


@app.route("", methods=["DELETE"])
@login_and_can_edit_goods_required
def categoryDelete(userData):
    try:
        req = request.json
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    DB.execute(SQLCategories.deleteCategoryById, [id])

    insertHistory(
        userData['id'],
        'category',
        f'Delete category: #{id}'
    )

    return jsonResponse("Категория удалена")
