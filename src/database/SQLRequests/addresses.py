insertAddress = \
    "INSERT INTO addresses (userId, title, city, street, house, entrance, code, comment) " \
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) " \
    "RETURNING *"

# ------------------
selectAddressesAll = \
    "SELECT * FROM addresses "

selectAddressById = \
    "SELECT * FROM addresses " \
    "WHERE id = %s"

def selectAddressByUserIdSearch(userId: str, search: str):
    return \
        "SELECT * FROM addresses " \
        "WHERE " \
        f"(LOWER(title) LIKE '%%{search.lower()}%%' OR " \
        f"LOWER(city) LIKE '%%{search.lower()}%%' OR " \
        f"LOWER(street) LIKE '%%{search.lower()}%%' OR " \
        f"LOWER(house) LIKE '%%{search.lower()}%%') " \
        f"AND userId == '{userId}'" \
        "ORDER BY createdDate DESC"

# ------------------

updateAddressById = \
    "UPDATE addresses " \
    "SET title = %s, " \
    "city = %s, " \
    "street = %s, " \
    "house = %s, " \
    "entrance = %s, " \
    "code = %s, " \
    "comment = %s " \
    "WHERE id = %s " \
    "RETURNING *"

# ------------------

deleteAddressById = \
    "DELETE FROM addresses " \
    "WHERE id = %s"
