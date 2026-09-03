# Customer PC configuration
# Change PLC_IP, PLC_PORT and the register range for each machine.

COMPANY_ID = 1
PLC_ID = 1

PLC_IP = "192.168.1.10"
PLC_PORT = 502
SLAVE_ID = 1

SERVER_URL = "http://77.104.95.230:5000"

# Get this value from /etc/scada-edge.env on the server after deployment.
EDGE_TOKEN = "PUT_SERVER_TOKEN_HERE"

# Continuous live reading. Address 0 means Modbus holding register 0.
READ_START = 0
READ_COUNT = 200

READ_INTERVAL = 0.5
COMMAND_INTERVAL = 0.25
HEARTBEAT_INTERVAL = 5
REQUEST_TIMEOUT = 5
RETRY_DELAY = 2
