#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/arcane-ai}"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

ensure_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    echo "${key}=${value}" >> .env
  fi
}

ensure_env ADMIN_BOOTSTRAP_EMAIL "admin@arcaneai.online"
ensure_env ADMIN_BOOTSTRAP_PASSWORD "ArcanaPanel#2026!Km"
ensure_env LEGAL_PAGE_URL "https://arcaneai.online/"
ensure_env SUPPORT_TELEGRAM_URL "https://t.me/OnePage_support"
if ! grep -q "^JWT_SECRET=" .env 2>/dev/null || grep -q "^JWT_SECRET=replace-me" .env 2>/dev/null; then
  ensure_env JWT_SECRET "$(openssl rand -hex 32)"
fi

git fetch origin main
git reset --hard origin/main

if [ -f /etc/letsencrypt/live/arcaneai.online/fullchain.pem ]; then
  cp deploy/nginx.conf deploy/nginx.active.conf
else
  cp deploy/nginx.bootstrap.conf deploy/nginx.active.conf
fi

docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d
docker compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head
docker compose -f "$COMPOSE_FILE" restart nginx

docker image prune -f

echo "Deploy finished: $(date -Is)"
