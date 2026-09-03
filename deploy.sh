#!/usr/bin/env bash
set -e
APP_DIR=/var/www/global
cd "$APP_DIR"

apt-get update
apt-get install -y python3 python3-venv python3-pip git openssl

python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

mkdir -p "$APP_DIR"
venv/bin/python -c 'import app; app.init_db()'

if [ ! -f /etc/scada-edge.env ]; then
  TOKEN=$(openssl rand -hex 32)
  cat > /etc/scada-edge.env <<EOF
SCADA_EDGE_TOKEN=$TOKEN
SCADA_DB_PATH=$APP_DIR/scada.db
PORT=5000
EOF
  chmod 600 /etc/scada-edge.env
fi

cat > /etc/systemd/system/old-scada.service <<EOF
[Unit]
Description=OLD SCADA Server
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/scada-edge.env
ExecStart=$APP_DIR/venv/bin/waitress-serve --listen=0.0.0.0:5000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable old-scada
systemctl restart old-scada

echo
echo 'OLD SCADA server is running on port 5000.'
echo 'Open: http://77.104.95.230:5000'
echo
echo 'IMPORTANT: copy this token into EDGE/config.py:'
grep '^SCADA_EDGE_TOKEN=' /etc/scada-edge.env
