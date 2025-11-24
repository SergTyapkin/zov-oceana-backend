from flask import Blueprint

from src.utils.access import *
from src.utils.utils import *

from src.database.SQLRequests import history as SQLHistory

app = Blueprint('history', __name__)

@app.route("")
@login_and_can_edit_history_required
def history():
    try:
        req = request.args

        userId = req.get('userId')
        search = req.get('search')
        type = req.get('type')
        dateStart = req.get('dateStart')
        dateEnd = req.get('dateEnd')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {err.__repr__()}", HTTP_INVALID_DATA)

    # get history list by filters
    history = DB.execute(SQLHistory.selectHistory(req), [], manyResults=True)
    return jsonResponse({"history": history})
