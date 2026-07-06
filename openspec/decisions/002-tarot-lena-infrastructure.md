# ADR-002: Отдельный репозиторий и VPS

**Статус:** Принято (проектирование)  
**Дата:** 2026-07-06

## Контекст

Заказчик указал новый git-репозиторий (`tarot-lena`) и новый VPS. Старый Arcana AI продолжает работать независимо.

## Решение

1. **Форк кодовой базы** Arcana AI → `https://github.com/Fullfaq-dev/tarot-lena.git`.
2. **VPS Zeabur** `43.165.5.18`, user `ubuntu`, путь `/opt/tarot-lena`.
3. **Бот** `@astro_leia_bot`, admins `267409502,7670490295`.
4. **Polling** вместо webhook до появления домена (ADR-003).
5. **PostgreSQL** с нуля — без миграции пользователей.
6. **Platega** — тот же мерчант, URLs на `http://43.165.5.18`.
7. **CI/CD** — GitHub Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

## Последствия

- Два независимых деплоя; Arcana AI на старом VPS не трогаем.
- SSL и webhook — отложены до домена.
- Рассылки по per-user timezone.

## Открыто

- Домен (когда будет — certbot + переход на webhook).
