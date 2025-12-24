from src.database.SQLRequests.user import userPublicColumns

insertOrder = \
    "INSERT INTO orders (number, userId, addressId, addressTextCopy, commentTextCopy, secretCode) " \
    "VALUES (%s, %s, %s, %s, %s, %s) " \
    "RETURNING *"

insertOrderGoods = \
    "INSERT INTO ordersGoods (orderId, goodsId, cost, amount) " \
    "VALUES (%s, %s, %s, %s) " \
    "RETURNING *"

# ------------------

selectOrderById = \
    "SELECT * FROM orders " \
    "WHERE id = %s"

selectAllOrdersWithUsers = \
    f"SELECT {userPublicColumns}, orders.* FROM orders " \
    "LEFT JOIN users ON orders.userId = users.id " \
    "ORDER BY createdDate DESC"

selectOrderByNumber = \
    "SELECT * FROM orders " \
    "WHERE number = %s"

selectUserOrdersByUserId = \
    "SELECT * FROM orders " \
    "WHERE userId = %s" \
    "ORDER BY createdDate DESC"

selectMaxOrderId = \
    "SELECT MAX(id) as maxId " \
    "FROM orders"

selectOrderGoodsByOrderId = \
    "SELECT goods.*, ordersGoods.*, goods.id FROM ordersGoods " \
    "JOIN goods ON ordersGoods.goodsId = goods.id " \
    "WHERE orderId = %s"

# ------------------

updateOrderById = \
    "UPDATE orders " \
    "SET addressId = %s, " \
    "addressTextCopy = %s, " \
    "commentTextCopy = %s, " \
    "updatedDate = NOW(), " \
    "status = %s, " \
    "trackingCode = %s " \
    "WHERE id = %s " \
    "RETURNING *"

updateOrderByNumber = \
    "UPDATE orders " \
    "SET addressId = %s, " \
    "addressTextCopy = %s, " \
    "commentTextCopy = %s, " \
    "updatedDate = NOW(), " \
    "status = %s, " \
    "trackingCode = %s " \
    "WHERE number = %s " \
    "RETURNING *"

updateOrderStatusById = \
    "UPDATE orders " \
    "SET status = %s, " \
    "updatedDate = NOW() " \
    "WHERE id = %s " \
    "RETURNING *"

updateOrderGoodsByOrderIdGoodsId = \
    "UPDATE ordersGoods " \
    "SET cost = %s," \
    "amount = %s " \
    "WHERE orderId = %s " \
    "AND goodsId = %s " \
    "RETURNING *"

# ------------------

deleteOrderById = \
    "DELETE FROM orders " \
    "WHERE id = %s"

deleteOrderGoodsByOrderIdGoodsId = \
    "DELETE FROM ordersGoods " \
    "WHERE orderId = %s " \
    "AND goodsId = %s "

deleteAllOrderGoodsByOrderId = \
    "DELETE FROM ordersGoods " \
    "WHERE orderId = %s "
