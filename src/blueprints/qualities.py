import json

from flask import Blueprint, request
from src.connections import DB
from src.constants import HTTP_NO_PERMISSIONS, HTTP_INVALID_DATA, HTTP_NOT_FOUND
from src.database.SQLRequests import qualities as SQLQualities
from src.database.databaseUtils import insertHistory
from src.utils.access import login_and_can_edit_globals_required, login_required, login_and_can_edit_partners_required
from src.utils.utils import jsonResponse

app = Blueprint('qualities', __name__)


@app.route("/", methods=["GET"])
def getQuality():
    try:
        req = request.args
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)
    quality = DB.execute(SQLQualities.selectQualityByid, [id])
    return jsonResponse(quality)

@app.route("/all", methods=["GET"])
def getQualities():
    qualities = DB.execute(SQLQualities.selectAllQualities, [], manyResults=True)
    return jsonResponse({"qualities": qualities})

@app.route("/", methods=["POST"])
@login_and_can_edit_globals_required
def createQuality(userData):
    try:
        req = request.json
        title = req['title']
        branchDeepForQuality = req['branchDeepForQuality']
        percentForQuality = req['percentForQuality']
        activeCountRequirement = req['activeCountRequirement']
        branchesCountRequirement = req['branchesCountRequirement']
        branchesValuesRequirement = req['branchesValuesRequirement']
        totalPersonalBonusesRequirement = req['totalPersonalBonusesRequirement']
        qualityBonusValue = req['qualityBonusValue']
        qualityBonusMaxCount = req['qualityBonusMaxCount']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    quality = DB.execute(SQLQualities.insertQuality, [title, branchDeepForQuality, percentForQuality, activeCountRequirement,
                                                      branchesCountRequirement, branchesValuesRequirement, totalPersonalBonusesRequirement,
                                                      qualityBonusValue, qualityBonusMaxCount])
    insertHistory(
        userData['id'],
        'quality',
        f'Created quality #{quality['id']}: {json.dumps(req)}'
    )
    return jsonResponse(quality)

@app.route("/", methods=["PUT"])
@login_and_can_edit_globals_required
def updateQuality(userData):
    try:
        req = request.json
        id = req['id']
        title = req.get('title')
        branchDeepForQuality = req.get('branchDeepForQuality')
        percentForQuality = req.get('percentForQuality')
        activeCountRequirement = req.get('activeCountRequirement')
        branchesCountRequirement = req.get('branchesCountRequirement')
        branchesValuesRequirement = req.get('branchesValuesRequirement')
        totalPersonalBonusesRequirement = req.get('totalPersonalBonusesRequirement')
        qualityBonusValue = req.get('qualityBonusValue')
        qualityBonusMaxCount = req.get('qualityBonusMaxCount')
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    quality = DB.execute(SQLQualities.selectQualityById, [id])
    if not quality:
        return jsonResponse(f"Квалификация не найдена: {str(err)}", HTTP_NOT_FOUND)

    title = title or quality['title']
    branchDeepForQuality = branchDeepForQuality if branchDeepForQuality is not None else quality['branchdeepforquality']
    percentForQuality = percentForQuality if percentForQuality is not None else quality['percentforquality']
    activeCountRequirement = activeCountRequirement if activeCountRequirement is not None else quality['activecounttequirement']
    branchesCountRequirement = branchesCountRequirement if branchesCountRequirement is not None else quality['branchescountrequirement']
    branchesValuesRequirement = branchesValuesRequirement if branchesValuesRequirement is not None else quality['branchesvaluesrequirement']
    totalPersonalBonusesRequirement = totalPersonalBonusesRequirement if totalPersonalBonusesRequirement is not None else quality['totalpersonalbonusesrequirement']
    qualityBonusValue = qualityBonusValue if qualityBonusValue is not None else quality['qualitybonusvalue']
    qualityBonusMaxCount = qualityBonusMaxCount if qualityBonusMaxCount is not None else quality['qualitybonusmaxcount']

    quality = DB.execute(SQLQualities.updateQualityById, [title, branchDeepForQuality, percentForQuality, activeCountRequirement,
                                                      branchesCountRequirement, branchesValuesRequirement, totalPersonalBonusesRequirement,
                                                      qualityBonusValue, qualityBonusMaxCount, id])
    insertHistory(
        userData['id'],
        'quality',
        f'Updated quality #{id}: {json.dumps(req)}'
    )
    return jsonResponse(quality)


@app.route("/", methods=["DELETE"])
@login_and_can_edit_globals_required
def deleteQuality(userData):
    try:
        req = request.json
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    DB.execute(SQLQualities.deleteQualityById, [id])
    insertHistory(
        userData['id'],
        'quality',
        f'Deleted quality #{id}'
    )
    return jsonResponse("Квалификация удалена")

