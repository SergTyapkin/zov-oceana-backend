# ----- INSERTS -----

insertGoodsInCart = \
    "INSERT INTO goodsInCarts (goodsId, userId, amount) " \
    "VALUES (%s, %s, %s) " \
    "RETURNING *"

# ----- SELECTS -----

selectGoodsInCartById = \
    "SELECT * FROM goodsInCarts " \
    "WHERE id = %s"

selectGoodsInCartByUserId = \
    "SELECT * FROM goodsInCarts " \
    "JOIN goods ON goods.id = goodsInCarts.goodsId " \
    "WHERE userId = %s"

selectGoodsInCartByUserIdGoodsId = \
    "SELECT * FROM goodsInCarts " \
    "JOIN goods ON goods.id = goodsInCarts.goodsId " \
    "WHERE userId = %s " \
    "AND goodsId = %s "

selectGoodsInCartUsersCountByGoodsId = \
    "SELECT COUNT(*) as count FROM goodsInCarts " \
    "WHERE goodsId = %s"


# ----- UPDATES ------

updateGoodsInCartAmountByUserIdGoodsId = \
    "UPDATE goodsInCarts " \
    "SET amount = %s " \
    "WHERE userId = %s " \
    "AND goodsId = %s " \
    "RETURNING *"

# ----- DELETES -----

deleteGoodsInCartsByUserIdGoodsId = \
    "DELETE FROM goodsInCarts " \
    "WHERE userId = %s " \
    "AND goodsId = %s"

deleteAllGoodsInCartsByUserId = \
    "DELETE FROM goodsInCarts " \
    "WHERE userId = %s"

