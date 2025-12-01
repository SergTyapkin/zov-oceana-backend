import json

from flask import Blueprint

from src.blueprints.goods import prepareGoodsData
from src.utils.access import *
from src.constants import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import globals as SQLGlobals
from src.database.SQLRequests import goods as SQLGoods
from src.database.SQLRequests import categories as SQLCategories

app = Blueprint('globals', __name__)


@app.route("", methods=["PUT"])
@login_and_can_edit_globals_required
def globalsUpdate(userData):
    try:
        req = request.json
        isOnMaintenance = req.get('isOnMaintenance')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    globalsData = DB.execute(SQLGlobals.selectGlobals)

    isOnMaintenance = isOnMaintenance if isOnMaintenance is not None else globalsData['isonmaintenance']

    resp = DB.execute(SQLGlobals.updateGlobals, [isOnMaintenance])

    insertHistory(
        userData['id'],
        'globals',
        f'Set globals: {json.dumps(req)}'
    )
    return jsonResponse(resp)

@app.route("")
def getGlobals():
    try:
        req = request.args
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    globalsData = DB.execute(SQLGlobals.selectGlobals)

    # Add goods on landing data
    goodsData = DB.execute(SQLGoods.selectGoodsByIds(globalsData['goodsidsonlanding']), [], manyResults=True)
    categoriesData = DB.execute(SQLCategories.selectCategoriesAll, [], manyResults=True)

    for goodsOne in goodsData:
        prepareGoodsData(goodsOne, True, False)

    globalsData['goodsonlanding'] = goodsData
    globalsData['categories'] = categoriesData

    return jsonResponse(globalsData)

