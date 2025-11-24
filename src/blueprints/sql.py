from flask import Blueprint

from src.utils.access import *
from src.constants import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import history as SQLHistory

app = Blueprint('sql', __name__)


@app.route("", methods=["POST"])
@login_and_can_execute_sql_required
def executeSQL(userData):
    try:
        req = request.json
        sqlText = req['sql']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    try:
        resp = DB.execute(sqlText, manyResults=True)

        insertHistory(
            userData['id'],
            'sql',
            sqlText,
        )

        return jsonResponse({"response": resp})
    except Exception as err:
        return jsonResponse(str(err), HTTP_INTERNAL_ERROR)

@app.route("/history")
@login_and_can_execute_sql_required
def getSQLHistory(userData):
    try:
        req = request.args
        limit = req.get('limit')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    resp = DB.execute(SQLHistory.selectHistory(req | {"type": "sql"}), manyResults=True)

    return jsonResponse({"history": resp})

@app.route("/history", methods=["DELETE"])
@login_and_can_execute_sql_required
def deleteSQLHistory(userData):
    try:
        req = request.json
        id = req["id"]
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    DB.execute(SQLHistory.deleteHistoryById, [id])

    return jsonResponse("Запись истории удалена")
