import random
import uuid

from src.connections import DB
from src.database.SQLRequests import history as SQLHistory
from src.database.SQLRequests import user as SQLUser


def insertHistory(userId: str, type: str, text: str):
    DB.execute(SQLHistory.insertHistory, [userId, type, text])


def createSecretCode(userId: str, type: str, meta: str = None, hours=1):
    DB.execute(SQLUser.deleteExpiredSecretCodes)

    secretCode = DB.execute(SQLUser.selectSecretCodeByUserIdType, [str(userId), type])
    if secretCode:
        code = secretCode['code']
        return code

    # create new
    if type == "login":
        random.seed()
        code = str(random.randint(1, 999999)).zfill(6)
    else:
        code = str(uuid.uuid4())

    DB.execute(SQLUser.insertSecretCode, [str(userId), code, type, meta, hours])

    return code
