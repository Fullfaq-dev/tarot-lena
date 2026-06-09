#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/arcane-ai}"
DOMAIN="${DOMAIN:-arcaneai.online}"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
  echo "Certificate already exists"
  cp deploy/nginx.conf deploy/nginx.active.conf
  sed -i 's|^APP_ENV=.*|APP_ENV=production|' .env
  sed -i 's|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://'"${DOMAIN}"'|' .env
  docker compose -f "$COMPOSE_FILE" --profile polling stop bot 2>/dev/null || true
  docker compose -f "$COMPOSE_FILE" rm -f bot 2>/dev/null || true
  docker compose -f "$COMPOSE_FILE" up -d
  docker compose -f "$COMPOSE_FILE" restart api
  exit 0
fi

if ! getent ahostsv4 "$DOMAIN" | grep -q '147.45.228.92'; then
  echo "DNS for ${DOMAIN} is not pointing to this server yet"
  exit 1
fi

bash deploy/setup-ssl.sh

sed -i 's|^APP_ENV=.*|APP_ENV=production|' .env
sed -i 's|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://'"${DOMAIN}"'|' .env
docker compose -f "$COMPOSE_FILE" --profile polling stop bot 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" rm -f bot 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" restart api
