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

For Telegram webhook and reliable KIE image fetch, add a domain with HTTPS and set `PUBLIC_BASE_URL=https://your-domain`.
