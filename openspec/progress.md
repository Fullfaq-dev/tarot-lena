# Progress

## Arcana AI (исходный проект)

- [Completed] Build Telegram acquisition landing page with Arcana visual style.
- [Completed] Mark `/start landing` users in owner notifications and analytics payload.
- [Completed] Validate static site and Python changes.
- [Completed] Move legal documents to a separate page, add real avatar, themed SVG icons, sparkles, and mobile fixes.
- [Completed] Add dual iPhone bot screenshots and interactive referral earning section to the landing page.
- [Completed] Localize daily-card generation and prevent cross-language daily-card cache reuse.
- [Completed] Landing page analytics: click/scroll/section tracking, session duration, admin dashboard page.
- [Completed] Per-partner referral reward percent in DB with admin editing; 50% for telegram_id 8082467889.

---

## Tarot Lena — миграция на бота «Лея»

- [Completed] Проектирование: `openspec/proposals/tarot-lena-migration.md`, ADR-001, ADR-002.
- [Completed] Фаза 0: VPS Zeabur `43.165.5.18`, Docker, polling-бот, health OK на `:8080`.
- [Completed] Фаза 1: Лея — onboarding, нумеропортрет, 5 продуктов (мини→полная), Platega.
- [Completed] Фаза 2: комбо «Счастливая женщина», ЛЮБОВЬ+, VIP, entitlements.
- [Completed] Фаза 3: утренняя/вечерняя рассылка, гороскоп по понедельникам, воронка день 2.
- [Completed] Сайт и legal под Лею (скрины оставлены); админ-панель: брендинг, метрики VIP/ЛЮБОВЬ+/комбо, entitlements в карточке пользователя.
- [Completed] Фаза 4: реферал «Приведи подругу» (−20% для подруги, +3 дня после покупки), UX-правки из docx, legal Карпова.
- [Completed] Rich-разметка Леи: профиль с таблицами, меню/пакеты/реферал, постобработка ответов ИИ (`leia_rich.py`), дружелюбные тексты.

**Инфра утверждена:** IP `85.234.106.108`, `@astro_leia_bot`, admins `267409502,7670490295`, polling, Platega тот же, legal docx в корне.

**Деплой:** push в `Fullfaq-dev/tarot-lena` → GitHub Actions → `git pull` на VPS + `deploy/deploy.sh`.

**Оплата:** `PAYMENTS_DEMO_MODE=1` — кнопка «Купить» сразу проводит платёж (без Platega).
