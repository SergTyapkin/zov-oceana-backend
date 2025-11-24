insertImage = \
    "INSERT INTO images (type, path) " \
    "VALUES (%s, %s) " \
    "RETURNING *"

insertGoodsImage = \
    "INSERT INTO goodsImages (goodsId, imageId, sortingKey) " \
    "VALUES (%s, %s, %s) " \
    "RETURNING *"

# ------------------

selectImageById = \
    "SELECT * FROM images " \
    "WHERE id = %s"

selectGoodsImageById = \
    "SELECT * FROM goodsImages " \
    "WHERE id = %s"

# ------------------

updateGoodsImageSortingKeyById = \
    "UPDATE goodsImages " \
    "SET sortingKey = %s " \
    "WHERE id = %s"

updateImageById = \
    "UPDATE images " \
    "SET type = %s, " \
    "path = %s " \
    "WHERE id = %s"

# ------------------

deleteImageById = \
    "DELETE FROM images " \
    "WHERE id = %s"

deleteGoodsImageById = \
    "DELETE FROM goodsImages " \
    "WHERE id = %s"
