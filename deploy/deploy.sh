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
ensure_env APP_ENV "production"
ensure_env PUBLIC_BASE_URL "https://arcaneai.online"
ensure_env PLATEGA_RETURN_URL "https://arcaneai.online/payment/success"
ensure_env PLATEGA_FAILED_URL "https://arcaneai.online/payment/failed"
ensure_env PLATEGA_PAYMENT_METHOD "0"
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

if [ -f frontend-admin/dist/index.html ]; then
  echo "Admin dist ready: $(grep -o 'index-[^\"]*\\.js' frontend-admin/dist/index.html || true)"
  set +e
  docker compose -f "$COMPOSE_FILE" build --no-cache --pull=false admin
  admin_build_rc=$?
  set -e
  if [ "$admin_build_rc" -ne 0 ]; then
    echo "WARN: admin build failed; panel may serve an older build"
  fi
else
  echo "WARN: frontend-admin/dist/index.html missing; upload admin build in CI before deploy"
  ls -la frontend-admin/ || true
  ls -la frontend-admin/dist/ || true
fi

build_ok=0
set +e
docker compose -f "$COMPOSE_FILE" build --pull=false api worker
build_rc=$?
set -e
if [ "$build_rc" -eq 0 ]; then
  build_ok=1
else
  echo "WARN: api/worker Docker build skipped (likely Hub rate limit). Using cached images + live backend mount."
fi

if [ "$build_ok" -eq 1 ]; then
  docker compose -f "$COMPOSE_FILE" up -d
else
  docker compose -f "$COMPOSE_FILE" up -d --no-build
fi

if [ -f frontend-admin/dist/index.html ]; then
  docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps admin
fi

docker compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head
docker compose -f "$COMPOSE_FILE" restart api worker admin nginx

docker image prune -f

echo "Deploy finished: $(date -Is)"
