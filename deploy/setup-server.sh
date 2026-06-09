#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/arcane-ai"
REPO_URL="${REPO_URL:-https://github.com/Fullfaq-dev/arcane-ai.git}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl git ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

ufw allow OpenSSH
ufw allow 80/tcp
ufw --force enable

mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

mkdir -p "$APP_DIR/backend/static/generated"
chmod +x "$APP_DIR/deploy/deploy.sh"

echo "Server bootstrap done. Configure $APP_DIR/.env and run deploy/deploy.sh"
