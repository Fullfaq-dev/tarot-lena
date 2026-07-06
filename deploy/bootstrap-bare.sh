#!/usr/bin/env bash
set -euo pipefail

VPS_HOST="${VPS_HOST:-85.234.106.108}"
VPS_USER="${VPS_USER:-root}"
APP_DIR="/opt/tarot-lena"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SSH_OPTS=(-o StrictHostKeyChecking=no)

if [ -z "${SSHPASS:-}" ]; then
  echo "Set SSHPASS" >&2
  exit 1
fi

remote() {
  sshpass -e ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "$@"
}

echo "==> Bootstrap server..."
remote "bash -s" < "${PROJECT_DIR}/deploy/setup-server.sh"

echo "==> Add swap (2GB RAM)..."
remote "fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048; chmod 600 /swapfile; mkswap /swapfile; swapon /swapfile; grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab"

echo "==> Sync project..."
sshpass -e rsync -az --delete \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude 'Таро Божественного наследия' \
  --exclude '*.docx' \
  "${PROJECT_DIR}/" "${VPS_USER}@${VPS_HOST}:${APP_DIR}/"

echo "==> Write .env..."
PG_PASS="$(openssl rand -hex 16)"
JWT_SECRET="$(openssl rand -hex 32)"
WEBHOOK_SECRET="$(openssl rand -hex 24)"

remote "cat > ${APP_DIR}/.env" <<EOF
APP_ENV=production
APP_NAME=Лея — Таро и Нумерология
PUBLIC_BASE_URL=http://${VPS_HOST}

POSTGRES_PASSWORD=${PG_PASS}
DATABASE_URL=postgresql+asyncpg://tarot:${PG_PASS}@postgres:5432/tarot
REDIS_URL=redis://redis:6379/0

TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:?set TELEGRAM_BOT_TOKEN}
TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET}
TELEGRAM_USE_POLLING=1
TELEGRAM_ADMIN_IDS=267409502,7670490295
OWNER_TELEGRAM_ID=7670490295

KIE_API_KEY=${KIE_API_KEY:?set KIE_API_KEY}
KIE_BASE_URL=https://api.kie.ai
KIE_FILE_UPLOAD_BASE_URL=https://kieai.redpandaai.co
KIE_CALLBACK_SECRET=${WEBHOOK_SECRET}

JWT_SECRET=${JWT_SECRET}
ADMIN_BOOTSTRAP_EMAIL=admin@tarot-lena.local
ADMIN_BOOTSTRAP_PASSWORD=LeiaPanel#2026!Km
LEGAL_PAGE_URL=http://${VPS_HOST}/legal
SUPPORT_TELEGRAM_URL=https://t.me/astro_leia_bot

PLATEGA_MERCHANT_ID=
PLATEGA_API_KEY=
PLATEGA_PAYMENT_METHOD=0
PLATEGA_RETURN_URL=http://${VPS_HOST}/payment/success
PLATEGA_FAILED_URL=http://${VPS_HOST}/payment/failed
PAYMENTS_DEMO_MODE=1

MEDIA_STORAGE_DIR=backend/static/generated
TAROT_CARDS_DIR=Cards-jpg
HTTP_PORT=80
EOF

echo "==> Deploy..."
remote "cd ${APP_DIR} && chmod +x deploy/deploy.sh && SKIP_GIT_PULL=1 VPS_IP=${VPS_HOST} HTTP_PORT=80 bash deploy/deploy.sh"

echo "==> Health check..."
sleep 10
curl -sf "http://${VPS_HOST}/health" && echo

echo "Done: http://${VPS_HOST}/ — bot @astro_leia_bot"
