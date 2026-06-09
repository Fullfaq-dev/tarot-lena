#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/arcane-ai}"
DOMAIN="${DOMAIN:-arcaneai.online}"
EMAIL="${EMAIL:-admin@arcaneai.online}"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq certbot
ufw allow 443/tcp || true

# HTTP-only nginx while issuing the certificate
cp deploy/nginx.bootstrap.conf deploy/nginx.active.conf
docker compose -f "$COMPOSE_FILE" up -d nginx api admin

docker compose -f "$COMPOSE_FILE" stop nginx

if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
  certbot certonly --standalone \
    -d "$DOMAIN" \
    -d "www.${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    -m "$EMAIL" \
    --preferred-challenges http
fi

cp deploy/nginx.conf deploy/nginx.active.conf
docker compose -f "$COMPOSE_FILE" up -d

if ! crontab -l 2>/dev/null | grep -q certbot; then
  (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'cd ${APP_DIR} && docker compose -f ${COMPOSE_FILE} restart nginx'") | crontab -
fi

sed -i 's|^APP_ENV=.*|APP_ENV=production|' .env
sed -i 's|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://'"${DOMAIN}"'|' .env
docker compose -f "$COMPOSE_FILE" --profile polling stop bot 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" rm -f bot 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" restart api

echo "SSL ready for https://${DOMAIN}"
