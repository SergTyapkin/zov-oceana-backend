import os
import random
import string
from io import BytesIO

from PIL import Image
from flask import Blueprint, Response, send_file

from src.config import CONFIG
from src.utils.access import *
from src.utils.utils import *
from src.database.databaseUtils import insertHistory

from src.database.SQLRequests import images as SQLImages

import base64

app = Blueprint('images', __name__)

MAX_SIZE = CONFIG.max_image_size_px


@app.route("/<imageId>.<imageExt>")
@app.route("/<imageId>")
def imageGet(imageId, imageExt=None):
    # Вытаскиваем картинку из БД
    if CONFIG.save_images_to_db:
        if not imageId.isnumeric():
            return jsonResponse("ID изображения должно быть целым числом", HTTP_INVALID_DATA)
        resp = DB.execute(SQLImages.selectImageById, [imageId])
        if (not resp) or ((imageExt is not None) and (resp['type'] != imageExt)):
            return jsonResponse("Изображение не найдено", HTTP_NOT_FOUND)
        # base64Data = resp['base64']
        # imageBytes = base64.b64decode(base64Data)
        imageBytes = resp['bytes']
        imageLen = len(imageBytes)

        res = Response(imageBytes, mimetype=f'image/{resp["type"]}')
        res.headers['Content-Length'] = imageLen
        return res
    
    # Вытаскиваем картинку из папки (только для DEBUG. В проде этим должен заниматься nginx)
    if not CONFIG.debug:
        return jsonResponse("Конфигурацией сервера задано, что он не должен отдавать картинки. Настройте их как раздачу статики через сторонний сервер для статики", HTTP_INTERNAL_ERROR)
    
    filename = f"{imageId}.{imageExt}" if imageExt else imageId
    
    # Проверяем существование файла
    fullpath = os.path.join(os.getcwd(), CONFIG.save_images_folder, filename)
    if not os.path.exists(fullpath):
        return jsonResponse("Изображение не найдено", HTTP_NOT_FOUND)
    
    # Отдаем файл
    try:
        return send_file(fullpath, mimetype=f'image/{imageExt}')
    except Exception as e:
        return jsonResponse(f"Ошибка при отдаче изображения: {str(e)}", HTTP_INTERNAL_ERROR)


_leftLen = len('data:image/')
_rightLen = len(';base64')
@app.route("", methods=["POST"])
@login_and_can_edit_goods_required
def imageGoodsUpload(userData):
    try:
        req = request.json
        dataUrl = req['dataUrl']
        goodsId = req['goodsId']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    [dataUrl, base64Data] = dataUrl.split(',')
    imageType = dataUrl[_leftLen: -_rightLen]

    imageBytes = base64.b64decode(base64Data)
    img = Image.open(BytesIO(imageBytes))  # open image

    (wOrig, hOrig) = img.size
    maxSize = max(wOrig, hOrig)

    if maxSize > MAX_SIZE:  # image bigger than MAX_SIZE. Need to resize
        multiplier = maxSize / MAX_SIZE
        w = int(wOrig / multiplier)
        h = int(hOrig / multiplier)

        img = img.resize((w, h), Image.Resampling.LANCZOS)  # resize to MAX_SIZE

    saveFormat = 'JPEG'
    if img.mode == 'RGBA':
        saveFormat = 'PNG'

    if CONFIG.save_images_to_db:
        optimized = BytesIO()
        img.save(optimized, format=saveFormat, optimize=True, quality=85)
        hex_data = optimized.getvalue()

        imageData = DB.execute(SQLImages.insertImageByBytes, [saveFormat.lower(), hex_data])

        insertHistory(
            userData["id"],
            'image',
            f'Image saved to database: #{imageData["id"]}, format: {saveFormat}, size: {img.size}',
        )
    else:
        chars = string.ascii_letters + string.digits
        randomFileNameUid = ''.join(random.choice(chars) for _ in range(CONFIG.image_uid_generate_len))
        fileName = f"{userData['id']}_{randomFileNameUid}.{saveFormat.lower()}"
        saveFullPath = os.path.join(CONFIG.save_images_folder, fileName)
        img.save(saveFullPath, format=saveFormat, optimize=True, quality=85)

        imageData = DB.execute(SQLImages.insertImageByPath, [saveFormat.lower(), fileName])

        insertHistory(
            userData["id"],
            'image',
            f'Image saved to filesystem at "{saveFullPath}", format: {saveFormat}, size: {img.size}, #{imageData["id"]}',
        )

    maxSortingKey = DB.execute(SQLImages.selectMaxImageSortingKeyByGoodsId, [goodsId])
    maxSortingKey = (maxSortingKey['maxsortingkey'] or 0) if maxSortingKey is not None else 0

    DB.execute(SQLImages.insertGoodsImage, [goodsId, imageData['id'], maxSortingKey + 1])
    return jsonResponse({'id': imageData['id'], 'path': imageData['path']})


@app.route("", methods=["DELETE"])
@login_and_can_edit_goods_required
def imageDelete(userData):
    try:
        req = request.json
        id = req['id']
    except Exception as err:
        return jsonResponse(f"Не удалось сериализовать json: {str(err)}", HTTP_INVALID_DATA)

    if CONFIG.save_images_to_db:
        DB.execute(SQLImages.deleteImageById, [id])

        insertHistory(
            userData['id'],
            'image',
            f'Image deleted from database: #{id}',
        )

        return jsonResponse("Изображение удалено")

    imageData = DB.execute(SQLImages.selectImageById, [id])
    if not imageData:
        return jsonResponse("Изображение не найдено в базе данных", HTTP_NOT_FOUND)

    fileName = imageData['path']
    fullPath = os.path.join(CONFIG.save_images_folder, fileName)
    if not os.path.isfile(fullPath):
        # DB.execute(SQLImages.deleteImageById, [id])
        return jsonResponse("Изображение не найдено в файловой системе", HTTP_NOT_FOUND)

    os.remove(fullPath)

    DB.execute(SQLImages.deleteImageById, [id])

    insertHistory(
        userData['id'],
        'image',
        f'Image deleted from filesystem from "{fullPath}", #{imageData["id"]}',
    )

    return jsonResponse("Изображение удалено")


