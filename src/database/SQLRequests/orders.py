insertOrder = \
    "INSERT INTO orders (number, userId, addressId, secretCode) " \
    "VALUES (%s, %s, %s, %s) " \
    "RETURNING *"

insertOrderGoods = \
    "INSERT INTO ordersGoods (orderId, goodsId, cost, amount) " \
    "VALUES (%s, %s, %s, %s) " \
    "RETURNING *"

# ------------------

selectOrderById = \
    "SELECT orders.*, ordersGoods.cost as orderGoodsCost, ordersGoods.goodsAmount orderGoodsAmount, goods.title as goodsTitle, goods.previewUrl as goodsPreviewUrl, goods.isOnSale as goodsIsOnSale FROM orders " \
    "JOIN ordersGoods ON orders.id = ordersGoods.orderId " \
    "JOIN goods ON ordersGoods.goodsId = goods.id " \
    "WHERE orders.id = %s"

selectOrdersByGoodsId = \
    "SELECT orders.*, ordersGoods.cost as orderGoodsCost, ordersGoods.goodsAmount orderGoodsAmount, goods.title as goodsTitle, goods.previewUrl as goodsPreviewUrl, goods.isOnSale as goodsIsOnSale FROM orders " \
    "JOIN ordersGoods ON orders.id = ordersGoods.orderId " \
    "JOIN goods ON ordersGoods.goodsId = goods.id " \
    "WHERE goods.id = %s"

selectUserOrdersByUserId = \
    "SELECT orders.*, ordersGoods.cost as orderGoodsCost, ordersGoods.goodsAmount orderGoodsAmount, goods.title as goodsTitle, goods.previewUrl as goodsPreviewUrl, goods.isOnSale as goodsIsOnSale FROM orders " \
    "JOIN ordersGoods ON orders.id = ordersGoods.orderId " \
    "JOIN goods ON ordersGoods.goodsId = goods.id " \
    "WHERE orders.id = %s"

selectMaxOrderNumber = \
    "SELECT MAX(number) as maxNumber " \
    "FROM orders"

# ------------------

updateOrderById = \
    "UPDATE orders " \
    "SET addressId = %s, " \
    "updatedDate = NOW(), " \
    "status = %s, " \
    "trackingCode = %s " \
    "WHERE id = %s " \
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
