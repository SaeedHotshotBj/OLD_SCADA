#!/bin/bash
set -e

APP_DIR="/var/www/scada"
REPO="https://github.com/SaeedHotshotBj/OLD_SCADA.git"
SERVICE="scada"
EDGE_SERVICE="scada-edge-gateway"
PORT="5000"
EDGE_PORT="5001"

apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

mkdir -p /var/www

if [ ! -d "$APP_DIR/.git" ]; then
    rm -rf "$APP_DIR"
    git clone "$REPO" "$APP_DIR"
else
    cd "$APP_DIR"
    git fetch origin
    git reset --hard origin/main
fi

cd "$APP_DIR"

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install Flask Flask-SocketIO pandas openpyxl jdatetime pymodbus==2.5.3 simple-websocket requests

./venv/bin/python -c "import database; print('SQLite database initialized:', database.SQLITE_DB)"
./venv/bin/python -c "import edge_gateway; edge_gateway.init_db(); print('Edge gateway database initialized')"

cat > /etc/systemd/system/${SERVICE}.service <<EOF
[Unit]
Description=OLD SCADA Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=SCADA_DB_PATH=${APP_DIR}/scada.db
ExecStart=${APP_DIR}/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/${EDGE_SERVICE}.service <<EOF
[Unit]
Description=OLD SCADA Edge Gateway
After=network.target ${SERVICE}.service

[Service]
User=root
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=SCADA_DB_PATH=${APP_DIR}/scada.db
Environment=SCADA_EDGE_TOKEN=CHANGE_ME
ExecStart=${APP_DIR}/venv/bin/python edge_gateway.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl enable "$EDGE_SERVICE"
systemctl restart "$SERVICE"
systemctl restart "$EDGE_SERVICE"

sleep 2
systemctl --no-pager --full status "$SERVICE" || true
systemctl --no-pager --full status "$EDGE_SERVICE" || true

echo ""
echo "OLD SCADA deployed to $APP_DIR"
echo "SQLite database: $APP_DIR/scada.db"
echo "SCADA service: $SERVICE on port $PORT"
echo "Edge gateway: $EDGE_SERVICE on port $EDGE_PORT"
echo "IMPORTANT: set SCADA_EDGE_TOKEN in this service and the customer EDGE/config.py to the same secret."
