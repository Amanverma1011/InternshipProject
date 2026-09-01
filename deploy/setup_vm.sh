#!/bin/bash
# Run as root on fresh Ubuntu 22.04 VM
set -e

APP_DIR="/opt/solar-proposal"
REPO="https://github.com/Amanverma1011/InternshipProject"

echo ">>> Installing system packages"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip \
    mysql-server nginx git \
    python3-cffi libpango-1.0-0 libpangocairo-1.0-0 \
    libharfbuzz0b libpangoft2-1.0-0 libfontconfig1 libglib2.0-0

echo ">>> Cloning / updating repo"
if [ -d "$APP_DIR/.git" ]; then
    git -C $APP_DIR pull
else
    git clone $REPO $APP_DIR
fi

echo ">>> Python venv + dependencies"
python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install --upgrade pip --quiet
$APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt --quiet

echo ">>> MySQL setup"
systemctl start mysql
systemctl enable mysql
mysql -u root < $APP_DIR/database/schema.sql

echo ">>> Creating .env"
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DB_PASS="${DB_PASSWORD:-SologixApp2026!}"
cat > $APP_DIR/.env << EOF
FLASK_ENV=production
SECRET_KEY=$SECRET
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=sologix_proposals
DB_USER=sologix_app
DB_PASSWORD=$DB_PASS
STORAGE_PATH=/opt/solar-proposal/storage/proposals
PDF_TIMEOUT=60000
EOF

echo ">>> Seeding database"
cd $APP_DIR && venv/bin/python database/seed_auto.py

echo ">>> Storage directory"
mkdir -p $APP_DIR/storage/proposals
chmod -R 755 $APP_DIR/storage

echo ">>> Systemd service"
cat > /etc/systemd/system/solar-proposal.service << 'EOF'
[Unit]
Description=Sologix Solar Proposal System
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/opt/solar-proposal
EnvironmentFile=/opt/solar-proposal/.env
ExecStart=/opt/solar-proposal/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 --timeout 120 wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable solar-proposal
systemctl restart solar-proposal

echo ">>> Nginx config"
cat > /etc/nginx/sites-available/solar-proposal << 'EOF'
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 20M;

    location /static/ {
        alias /opt/solar-proposal/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120;
    }
}
EOF

ln -sf /etc/nginx/sites-available/solar-proposal /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx && systemctl enable nginx

EXT_IP=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)
echo ""
echo "========================================="
echo "DEPLOY COMPLETE"
echo "URL: http://$EXT_IP"
echo "Login: master / Admin@1234"
echo "========================================="
