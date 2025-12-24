insertCategory = \
    "INSERT INTO categories (title, description, imageId) " \
    "VALUES (%s, %s, %s) " \
    "RETURNING *"

# ------------------
selectCategoriesAll = \
    "SELECT * FROM categories " \
    "ORDER BY id"

selectCategoryById = \
    "SELECT * FROM categories " \
    "WHERE id = %s " \
    "ORDER BY id"

def selectCategoryBySearch(search: str):
    return \
        "SELECT * FROM categories " \
        "WHERE " \
        f"LOWER(title) LIKE '%%{search.lower()}%%' OR " \
        "ORDER BY title"

# ------------------

updateCategoryById = \
    "UPDATE categories " \
    "SET title = %s, " \
    "description = %s, " \
    "imageId = %s " \
    "WHERE id = %s " \
    "RETURNING *"

# ------------------

deleteCategoryById = \
    "DELETE FROM categories " \
    "WHERE id = %s"
