# Deploy

## GitHub

Repository: https://github.com/Fullfaq-dev/arcane-ai

Autodeploy runs on every push to `main` via `.github/workflows/deploy.yml`.

Required GitHub secrets:

- `VPS_HOST` — server IP
- `VPS_USER` — SSH user (`root`)
- `VPS_SSH_KEY` — private deploy key

## Server layout

- App path: `/opt/arcane-ai`
- Env file: `/opt/arcane-ai/.env` (not in git)
- Compose: `docker-compose.prod.yml`

Manual deploy on server:

```bash
cd /opt/arcane-ai
bash deploy/deploy.sh
```

## URLs

- Admin: `http://<server-ip>/`
- API health: `http://<server-ip>/health`
- Static uploads for KIE: `http://<server-ip>/static/generated/...`

## Domain arcaneai.online

1. At the registrar, set nameservers to Vercel (if the domain is managed in Vercel DNS).
2. In Vercel DNS add `A` records for `@` and `www` → `147.45.228.92`.
3. Wait until `dig +short arcaneai.online` returns the VPS IP.
4. On the server run:

```bash
cd /opt/arcane-ai
bash deploy/retry-ssl.sh
```

Cron (optional, retries SSL every 15 minutes until DNS is live):

```bash
echo "*/15 * * * * cd /opt/arcane-ai && bash deploy/retry-ssl.sh >> /var/log/arcane-ssl.log 2>&1" | crontab -
```

Set in `/opt/arcane-ai/.env`:

```env
APP_ENV=production
PUBLIC_BASE_URL=https://arcaneai.online
AI302_API_KEY=your-302ai-key
AI302_BASE_URL=https://api.302.ai
AI302_STT_MODEL=whisper-v3-turbo
```

On deploy, `AI302_API_KEY` is synced from GitHub secret `AI302_API_KEY` when set.
