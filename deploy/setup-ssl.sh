#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/tarot-lena}"
DOMAIN="${DOMAIN:-arcaneai.online}"
EMAIL="${EMAIL:-admin@${DOMAIN}}"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq certbot
ufw allow 443/tcp || true
mkdir -p /var/www/certbot

# HTTP config must serve ACME before the cert exists.
if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
  cp deploy/nginx.ip.conf deploy/nginx.active.conf
  docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps nginx
  sleep 2
fi

if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
  certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN" \
    -d "www.${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    -m "$EMAIL"
fi

cp deploy/nginx.conf deploy/nginx.active.conf
sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://${DOMAIN}|" .env
sed -i "s|^LEGAL_PAGE_URL=.*|LEGAL_PAGE_URL=https://${DOMAIN}/legal|" .env
sed -i "s|^PLATEGA_RETURN_URL=.*|PLATEGA_RETURN_URL=https://${DOMAIN}/payment/success|" .env
sed -i "s|^PLATEGA_FAILED_URL=.*|PLATEGA_FAILED_URL=https://${DOMAIN}/payment/failed|" .env

docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps nginx
docker compose -f "$COMPOSE_FILE" restart api

if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
  (crontab -l 2>/dev/null || true; echo "0 3 * * * certbot renew --quiet --webroot -w /var/www/certbot --deploy-hook 'cd ${APP_DIR} && docker compose -f ${COMPOSE_FILE} exec -T nginx nginx -s reload'") | crontab -
fi

echo "SSL ready for https://${DOMAIN}"
