#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/tarot-lena}"
REPO_URL="${REPO_URL:-https://github.com/Fullfaq-dev/tarot-lena.git}"
VPS_IP="${VPS_IP:-43.165.5.18}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl git ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR" || true
fi

mkdir -p "$APP_DIR/backend/static/generated"
chmod +x "$APP_DIR/deploy/deploy.sh" 2>/dev/null || true

if [ -f "$APP_DIR/deploy/nginx.ip.conf" ]; then
  cp "$APP_DIR/deploy/nginx.ip.conf" "$APP_DIR/deploy/nginx.active.conf"
fi

echo "Server bootstrap done. Configure $APP_DIR/.env and run deploy/deploy.sh"
