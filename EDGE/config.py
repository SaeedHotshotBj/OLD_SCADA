# Customer-side SCADA Edge configuration
# Edit only the values in this file for each customer PLC.

COMPANY_ID = 1
PLC_ID = 1
PLC_IP = "192.168.1.10"
PLC_PORT = 502
SLAVE_ID = 1

# Public URL of the OLD_SCADA server
SERVER_URL = "http://77.104.95.230"

# Edge identity/token. Change this per customer installation.
EDGE_TOKEN = "CHANGE_ME"

# PLC read range. The current OLD_SCADA project reads holding registers 0..60.
READ_START = 0
READ_COUNT = 61

# Polling intervals (seconds)
READ_INTERVAL = 0.5
COMMAND_INTERVAL = 0.5
HEARTBEAT_INTERVAL = 5

REQUEST_TIMEOUT = 5
RETRY_DELAY = 2
