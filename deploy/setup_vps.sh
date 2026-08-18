#!/usr/bin/env bash
# Sets up stock-calculator on a fresh Ubuntu VPS: Caddy + gunicorn + systemd.
# Usage: bash setup_vps.sh [domain]
# No domain given -> falls back to a sslip.io hostname (still gets real HTTPS).

set -euo pipefail

REPO_URL="https://github.com/ari-butterfield/stock-calculator.git"
APP_DIR="/opt/stock-calculator"
APP_USER="stockapp"
DOMAIN="${1:-}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this as root (e.g. via sudo)." >&2
  exit 1
fi

if [ -z "$DOMAIN" ]; then
  PUBLIC_IP="$(curl -fsSL https://api.ipify.org)"
  DOMAIN="${PUBLIC_IP//./-}.sslip.io"
  echo "No domain passed in — using sslip.io magic domain: $DOMAIN"
fi

echo "==> Installing base packages"
apt-get update -y
apt-get install -y python3-venv python3-pip git ufw curl debian-keyring debian-archive-keyring apt-transport-https gnupg

if ! command -v caddy >/dev/null 2>&1; then
  echo "==> Installing Caddy"
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  echo "==> Creating service user $APP_USER"
  useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
fi

if [ -d "$APP_DIR/.git" ]; then
  echo "==> Pulling latest code"
  sudo -u "$APP_USER" git -C "$APP_DIR" pull
else
  echo "==> Cloning repo"
  git clone "$REPO_URL" "$APP_DIR"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

echo "==> Installing Python dependencies"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
  echo "==> Creating .env from .env.example"
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  GENERATED_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  sed -i "s#changeme-generate-a-random-value#$GENERATED_SECRET#" "$APP_DIR/.env"
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
fi

echo "==> Installing systemd service"
cp "$APP_DIR/deploy/stock-calculator.service" /etc/systemd/system/stock-calculator.service
systemctl daemon-reload
systemctl enable stock-calculator
systemctl restart stock-calculator

echo "==> Configuring Caddy for $DOMAIN"
sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/" "$APP_DIR/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl restart caddy

echo "==> Configuring firewall"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Done: https://$DOMAIN"
if grep -q 'key-from-alphavantage.co' "$APP_DIR/.env" 2>/dev/null; then
  echo "==> Set ALPHA_VANTAGE_API_KEY in $APP_DIR/.env, then: systemctl restart stock-calculator"
fi
