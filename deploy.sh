#!/bin/bash
set -e

APP_DIR="/var/www/scada"
REPO="https://github.com/SaeedHotshotBj/OLD_SCADA.git"
SERVICE="scada"
PORT="5000"

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

if [ ! -f requirements.txt ]; then
    echo "ERROR: requirements.txt not found in $APP_DIR"
    exit 1
fi

apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

cat > /etc/systemd/system/${SERVICE}.service <<EOF
[Unit]
Description=OLD SCADA Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=${APP_DIR}
Environment="PYTHONUNBUFFERED=1"
ExecStart=${APP_DIR}/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

sleep 2
systemctl --no-pager --full status "$SERVICE" || true

echo ""
echo "OLD SCADA deployed to $APP_DIR"
echo "Service: $SERVICE"
echo "Port: $PORT"
