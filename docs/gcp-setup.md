# GCP Deployment Guide

Deploys on a single Ubuntu 24.04 VM using **Gunicorn + Nginx**.  
The setup script handles everything — packages, MySQL, app clone, secrets, service, and reverse proxy.

---

## Prerequisites

- A GCP VM (Ubuntu 22.04 or 24.04) with:
  - HTTP traffic allowed (port 80 or custom port)
  - At least 2 GB RAM recommended
- SSH access to the VM (via GCP Console browser SSH or `gcloud compute ssh`)

---

## Fresh VM — one command

SSH into the VM and run:

```bash
curl -fsSL https://raw.githubusercontent.com/Amanverma1011/InternshipProject/main/deploy/setup_vm.sh | sudo bash
```

The script will:
1. Install Python 3, MySQL, Nginx, Git, build tools
2. Clone the repo to `/opt/solar-proposal`
3. Create a Python venv and install dependencies
4. Generate a random `SECRET_KEY` and `DB_PASSWORD`
5. Create the database schema and MySQL app user
6. Seed the database with a master admin account
7. Create and start a `solar-proposal` systemd service (runs as `www-data`)
8. Configure Nginx as a reverse proxy on port 80

**At the end, save the credentials printed in the terminal — they will not be shown again.**

---

## If another app already occupies port 80

Configure Nginx to serve on a different port (e.g. 8080):

```nginx
server {
    listen 8080;
    server_name _;
    ...
}
```

Then open the port in GCP firewall:

```bash
gcloud compute firewall-rules create allow-solar-8080 \
  --allow=tcp:8080 \
  --target-tags=YOUR_VM_TAG \
  --project=YOUR_PROJECT_ID
```

---

## Updating an existing deployment

```bash
sudo bash -c 'cd /opt/solar-proposal \
  && git pull \
  && venv/bin/pip install -r requirements.txt --quiet \
  && systemctl restart solar-proposal'
```

---

## Useful commands on the VM

```bash
# Check service status
sudo systemctl status solar-proposal

# View live logs
sudo journalctl -u solar-proposal -f

# View access logs
sudo tail -f /var/log/solar-proposal-access.log

# Restart service
sudo systemctl restart solar-proposal

# Test nginx config
sudo nginx -t
```

---

## After setting up HTTPS / SSL

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

Then enable secure cookies:

```bash
sudo sed -i 's/SESSION_COOKIE_SECURE=false/SESSION_COOKIE_SECURE=true/' /opt/solar-proposal/.env
sudo systemctl restart solar-proposal
```

---

## Environment variables reference

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | **Required** |
| `DB_HOST` | MySQL host | `127.0.0.1` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `sologix_proposals` |
| `DB_USER` | MySQL app user | `sologix_app` |
| `DB_PASSWORD` | MySQL app password | **Required** |
| `STORAGE_PATH` | PDF storage directory | `storage/proposals` |
| `SESSION_COOKIE_SECURE` | Set `true` after HTTPS is configured | `false` |
