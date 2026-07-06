#!/usr/bin/env bash
set -euo pipefail

VPS_HOST="${VPS_HOST:-43.165.5.18}"
VPS_USER="${VPS_USER:-ubuntu}"
APP_DIR="/opt/tarot-lena"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

if [ -n "${SSHPASS_FILE:-}" ]; then
  SSHPASS_PREFIX=(sshpass -f "${SSHPASS_FILE}")
elif [ -n "${SSHPASS:-}" ]; then
  SSHPASS_PREFIX=(sshpass -e)
else
  echo "Set SSHPASS_FILE or SSHPASS" >&2
  exit 1
fi

remote() {
  "${SSHPASS_PREFIX[@]}" ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "$@"
}

echo "==> Checking VPS connectivity..."
remote "echo connected && uname -a"

echo "==> Installing Docker if needed..."
remote "sudo bash -s" < "${PROJECT_DIR}/deploy/setup-server.sh"
remote "sudo usermod -aG docker ${VPS_USER} 2>/dev/null || true"
remote "sudo mkdir -p ${APP_DIR} && sudo chown -R ${VPS_USER}:${VPS_USER} ${APP_DIR}"

echo "==> Syncing project files..."
"${SSHPASS_PREFIX[@]}" rsync -az --delete \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude 'Таро Божественного наследия' \
  "${PROJECT_DIR}/" "${VPS_USER}@${VPS_HOST}:${APP_DIR}/"

echo "==> Writing production .env..."
PG_PASS="$(openssl rand -hex 16)"
JWT_SECRET="$(openssl rand -hex 32)"
WEBHOOK_SECRET="$(openssl rand -hex 24)"

remote "cat > ${APP_DIR}/.env" <<EOF
APP_ENV=production
APP_NAME=Лея — Таро и Нумерология
PUBLIC_BASE_URL=http://${VPS_HOST}:8080

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
LEGAL_PAGE_URL=http://${VPS_HOST}:8080/legal
SUPPORT_TELEGRAM_URL=https://t.me/astro_leia_bot

PLATEGA_MERCHANT_ID=${PLATEGA_MERCHANT_ID:-}
PLATEGA_API_KEY=${PLATEGA_API_KEY:-}
PLATEGA_PAYMENT_METHOD=0
PLATEGA_RETURN_URL=http://${VPS_HOST}:8080/payment/success
PLATEGA_FAILED_URL=http://${VPS_HOST}:8080/payment/failed

MEDIA_STORAGE_DIR=backend/static/generated
TAROT_CARDS_DIR=Cards-jpg
EOF

echo "==> Running deploy..."
remote "cd ${APP_DIR} && chmod +x deploy/deploy.sh deploy/setup-server.sh && sg docker -c 'bash deploy/deploy.sh'"

echo "==> Health check..."
sleep 8
curl -sf "http://${VPS_HOST}/health" && echo

echo "==> Container status..."
remote "cd ${APP_DIR} && sg docker -c 'docker compose -f docker-compose.prod.yml ps'"

echo "Done. Bot: https://t.me/astro_leia_bot"
