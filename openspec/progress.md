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
- [Completed] Бесплатный контент по ТЗ: матрица Хшановской, утро/неделя по шаблонам, 7 дней trial, мини-портрет, кнопки 5 продуктов в рассылках.
- [Completed] Сброс всех пользователей в production (0 в БД), fix миграции `user_settings` (колонки рассылок), `/start` без «Что-то пошло не так», legal/оплата — Карпова Е.И.
- [Completed] Fix проактивных сообщений: активность с 09:00 (messages + product_usages), dedupe утра, local date для карты дня.
- [Completed] Фидбек заказчицы: «Расклад Таро», Матрица судьбы, реферал −20% шарящему, чат для оплативших, pitch-подсказки, launch→оплата.
- [Completed] Картинки из `Асторобот.docx` в сценариях (продукты, пакеты, реферал, портрет, воронка); сверка текстов с ТЗ; вечерний расклад; fix панелей без удаления разбора.
- [Completed] Автоматизация: «не выбрали тариф» (+10% промо, image4, пакеты); реферал через 3 дня после покупки (картинка, кнопка «Поделиться»).
- [Completed] Деплой `8cdc297` на VPS `85.234.106.108`.
- [Completed] Fix VIP-расклад: расшифровка отдельным сообщением; follow-up «Расшифруй» с контекстом из БД, без сброса в меню.
- [Completed] Картинки Леи в rich-блоке (одно сообщение, крупнее); убрана лишняя подсказка после разбора.
- [Completed] Приветственный экран `/start` — rich-текст по ТЗ (умения + документы + согласие).
- [Completed] Fix raw markdown в чате: фото отдельно, HTML-fallback; расклад с резервной расшифровкой; меньше спама после анкеты.
- [Completed] Fix мини-кнопки (alert + повтор при пустом AI); история разборов в меню/клавиатуре; быстрее ответы AI.
- [Completed] KIE: обработка code=500, fallback на gemini-2.5-flash; один пузырь расклада; typing «печатает…».
- [Completed] Busy-lock: пока идёт разбор — нельзя стартовать другой; статус-сообщение + typing heartbeat.
- [Completed] Деплой busy-lock (`382c5f8`) на VPS `85.234.106.108` — health OK, bot polling.
- [Completed] Fix истории разборов: callback брал telegram_id бота → «нажми /start» (`188c5f7`).
- [Completed] Чат: меню в промпте, обсуждение только оплаченных разборов, новые разборы только из меню.
- [Completed] Robokassa: клиент MD5, ResultURL `/callbacks/robokassa`, demo пока нет ключей.
- [Completed] Оплата: кнопка «Оплатить N ₽» вместо URL-простыни; пост-оплата через rich/HTML (не сырой markdown); богатство 390 ₽.
- [Completed] Админ: история из ProductUsage; рефералка −20% + приглашённый; drill-down платежа `/billing/{id}`.
- [Completed] Админ «Переписка»: полная лента Message + разборы ProductUsage; лог чата Леи/followup/разборов в `messages`.
- [Completed] Токены: usage_records для Леи + оценка старых разборов; касса Robokassa на дашборде (оборот по платежам).
- [Completed] Онбординг: выбор пола; профиль → «Изменить» (имя/пол/дата/время/город).
- [Completed] Промпты v2 по ТЗ заказчицы: основной + блоки продуктов/мини/рассылок;
  переменные считает бэкенд; утро без карты дня (знак + личное число).
- [Completed] Fix утра: rich-разметка (без сырых ###); VIP/оплатившие тоже получают ежедневный прогноз.
- [Completed] Daily-fix: sign_theme, link_type, таблица чисел, last_7-банлист.
- [Completed] Продукт «Переписка» 300 ₽ (мини 1×; Love+/VIP безлимит).

**Инфра утверждена:** IP `85.234.106.108`, `@astro_leia_bot`, admins `267409502,7670490295`, polling, Robokassa, legal docx в корне.

**Деплой:** push в `Fullfaq-dev/tarot-lena` → rsync/`deploy/deploy.sh` на VPS (`SKIP_GIT_PULL=1` при rsync).

- [Completed] Сайт-квиз по ТЗ: `frontend-web`, `/api/web`, Robokassa, мини-шаблоны, апселл/безлимит 590, бот `web_<token>`, админка карточек, кэш матрицы, Метрика 110607194.
- [Completed] Окно оплаты без почты/входа, новая колода 78 JPG, Метрика грузится сразу (отказ в баннере).
- [Completed] Колода «Божественное наследие» оригиналами + новая рубашка; тариф выбирается кликом, оплата только кнопкой.
- [Completed] Мини-разбор через ИИ (JSON verdict/body/hook), полный текст на экране без fade.
- [Completed] ТЗ сайта v1 (02.10.2026): один пакет оплаты, 3 вопроса Лее + пакеты 99/199, лимит 5/20 мини, Telegram-выход, SVG матрицы, офлайн purchase, CORE полного разбора.
- [Completed] Фикс возврата после оплаты на полный разбор, «есть ли другая» как платный 3-картный расклад, разбор в кабинете с гостевой сессии.
- [Completed] После Robokassa кидать строго на `/r/{token}` оплаченного разбора, не в кабинет и не на чужой last_reading.
- [Completed] Пейвол 04.10: подарок один текст, строка про алгоритм по ветке, страйк `price+3×99` под флагом, без цен специалиста и «+ доп. разбор», вёрстка 390px.
- [Completed] Отступ кнопки «Дальше» от последнего варианта в квизе.
- [Completed] Временные 10 ₽ на сайте для проверки кассы: оплата открывает полный разбор, боевые цены закомментированы.
- [Completed] Возврат из Robokassa не на /lk (логин не нужен): попап/iframe кассы, полный разбор на той же странице мини, индикатор «Лея пишет», 503 вместо 500 в чате.
- [Completed] Вернул боевые цены и HTML-разметку полного разбора (заголовки/курсив вместо сырого markdown).
- [Completed] Чат по разбору: убрал обрезку 800/400, таймаут 180 с в `deploy/nginx.conf`. Второй вопрос падал 400: Responses API не принимает `input_text` у assistant.
- [Completed] Чат: прошлый ответ Леи уходит как `output_text`, чтобы второй вопрос не ловил 400.
- [Completed] Зачёркнутая цена на пейволе и в окне оплаты: `SHOW_STRIKE_PRICE=true`, в модалке тот же блок что на пейволе.
