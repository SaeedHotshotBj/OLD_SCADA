import os

# SQLite database used by the server.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.environ.get("SCADA_DB_PATH", os.path.join(BASE_DIR, "scada.db"))
