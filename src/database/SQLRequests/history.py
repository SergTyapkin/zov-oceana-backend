insertHistory = \
    "INSERT INTO history (userId, type, text) " \
    "VALUES (%s, %s, %s) " \
    "RETURNING *"

# ------------------

def selectHistory(filters):
    userId = filters.get('userId')
    type = filters.get('type')
    search = filters.get('search')
    dateStart = filters.get('dateStart')
    dateEnd = filters.get('dateEnd')
    limit = filters.get('limit')

    return "SELECT * FROM history " \
        "WHERE " + \
        (f"date >= '{dateStart}' AND " if dateStart is not None else "") + \
        (f"cameDate < '{dateEnd}' AND " if dateEnd is not None else "") + \
        (f"userId = '{userId}' AND " if userId is not None else "") + \
        (f"LOWER(type) LIKE '%%{type.lower()}%%' AND " if type is not None else "") + \
        (f"LOWER(text) LIKE '%%{search.lower()}%%' AND " if search is not None else "") + \
        "1 = 1 " \
        "ORDER BY date DESC " + \
        (f"LIMIT {limit} " if limit is not None else "")
# ------------------

deleteHistoryById = \
    "DELETE FROM history " \
    "WHERE id = %s"
