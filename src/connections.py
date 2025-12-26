from src.database.database import Database
from src.config import CONFIG

DB = Database(
    host=CONFIG.db.host,
    port=CONFIG.db.port,
    user=CONFIG.db.user,
    password=CONFIG.db.password,
    dbname=CONFIG.db.name,
)
