insertGoods = \
    "INSERT INTO goods (title, description, fromLocation, amountLeft, amountStep, cost, isOnSale, characters) " \
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) " \
    "RETURNING *"

insertGoodsCategories = \
    "INSERT INTO goodsCategoriess (goodsId, categoryId) " \
    "VALUES (%s, %s) " \
    "RETURNING *"

# ------------------

def selectGoods(filters):
    search = filters.get('search')
    categoryId = filters.get('categoryId')
    costMin = filters.get('costMin')
    costMax = filters.get('costMax')
    isOnSale = filters.get('isOnSale') != False
    amountMin = filters.get('amountMin')
    fromLocation = filters.get('fromLocation')
    limit = filters.get('limit')

    return \
            "SELECT goods.*, categories.id categoryId, category.title categoryTitle FROM goods " \
            "LEFT JOIN goodsCategories ON goods.id = goodsCategories.goodsId " + \
            "LEFT JOIN categories ON goodsCategories.categoryId = category.id " + \
            f"WHERE isOnSale = '{isOnSale}' " + \
            (f"category.id = '{categoryId}' AND " if categoryId is not None else "") + \
            (f"cost <= '{costMax}' AND " if costMax is not None else "") + \
            (f"cost >= '{costMin}' AND " if costMin is not None else "") + \
            (f"amountTotal >= '{amountMin}' AND " if amountMin is not None else "") + \
            (f"fromLocation = '{fromLocation}' AND " if fromLocation is not None else "") + \
            (f"(LOWER(title) LIKE '%%{search.lower()}%%' OR LOWER(description) LIKE '%%{search.lower()}%%') AND " if search is not None else "") + \
            "1 = 1 " + \
            "ORDER BY goods.title " + \
            (f"LIMIT {limit} " if limit is not None else "")

selectGoodsById = \
    "SELECT goods.*, categories.id categoryId, category.title categoryTitle FROM goods " \
    "LEFT JOIN goodsCategories ON goods.id = goodsCategories.goodsId " + \
    "LEFT JOIN categories ON goodsCategories.categoryId = category.id " + \
    "WHERE goods.id = %s "

selectGoodsByCategoryId = \
    "SELECT goods.*, categories.id categoryId, category.title categoryTitle FROM goods " \
    "LEFT JOIN goodsCategories ON goods.id = goodsCategories.goodsId " + \
    "LEFT JOIN categories ON goodsCategories.categoryId = category.id " + \
    "WHERE categories.id = %s "


# ------------------
updateGoodsById = \
    "UPDATE goods SET " \
    "title = %s, " \
    "description = %s, " \
    "createdDate = %s, " \
    "fromLocation = %s, " \
    "amountLeft = %s, " \
    "amountStep = %s, " \
    "cost = %s, " \
    "isOnSale = %s, " \
    "characters = %s " \
    "WHERE id = %s " \
    "RETURNING *"

# ------------------

deleteGoodsById = \
    "DELETE FROM goods " \
    "WHERE id = %s"

deleteGoodsCategoriesById = \
    "DELETE FROM goodsCategories " \
    "WHERE id = %s"

deleteGoodsCategoriesByGoodsIdCategoryId = \
    "DELETE FROM goodsCategories " \
    "WHERE goodsId = %s AND categoryId = %s"
