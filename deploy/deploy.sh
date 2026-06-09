#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/arcane-ai}"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

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
