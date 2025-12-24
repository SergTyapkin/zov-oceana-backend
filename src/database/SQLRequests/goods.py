insertGoods = \
    "INSERT INTO goods (title, description, fromLocation, amountLeft, amountStep, amountMin, cost, isWeighed, isOnSale, characters) " \
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " \
    "RETURNING *"

insertGoodsCategories = \
    "INSERT INTO goodsCategoriess (goodsId, categoryId) " \
    "VALUES (%s, %s) " \
    "RETURNING *"

# ------------------

def selectGoods(filters, isAdmin=False):
    search = filters.get('search')
    categoryId = filters.get('categoryId')
    costMin = filters.get('costMin')
    costMax = filters.get('costMax')
    if isAdmin:
        isOnSale = filters.get('isOnSale') != 'false' if filters.get('isOnSale') else None
    else:
        isOnSale = filters.get('isOnSale') != 'false'
    amountMin = filters.get('amountMin')
    isWeighed = filters.get('isWeighed') != 'false' if filters.get('isWeighed') else None
    fromLocation = filters.get('fromLocation')
    limit = filters.get('limit')

    return \
            "SELECT * FROM goods " \
            "WHERE " + \
            (f"isOnSale = '{isOnSale}' AND " if isOnSale is not None else "") + \
            (f"isWeighed = '{isWeighed}' AND " if isWeighed is not None else "") + \
            (f"categories.id = '{categoryId}' AND " if categoryId is not None else "") + \
            (f"cost <= '{costMax}' AND " if costMax is not None else "") + \
            (f"cost >= '{costMin}' AND " if costMin is not None else "") + \
            (f"amountTotal >= '{amountMin}' AND " if amountMin is not None else "") + \
            (f"fromLocation = '{fromLocation}' AND " if fromLocation is not None else "") + \
            (f"(LOWER(title) LIKE '%%{search.lower()}%%' OR LOWER(description) LIKE '%%{search.lower()}%%') AND " if search is not None else "") + \
            "1 = 1 " + \
            "ORDER BY goods.title " + \
            (f"LIMIT {limit} " if limit is not None else "")

def selectGoodsByIds(goodsIds):
    return \
        "SELECT * FROM goods " \
        "WHERE id IN ('" + "','".join(map(str, goodsIds)) + "')"

selectGoodsById = \
    "SELECT * FROM goods " \
    "WHERE id = %s "

selectCategoriesByGoodsId = \
    "SELECT categories.* FROM categories " \
    "JOIN goodsCategories ON categories.id = goodsCategories.categoryId " \
    "JOIN goods ON goodsCategories.goodsId = goods.id " \
    "WHERE goodsId = %s"

selectGoodsByCategoryId = \
    "SELECT goods.* FROM categories " \
    "JOIN goodsCategories ON goodsCategories.categoryId = categories.id " + \
    "JOIN goods ON goods.id = goodsCategories.goodsId " + \
    "WHERE categoryId = %s "


# ------------------
updateGoodsById = \
    "UPDATE goods SET " \
    "title = %s, " \
    "description = %s, " \
    "fromLocation = %s, " \
    "amountLeft = %s, " \
    "amountStep = %s, " \
    "amountMin = %s, " \
    "cost = %s, " \
    "isWeighed = %s, " \
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
