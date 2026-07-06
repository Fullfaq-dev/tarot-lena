#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/tarot-lena}"
COMPOSE_FILE="docker-compose.prod.yml"
VPS_IP="${VPS_IP:-43.165.5.18}"

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

ensure_env APP_NAME "Лея — Таро и Нумерология"
ensure_env ADMIN_BOOTSTRAP_EMAIL "admin@tarot-lena.local"
ensure_env ADMIN_BOOTSTRAP_PASSWORD "LeiaPanel#2026!Km"
ensure_env LEGAL_PAGE_URL "http://${VPS_IP}:8080/legal"
ensure_env SUPPORT_TELEGRAM_URL "https://t.me/astro_leia_bot"
ensure_env APP_ENV "production"
ensure_env PUBLIC_BASE_URL "http://${VPS_IP}:8080"
ensure_env PLATEGA_RETURN_URL "http://${VPS_IP}:8080/payment/success"
ensure_env PLATEGA_FAILED_URL "http://${VPS_IP}:8080/payment/failed"
ensure_env PLATEGA_PAYMENT_METHOD "0"
ensure_env TELEGRAM_ADMIN_IDS "267409502,7670490295"
ensure_env OWNER_TELEGRAM_ID "7670490295"
ensure_env TELEGRAM_USE_POLLING "1"
ensure_env PAYMENTS_DEMO_MODE "1"
if ! grep -q "^JWT_SECRET=" .env 2>/dev/null || grep -q "^JWT_SECRET=replace-me" .env 2>/dev/null; then
  ensure_env JWT_SECRET "$(openssl rand -hex 32)"
fi
if ! grep -q "^POSTGRES_PASSWORD=" .env 2>/dev/null; then
  ensure_env POSTGRES_PASSWORD "$(openssl rand -hex 16)"
fi
if ! grep -q "^TELEGRAM_WEBHOOK_SECRET=" .env 2>/dev/null || grep -q "^TELEGRAM_WEBHOOK_SECRET=replace-me" .env 2>/dev/null; then
  ensure_env TELEGRAM_WEBHOOK_SECRET "$(openssl rand -hex 24)"
fi

if [ -d .git ]; then
  git fetch origin main 2>/dev/null || true
  git reset --hard origin/main 2>/dev/null || true
fi

if [ -f /etc/letsencrypt/live/*/fullchain.pem ] 2>/dev/null; then
  cp deploy/nginx.conf deploy/nginx.active.conf
elif [ -f deploy/nginx.ip.conf ]; then
  cp deploy/nginx.ip.conf deploy/nginx.active.conf
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
fi

build_ok=0
set +e
docker compose -f "$COMPOSE_FILE" build --pull=false api worker bot
build_rc=$?
set -e
if [ "$build_rc" -eq 0 ]; then
  build_ok=1
else
  echo "WARN: Docker build skipped (likely Hub rate limit). Using cached images + live backend mount."
fi

if [ "$build_ok" -eq 1 ]; then
  docker compose -f "$COMPOSE_FILE" up -d
else
  docker compose -f "$COMPOSE_FILE" up -d --no-build
fi

if [ -f frontend-admin/dist/index.html ]; then
  docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps admin
fi

docker compose -f "$COMPOSE_FILE" run --rm --no-deps api alembic upgrade head
docker compose -f "$COMPOSE_FILE" restart api worker bot admin nginx

docker image prune -f

echo "Deploy finished: $(date -Is)"
