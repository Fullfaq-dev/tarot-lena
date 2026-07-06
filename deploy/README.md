# Deploy — Tarot Lena (бот «Лея»)

## GitHub

Repository: https://github.com/Fullfaq-dev/tarot-lena

## Голый VPS (рекомендуется)

**Не Zeabur, не k3s** — обычный Ubuntu 24.04 (или 22.04), минимум 2 GB RAM, 1 CPU.
Порты Zeabur (4222, 6443, 30000+) **не нужны** — только **22, 80, 443**.

### 1. Подключиться к серверу

```bash
ssh root@<IP>
# или ssh ubuntu@<IP>
```

### 2. Bootstrap (Docker + git + firewall)

```bash
curl -fsSL https://raw.githubusercontent.com/Fullfaq-dev/tarot-lena/main/deploy/setup-server.sh | sudo bash
```

Или вручную после `git clone`:

```bash
sudo bash /opt/tarot-lena/deploy/setup-server.sh
```

### 3. Клонировать проект

```bash
sudo mkdir -p /opt/tarot-lena
sudo chown $USER:$USER /opt/tarot-lena
git clone https://github.com/Fullfaq-dev/tarot-lena.git /opt/tarot-lena
cd /opt/tarot-lena
```

### 4. Настроить `.env`

```bash
cp .env.example .env
nano .env
```

Обязательно:

```
TELEGRAM_BOT_TOKEN=...
KIE_API_KEY=...
TELEGRAM_USE_POLLING=1
PAYMENTS_DEMO_MODE=1
```

Опционально в `.env` или перед деплоем:

```
VPS_IP=<IP_сервера>
HTTP_PORT=80
```

На голом сервере nginx слушает **порт 80** (не 8080 как на Zeabur).

### 5. Запуск

```bash
cd /opt/tarot-lena
bash deploy/deploy.sh
```

Проверка:

```bash
curl http://127.0.0.1/health
curl http://<IP>/health
```

### 6. Обновления

Локально пушишь в GitHub → на сервере:

```bash
cd /opt/tarot-lena && bash deploy/deploy.sh
```

---

## Альтернатива: залить с локальной машины (без git на сервере)

```bash
# с Mac, из папки проекта
rsync -az --exclude '.git' --exclude 'node_modules' --exclude '.env' \
  ./ ubuntu@<IP>:/opt/tarot-lena/

ssh ubuntu@<IP> 'cd /opt/tarot-lena && bash deploy/deploy.sh'
```

`.env` на сервере создаётся один раз вручную и не перезаписывается.

---

## Zeabur VPS (legacy)

Если 80/443 заняты k3s — в `.env`:

```
HTTP_PORT=8080
```

Тогда URLs: `http://<IP>:8080/health`

---

## Демо-оплата

`PAYMENTS_DEMO_MODE=1` — кнопка «Купить» сразу проводит платёж без Platega.

## URLs

- Site: `http://<IP>/`
- Legal: `http://<IP>/legal`
- Admin: `http://<IP>/panel/`
- Health: `http://<IP>/health`
- Bot: https://t.me/astro_leia_bot

## Platega (когда подключите)

Callback: `http://<IP>/callbacks/platega`

## Domain (later)

1. DNS A → IP сервера
2. `bash deploy/retry-ssl.sh`
3. `PUBLIC_BASE_URL=https://<domain>`, при webhook — `TELEGRAM_USE_POLLING=0`
