import json

from flask import Blueprint

from src.utils.access import *
from src.constants import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import globals as SQLGlobals

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

