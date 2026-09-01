#!/bin/bash
# Fresh Ubuntu 22.04 GCP VM setup for Sologix Solar Proposal System
# Usage: sudo bash setup_vm.sh
# Optional env vars:  MASTER_NAME  MASTER_USERNAME  MASTER_PASSWORD  DB_PASSWORD
set -e

APP_DIR="/opt/solar-proposal"
REPO="https://github.com/Amanverma1011/InternshipProject"

echo ">>> Installing system packages"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip \
    mysql-server nginx git libpq-dev

echo ">>> Cloning / updating repo"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO" "$APP_DIR"
fi

echo ">>> Python venv + dependencies"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip --quiet
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet

echo ">>> MySQL setup"
systemctl start mysql
systemctl enable mysql
mysql -u root < "$APP_DIR/database/schema.sql"

echo ">>> Generating secrets"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(48))")
DB_PASS="${DB_PASSWORD:-$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")}"
MASTER_PASS="${MASTER_PASSWORD:-$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")}"
MASTER_USER="${MASTER_USERNAME:-master}"
MASTER_NAME_VAL="${MASTER_NAME:-Sologix Admin}"

echo ">>> Writing .env"
cat > "$APP_DIR/.env" << EOF
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=sologix_proposals
DB_USER=sologix_app
DB_PASSWORD=$DB_PASS
STORAGE_PATH=/opt/solar-proposal/storage/proposals
PDF_TIMEOUT=60000
# Set to true after HTTPS/SSL is configured on nginx
SESSION_COOKIE_SECURE=false
EOF
chmod 600 "$APP_DIR/.env"

echo ">>> Seeding database"
MASTER_NAME="$MASTER_NAME_VAL" \
MASTER_USERNAME="$MASTER_USER" \
MASTER_PASSWORD="$MASTER_PASS" \
    "$APP_DIR/venv/bin/python" "$APP_DIR/database/seed_auto.py"

echo ">>> Storage directory"
mkdir -p "$APP_DIR/storage/proposals"
chmod -R 750 "$APP_DIR/storage"
chown -R www-data:www-data "$APP_DIR/storage" 2>/dev/null || true

echo ">>> Systemd service"
cat > /etc/systemd/system/solar-proposal.service << 'UNIT'
[Unit]
Description=Sologix Solar Proposal System
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/solar-proposal
EnvironmentFile=/opt/solar-proposal/.env
ExecStart=/opt/solar-proposal/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /var/log/solar-proposal-access.log \
    --error-logfile /var/log/solar-proposal-error.log \
    wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

# Give www-data access to app files
chown -R www-data:www-data "$APP_DIR" 2>/dev/null || true
chmod -R 750 "$APP_DIR"
chmod 600 "$APP_DIR/.env"

systemctl daemon-reload
systemctl enable solar-proposal
systemctl restart solar-proposal

echo ">>> Nginx config"
cat > /etc/nginx/sites-available/solar-proposal << 'NGINX'
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 20M;

    # Security headers (app also sets these, nginx adds them at edge)
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /static/ {
        alias /opt/solar-proposal/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
        proxy_connect_timeout 10;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/solar-proposal /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx && systemctl enable nginx

EXT_IP=$(curl -sf -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip \
    || echo "unknown")

echo ""
echo "========================================="
echo "  DEPLOY COMPLETE"
echo "  URL:       http://$EXT_IP"
echo "  Username:  $MASTER_USER"
echo "  Password:  $MASTER_PASS"
echo "  DB Pass:   $DB_PASS"
echo ""
echo "  SAVE THESE CREDENTIALS NOW."
echo "  They will not be shown again."
echo "========================================="
