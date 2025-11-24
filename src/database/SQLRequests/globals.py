# ----- INSERTS -----
insertGlobals = \
    "INSERT INTO globals (isOnMaintenance) " \
    "VALUES (FALSE) " \
    f"RETURNING *"

# ----- SELECTS -----
selectGlobals = \
    f"SELECT * FROM globals"

# ----- UPDATES -----
updateGlobals = \
    "UPDATE globals SET " \
    "isOnMaintenance = %s " \
    "RETURNING *"
