"""User-facing service strings (billing, memory, profile, tarot, context)."""

SERVICE_STRINGS: dict[str, dict[str, str]] = {
    # Billing
    "billing_insufficient_balance": {
        "ru": "На балансе {balance} — недостаточно для ответа. Пополни баланс — нажми «Баланс».",
        "en": "Balance {balance} — not enough for a reply. Top up via «Balance».",
        "es": "Saldo {balance} — insuficiente. Recarga en «Saldo».",
        "pt": "Saldo {balance} — insuficiente. Recarregue em «Saldo».",
    },
    "billing_free_exhausted": {
        "ru": "Бесплатные сообщения закончились ({used}/{limit}). Пополни баланс (ответы 5–30 ₽) или подключи Plus/Premium — нажми «Баланс».",
        "en": "Free messages used up ({used}/{limit}). Top up (replies 5–30 ₽) or get Plus/Premium — tap «Balance».",
        "es": "Mensajes gratis agotados ({used}/{limit}). Recarga (5–30 ₽/resp.) o Plus/Premium — «Saldo».",
        "pt": "Mensagens grátis esgotadas ({used}/{limit}). Recarregue (5–30 ₽/resp.) ou Plus/Premium — «Saldo».",
    },
    "billing_infographic_needed": {
        "ru": "Для инфографики нужно {amount} на балансе. Пополни баланс — нажми «Баланс».",
        "en": "Infographic requires {amount} on balance. Top up via «Balance».",
        "es": "La infografía requiere {amount} en saldo. Recarga en «Saldo».",
        "pt": "Infográfico requer {amount} no saldo. Recarregue em «Saldo».",
    },
    "billing_insufficient_photo": {
        "ru": "На балансе {balance} — недостаточно для анализа фото. Пополни баланс — нажми «Баланс».",
        "en": "Balance {balance} — not enough for photo analysis. Top up via «Balance».",
        "es": "Saldo {balance} — insuficiente para foto. Recarga en «Saldo».",
        "pt": "Saldo {balance} — insuficiente para foto. Recarregue em «Saldo».",
    },
    "billing_panel_header": {
        "ru": (
            "<b>💳 Баланс и подписка</b>\n\n"
            "🎫 Тариф: <b>{tier}</b>\n\n"
            "💰 Баланс: <b>{balance}</b>\n\n"
            "🤝 Реферальный баланс: <b>{ref_balance}</b>"
        ),
        "en": (
            "<b>💳 Balance & subscription</b>\n\n"
            "🎫 Plan: <b>{tier}</b>\n\n"
            "💰 Balance: <b>{balance}</b>\n\n"
            "🤝 Referral balance: <b>{ref_balance}</b>"
        ),
        "es": (
            "<b>💳 Suscripción y saldo</b>\n\n"
            "🎫 Plan: <b>{tier}</b>\n\n"
            "💰 Saldo: <b>{balance}</b>\n\n"
            "🤝 Saldo de referidos: <b>{ref_balance}</b>"
        ),
        "pt": (
            "<b>💳 Assinatura e saldo</b>\n\n"
            "🎫 Plano: <b>{tier}</b>\n\n"
            "💰 Saldo: <b>{balance}</b>\n\n"
            "🤝 Saldo de indicação: <b>{ref_balance}</b>"
        ),
    },
    "billing_compare_table": {
        "ru": (
            "<b>Сравнение тарифов</b>\n\n"
            "| Возможность | Free | Plus | Premium |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| AI-чат | 10/мес | ∞ | ∞ |\n"
            "| Расклады | 3/мес | ∞ | ∞ |\n"
            "| Голос ответы | — | — | ✓ |\n"
            "| Инфографика | 100 ₽ | 100 ₽ | 50 беспл., далее 100 ₽ |\n"
            "| Цена/мес | 0 ₽ | 999 ₽ | 2999 ₽ |"
        ),
        "en": (
            "<b>Plan comparison</b>\n\n"
            "| Feature | Free | Plus | Premium |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| AI chat | 10/mo | ∞ | ∞ |\n"
            "| Readings | 3/mo | ∞ | ∞ |\n"
            "| Voice replies | — | — | ✓ |\n"
            "| Infographics | 100 ₽ | 100 ₽ | 50 free, then 100 ₽ |\n"
            "| Price/mo | 0 ₽ | 999 ₽ | 2999 ₽ |"
        ),
        "es": (
            "<b>Comparación de planes</b>\n\n"
            "| Función | Free | Plus | Premium |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| Chat IA | 10/mes | ∞ | ∞ |\n"
            "| Tiradas | 3/mes | ∞ | ∞ |\n"
            "| Voz | — | — | ✓ |\n"
            "| Infografías | 100 ₽ | 100 ₽ | 50 gratis, luego 100 ₽ |\n"
            "| Precio/mes | 0 ₽ | 999 ₽ | 2999 ₽ |"
        ),
        "pt": (
            "<b>Comparação de planos</b>\n\n"
            "| Recurso | Free | Plus | Premium |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| Chat IA | 10/mês | ∞ | ∞ |\n"
            "| Leituras | 3/mês | ∞ | ∞ |\n"
            "| Voz | — | — | ✓ |\n"
            "| Infográficos | 100 ₽ | 100 ₽ | 50 grátis, depois 100 ₽ |\n"
            "| Preço/mês | 0 ₽ | 999 ₽ | 2999 ₽ |"
        ),
    },
    "billing_panel_free_quota": {
        "ru": (
            "<b>Сейчас доступно бесплатно</b>\n\n"
            "💬 Сообщения в AI-чате: <b>{free_left}/{free_limit}</b>\n\n"
            "🔮 Расклады таро: <b>{readings_left}/3</b>\n\n"
            "<i>Когда лимит закончится:</i> ответ AI спишет <b>5–30 ₽</b> с баланса, "
            "а фото-инфографика по ауре/ладони — <b>100 ₽</b>."
        ),
        "en": (
            "<b>Free right now</b>\n\n"
            "💬 AI chat: <b>{free_left}/{free_limit}</b>\n\n"
            "🔮 Tarot readings: <b>{readings_left}/3</b>\n\n"
            "<i>After the free quota:</i> an AI reply costs <b>5–30 ₽</b>, "
            "an aura/palm infographic — <b>100 ₽</b>."
        ),
        "es": (
            "<b>Gratis ahora</b>\n\n"
            "💬 Chat IA: <b>{free_left}/{free_limit}</b>\n\n"
            "🔮 Tiradas: <b>{readings_left}/3</b>\n\n"
            "<i>Tras el límite:</i> respuesta IA <b>5–30 ₽</b>, infografía — <b>100 ₽</b>."
        ),
        "pt": (
            "<b>Grátis agora</b>\n\n"
            "💬 Chat IA: <b>{free_left}/{free_limit}</b>\n\n"
            "🔮 Leituras: <b>{readings_left}/3</b>\n\n"
            "<i>Após o limite:</i> resposta IA <b>5–30 ₽</b>, infográfico — <b>100 ₽</b>."
        ),
    },
    "billing_panel_premium_quota": {
        "ru": (
            "👑 <b>Premium активен</b>\n\n"
            "💬 Чат и расклады — без лимитов\n\n"
            "🖼️ Инфографика: <b>{info_left}/{info_limit}</b> в этом месяце "
            "(50 бесплатно, далее <b>100 ₽</b> за каждую)"
        ),
        "en": (
            "👑 <b>Premium active</b>\n\n"
            "💬 Chat & readings — unlimited\n\n"
            "🖼️ Infographics: <b>{info_left}/{info_limit}</b> this month "
            "(50 free, then <b>100 ₽</b> each)"
        ),
        "es": (
            "👑 <b>Premium activo</b>\n\n"
            "💬 Chat y tiradas — ilimitados\n\n"
            "🖼️ Infografías: <b>{info_left}/{info_limit}</b> este mes "
            "(50 gratis, luego <b>100 ₽</b> cada una)"
        ),
        "pt": (
            "👑 <b>Premium ativo</b>\n\n"
            "💬 Chat e leituras — ilimitados\n\n"
            "🖼️ Infográficos: <b>{info_left}/{info_limit}</b> este mês "
            "(50 grátis, depois <b>100 ₽</b> cada)"
        ),
    },
    "billing_panel_subs": {
        "ru": (
            "✨ <b>Plus</b> — {plus_price}/мес: безлимитный AI-чат и расклады, без списаний с баланса.\n\n"
            "👑 <b>Premium</b> — {premium_price}/мес: всё из Plus + голосовые ответы.\n\n"
            "🖼️ <b>50 инфографик в месяц бесплатно</b>, далее по <b>100 ₽</b> за каждую."
        ),
        "en": (
            "✨ <b>Plus</b> — {plus_price}/mo: unlimited AI chat & readings, no balance charges.\n\n"
            "👑 <b>Premium</b> — {premium_price}/mo: everything in Plus + voice replies.\n\n"
            "🖼️ <b>50 infographics per month free</b>, then <b>100 ₽</b> each."
        ),
        "es": (
            "✨ <b>Plus</b> — {plus_price}/mes: chat y tiradas ilimitados.\n\n"
            "👑 <b>Premium</b> — {premium_price}/mes: todo de Plus + respuestas de voz.\n\n"
            "🖼️ <b>50 infografías gratis al mes</b>, luego <b>100 ₽</b> cada una."
        ),
        "pt": (
            "✨ <b>Plus</b> — {plus_price}/mês: chat e leituras ilimitados.\n\n"
            "👑 <b>Premium</b> — {premium_price}/mês: tudo do Plus + respostas por voz.\n\n"
            "🖼️ <b>50 infográficos grátis por mês</b>, depois <b>100 ₽</b> cada."
        ),
    },
    "billing_panel_referral": {
        "ru": "🤝 Приглашай друзей и получай <b>40%</b> с их оплат. Вывод от {min_withdraw} в USDT.",
        "en": "🤝 Invite friends and get <b>40%</b> of their payments. Withdraw from {min_withdraw} in USDT.",
        "es": "🤝 Invita amigos y gana <b>40%</b> de sus pagos. Retiro desde {min_withdraw} en USDT.",
        "pt": "🤝 Convide amigos e ganhe <b>40%</b> dos pagamentos. Saque a partir de {min_withdraw} em USDT.",
    },
    "tier_free": {"ru": "Бесплатный", "en": "Free", "es": "Gratis", "pt": "Grátis"},
    "proactive_nudge": {
        "ru": (
            "✨ Давно не виделись. Звёзды кое-что подсказали о твоём ближайшем цикле — "
            "хочешь, вытяну карту дня или разберём, что тебя сейчас волнует?\n\n"
            "Просто напиши мне или нажми «🏠 На главную»."
        ),
        "en": (
            "✨ It's been a while. The cards have something to say about your current cycle — "
            "want a card of the day or to talk through what's on your mind?\n\n"
            "Just message me or tap «🏠 Home»."
        ),
        "es": (
            "✨ Hace tiempo que no hablamos. Las cartas tienen algo que decir sobre tu ciclo actual. "
            "¿Quieres una carta del día o hablar de lo que te preocupa?\n\n"
            "Solo escríbeme."
        ),
        "pt": (
            "✨ Faz tempo que não nos falamos. As cartas têm algo a dizer sobre seu ciclo atual. "
            "Quer uma carta do dia ou conversar sobre o que te preocupa?\n\n"
            "É só me escrever."
        ),
    },
    "profile_status_title": {
        "ru": "\n\n\n\n---\n\n\n\n### 💼 Подписка и лимиты",
        "en": "\n\n\n\n---\n\n\n\n### 💼 Subscription & limits",
        "es": "\n\n\n\n---\n\n\n\n### 💼 Suscripción y límites",
        "pt": "\n\n\n\n---\n\n\n\n### 💼 Assinatura e limites",
    },
    "profile_status_balance": {
        "ru": "💳 Баланс: {balance}",
        "en": "💳 Balance: {balance}",
        "es": "💳 Saldo: {balance}",
        "pt": "💳 Saldo: {balance}",
    },
    "profile_status_tier_free": {
        "ru": "🎫 Тариф: Бесплатный",
        "en": "🎫 Plan: Free",
        "es": "🎫 Plan: Gratis",
        "pt": "🎫 Plano: Grátis",
    },
    "profile_status_tier_paid": {
        "ru": "🎫 Тариф: {tier} (активен до {expires})",
        "en": "🎫 Plan: {tier} (active until {expires})",
        "es": "🎫 Plan: {tier} (activo hasta {expires})",
        "pt": "🎫 Plano: {tier} (ativo até {expires})",
    },
    "profile_status_messages": {
        "ru": "💬 Сообщений осталось: {left}/{limit}",
        "en": "💬 Messages left: {left}/{limit}",
        "es": "💬 Mensajes restantes: {left}/{limit}",
        "pt": "💬 Mensagens restantes: {left}/{limit}",
    },
    "profile_status_readings": {
        "ru": "🔮 Раскладов осталось: {left}/{limit}",
        "en": "🔮 Readings left: {left}/{limit}",
        "es": "🔮 Tiradas restantes: {left}/{limit}",
        "pt": "🔮 Leituras restantes: {left}/{limit}",
    },
    "profile_status_infographics": {
        "ru": "🖼️ Инфографик в подарок: {left}/{limit} в этом месяце",
        "en": "🖼️ Included infographics: {left}/{limit} this month",
        "es": "🖼️ Infografías incluidas: {left}/{limit} este mes",
        "pt": "🖼️ Infográficos incluídos: {left}/{limit} este mês",
    },
    "profile_status_reset": {
        "ru": "🔄 Лимиты обновятся {date}",
        "en": "🔄 Limits reset on {date}",
        "es": "🔄 Límites se renuevan el {date}",
        "pt": "🔄 Limites renovam em {date}",
    },
    "home_greeting": {
        "ru": "👋 С возвращением, <b>{name}</b>!",
        "en": "👋 Welcome back, <b>{name}</b>!",
        "es": "👋 ¡Bienvenido de nuevo, <b>{name}</b>!",
        "pt": "👋 Bem-vindo de volta, <b>{name}</b>!",
    },
    "home_greeting_anon": {
        "ru": "👋 С возвращением!",
        "en": "👋 Welcome back!",
        "es": "👋 ¡Bienvenido de nuevo!",
        "pt": "👋 Bem-vindo de volta!",
    },
    "home_balance": {
        "ru": "💳 Баланс: <b>{balance}</b>",
        "en": "💳 Balance: <b>{balance}</b>",
        "es": "💳 Saldo: <b>{balance}</b>",
        "pt": "💳 Saldo: <b>{balance}</b>",
    },
    "home_tier_free": {
        "ru": "🎫 Тариф: <b>Бесплатный</b>",
        "en": "🎫 Plan: <b>Free</b>",
        "es": "🎫 Plan: <b>Gratis</b>",
        "pt": "🎫 Plano: <b>Grátis</b>",
    },
    "home_tier_paid": {
        "ru": "🎫 Тариф: <b>{tier}</b> · активен до <b>{expires}</b>",
        "en": "🎫 Plan: <b>{tier}</b> · active until <b>{expires}</b>",
        "es": "🎫 Plan: <b>{tier}</b> · activo hasta <b>{expires}</b>",
        "pt": "🎫 Plano: <b>{tier}</b> · ativo até <b>{expires}</b>",
    },
    "home_free_messages": {
        "ru": "💬 Бесплатные сообщения: <b>{left}/{limit}</b>",
        "en": "💬 Free messages: <b>{left}/{limit}</b>",
        "es": "💬 Mensajes gratis: <b>{left}/{limit}</b>",
        "pt": "💬 Mensagens grátis: <b>{left}/{limit}</b>",
    },
    "home_free_readings": {
        "ru": "🔮 Бесплатные расклады: <b>{left}/{limit}</b>",
        "en": "🔮 Free readings: <b>{left}/{limit}</b>",
        "es": "🔮 Tiradas gratis: <b>{left}/{limit}</b>",
        "pt": "🔮 Leituras grátis: <b>{left}/{limit}</b>",
    },
    "home_infographics": {
        "ru": "🖼️ Инфографика в подарок: <b>{left}/{limit}</b> в этом месяце (50 бесплатно, далее <b>100 ₽</b>)",
        "en": "🖼️ Infographics included: <b>{left}/{limit}</b> this month (50 free, then <b>100 ₽</b>)",
        "es": "🖼️ Infografías incluidas: <b>{left}/{limit}</b> este mes (50 gratis, luego <b>100 ₽</b>)",
        "pt": "🖼️ Infográficos incluídos: <b>{left}/{limit}</b> este mês (50 grátis, depois <b>100 ₽</b>)",
    },
    "home_reset": {
        "ru": "🔄 Лимиты обновятся <b>{date}</b>",
        "en": "🔄 Limits reset on <b>{date}</b>",
        "es": "🔄 Los límites se renuevan el <b>{date}</b>",
        "pt": "🔄 Os limites renovam em <b>{date}</b>",
    },
    "billing_spending_empty": {
        "ru": (
            "### 📋 История трат\n\n"
            "Пока списаний с баланса нет — траты появятся после платных ответов, "
            "раскладов и генерации инфографики."
        ),
        "en": (
            "### 📋 Spending history\n\n"
            "No charges yet — they appear after paid replies, readings, and infographics."
        ),
        "es": "### 📋 Historial de gastos\n\nAún no hay cargos.",
        "pt": "### 📋 Histórico de gastos\n\nAinda não há cobranças.",
    },
    "btn_gift": {
        "ru": "🎁 Получить подарок",
        "en": "🎁 Get a gift",
        "es": "🎁 Recibir regalo",
        "pt": "🎁 Receber presente",
    },
    "gift_offer": {
        "ru": (
            "🎁 Подарок {amount} на баланс!\n\n"
            "Что нужно сделать:\n\n"
            "1. Подпишись на наш канал по кнопке ниже.\n\n"
            "2. Вернись и нажми «✅ Я подписался».\n\n"
            "После проверки я начислю тебе {amount} на личный счёт — их можно тратить "
            "на ответы ИИ, расклады и инфографику. Акция разовая."
        ),
        "en": (
            "🎁 A gift of {amount} to your balance!\n\n"
            "What to do:\n\n"
            "1. Subscribe to our channel via the button below.\n\n"
            "2. Come back and tap «✅ I subscribed».\n\n"
            "Once verified, I'll credit {amount} to your account. One-time offer."
        ),
        "es": (
            "🎁 ¡Un regalo de {amount} a tu saldo!\n\n"
            "Qué hacer:\n\n"
            "1. Suscríbete a nuestro canal con el botón de abajo.\n\n"
            "2. Vuelve y pulsa «✅ Me suscribí».\n\n"
            "Tras verificar, acreditaré {amount} a tu cuenta. Oferta única."
        ),
        "pt": (
            "🎁 Um presente de {amount} no seu saldo!\n\n"
            "O que fazer:\n\n"
            "1. Inscreva-se no nosso canal pelo botão abaixo.\n\n"
            "2. Volte e toque «✅ Me inscrevi».\n\n"
            "Após a verificação, vou creditar {amount} na sua conta. Oferta única."
        ),
    },
    "gift_success": {
        "ru": "🎁 Готово! Подарок {amount} зачислен на твой баланс. Спасибо, что с нами 💜",
        "en": "🎁 Done! A gift of {amount} was added to your balance. Thanks for joining 💜",
        "es": "🎁 ¡Listo! Un regalo de {amount} se añadió a tu saldo. Gracias 💜",
        "pt": "🎁 Pronto! Um presente de {amount} foi adicionado ao seu saldo. Obrigado 💜",
    },
    "gift_already_claimed": {
        "ru": "🎁 Ты уже получил этот подарок — он разовый. Спасибо, что ты с нами!",
        "en": "🎁 You've already claimed this one-time gift. Thanks for being with us!",
        "es": "🎁 Ya recibiste este regalo único. ¡Gracias por estar con nosotros!",
        "pt": "🎁 Você já recebeu este presente único. Obrigado por estar conosco!",
    },
    "gift_not_subscribed": {
        "ru": "Пока не вижу твою подписку 🙈 Подпишись на канал и нажми «✅ Я подписался» ещё раз.",
        "en": "I don't see your subscription yet 🙈 Subscribe and tap «✅ I subscribed» again.",
        "es": "Aún no veo tu suscripción 🙈 Suscríbete y pulsa «✅ Me suscribí» otra vez.",
        "pt": "Ainda não vejo sua inscrição 🙈 Inscreva-se e toque «✅ Me inscrevi» de novo.",
    },
    "btn_gift_open_channel": {
        "ru": "📣 Открыть канал",
        "en": "📣 Open channel",
        "es": "📣 Abrir canal",
        "pt": "📣 Abrir canal",
    },
    "btn_gift_check": {
        "ru": "✅ Я подписался",
        "en": "✅ I subscribed",
        "es": "✅ Me suscribí",
        "pt": "✅ Me inscrevi",
    },
    "billing_spending_title": {
        "ru": "📋 История трат",
        "en": "📋 Spending history",
        "es": "📋 Historial de gastos",
        "pt": "📋 Histórico de gastos",
    },
    "billing_spending_line": {
        "ru": "{when} — {label} — {amount}",
        "en": "{when} — {label} — {amount}",
        "es": "{when} — {label} — {amount}",
        "pt": "{when} — {label} — {amount}",
    },
    "billing_topup_link": {
        "ru": (
            "<b>💳 Пополнение баланса</b>\n\n"
            "Сумма на кнопке: <b>{amount} ₽</b>\n"
            "На баланс Arcana AI зачислится ровно <b>{amount} ₽</b>.\n\n"
            "Платёжная система может добавить свою комиссию сверху — это комиссия провайдера, "
            "не бота.\n\n"
            "После успешной оплаты я сразу пришлю уведомление."
        ),
        "en": (
            "<b>💳 Balance top-up</b>\n\n"
            "Button amount: <b>{amount} ₽</b>.\n"
            "Your Arcana AI balance receives exactly <b>{amount} ₽</b>.\n\n"
            "The payment provider may charge its own fee. "
            "You'll get a notification once payment succeeds."
        ),
        "es": (
            "Pago {amount} ₽ — pulsa el botón.\n\n"
            "El proveedor puede cobrar comisión. "
            "Se acreditan exactamente {amount} ₽ en el saldo.\n\n"
            "Te avisaré cuando se complete el pago."
        ),
        "pt": (
            "Pagamento {amount} ₽ — toque no botão.\n\n"
            "O provedor pode cobrar taxa. "
            "Creditamos exatamente {amount} ₽ no saldo.\n\n"
            "Avisarei quando o pagamento for concluído."
        ),
    },
    "billing_sub_link": {
        "ru": (
            "<b>✨ Подписка {label}</b>\n\n"
            "Стоимость: <b>{amount} ₽/мес</b>\n"
            "После оплаты тариф включится автоматически.\n\n"
            "Что изменится:\n"
            "• AI-чат станет безлимитным\n"
            "• за сообщения не будет списаний с баланса\n\n"
            "Платёжная система может добавить свою комиссию сверху. "
            "Когда оплата пройдёт, я пришлю уведомление."
        ),
        "en": (
            "<b>✨ {label} subscription</b>\n\n"
            "Price: <b>{amount} ₽/mo</b>.\n"
            "After payment, your plan activates automatically.\n\n"
            "The payment provider may charge its own fee. "
            "You'll get a notification once payment succeeds."
        ),
        "es": (
            "Suscripción {label} — {amount} ₽/mes. Pulsa el botón.\n\n"
            "El proveedor puede cobrar comisión. "
            "Importe del botón: {amount} ₽; chat IA ilimitado tras activar.\n\n"
            "Te avisaré cuando se complete el pago."
        ),
        "pt": (
            "Assinatura {label} — {amount} ₽/mês. Toque no botão.\n\n"
            "O provedor pode cobrar taxa. "
            "Valor do botão: {amount} ₽; chat IA ilimitado após ativação.\n\n"
            "Avisarei quando o pagamento for concluído."
        ),
    },
    "billing_payment_success_topup": {
        "ru": (
            "✅ Оплата прошла!\n\n"
            "На баланс зачислено {amount}. Текущий баланс: {balance}."
        ),
        "en": (
            "✅ Payment received!\n\n"
            "{amount} added to your balance. Current balance: {balance}."
        ),
        "es": "✅ ¡Pago recibido!\n\n{amount} acreditados. Saldo: {balance}.",
        "pt": "✅ Pagamento recebido!\n\n{amount} creditados. Saldo: {balance}.",
    },
    "billing_payment_success_sub": {
        "ru": (
            "✅ Оплата прошла!\n\n"
            "Подписка {label} активирована до {expires}. "
            "AI-чат безлимитен и без списаний с баланса."
        ),
        "en": (
            "✅ Payment received!\n\n"
            "{label} plan active until {expires}. Unlimited AI chat included."
        ),
        "es": "✅ ¡Pago recibido!\n\n{label} activa hasta {expires}. Chat IA ilimitado.",
        "pt": "✅ Pagamento recebido!\n\n{label} ativa até {expires}. Chat IA ilimitado.",
    },
    "billing_unknown_tier": {
        "ru": "Неизвестный тариф.",
        "en": "Unknown plan.",
        "es": "Plan desconocido.",
        "pt": "Plano desconhecido.",
    },
    "billing_payment_failed": {
        "ru": "Не удалось создать ссылку на оплату. Попробуй через минуту или напиши в поддержку.",
        "en": "Could not create a payment link. Try again in a minute or contact support.",
        "es": "No se pudo crear el enlace de pago. Inténtalo en un minuto.",
        "pt": "Não foi possível criar o link de pagamento. Tente em um minuto.",
    },
    "btn_pay_now": {
        "ru": "💳 Перейти к оплате",
        "en": "💳 Pay now",
        "es": "💳 Pagar ahora",
        "pt": "💳 Pagar agora",
    },
    "spend_chat": {"ru": "Чат", "en": "Chat", "es": "Chat", "pt": "Chat"},
    "spend_tarot": {"ru": "Расклад", "en": "Reading", "es": "Tirada", "pt": "Leitura"},
    "spend_aura": {"ru": "Аура", "en": "Aura", "es": "Aura", "pt": "Aura"},
    "spend_palm": {"ru": "Ладонь", "en": "Palm", "es": "Palma", "pt": "Palma"},
    "spend_photo": {"ru": "Фото", "en": "Photo", "es": "Foto", "pt": "Foto"},
    # Tarot
    "tarot_daily_query": {
        "ru": "карта дня на сегодня",
        "en": "daily card for today",
        "es": "carta del día de hoy",
        "pt": "carta do dia de hoje",
    },
    "tarot_daily_fallback": {
        "ru": (
            "Сегодня с тобой **{name}**.\n\n"
            "В эзотерической интерпретации это может означать: {description}.\n"
            "Прислушайся к знакам дня и не торопи то, что должно раскрыться естественно."
        ),
        "en": (
            "Today you're with **{name}**.\n\n"
            "In esoteric terms this may mean: {description}.\n"
            "Listen to the day's signs and don't rush what needs to unfold naturally."
        ),
        "es": "Hoy contigo **{name}**.\n\nEn términos esotéricos: {description}.",
        "pt": "Hoje com você **{name}**.\n\nEm termos esotéricos: {description}.",
    },
    "tarot_daily_card_header": {
        "ru": "**Карта дня — {name}**\n\n{text}",
        "en": "**Daily card — {name}**\n\n{text}",
        "es": "**Carta del día — {name}**\n\n{text}",
        "pt": "**Carta do dia — {name}**\n\n{text}",
    },
    "tarot_daily_card_header_prefix": {
        "ru": "**Карта дня —",
        "en": "**Daily card —",
        "es": "**Carta del día —",
        "pt": "**Carta do dia —",
    },
    "tarot_daily_context_msg": {
        "ru": "🌅 Карта дня на сегодня",
        "en": "🌅 Daily card for today",
        "es": "🌅 Carta del día de hoy",
        "pt": "🌅 Carta do dia de hoje",
    },
    "tarot_readings_limit": {
        "ru": (
            "Сегодня уже {limit} раскладов — дневной лимит исчерпан. "
            "Новые расклады будут доступны завтра."
        ),
        "en": "You've used {limit} readings today — daily limit reached. New readings tomorrow.",
        "es": "Límite diario de {limit} tiradas alcanzado. Mañana habrá más.",
        "pt": "Limite diário de {limit} leituras atingido. Amanhã haverá mais.",
    },
    "tarot_readings_monthly_limit": {
        "ru": (
            "Бесплатные расклады на этот месяц закончились ({limit} из {limit}). "
            "Пополни баланс — нажми «Баланс» (на балансе {balance})."
        ),
        "en": (
            "Free readings for this month are used up ({limit}/{limit}). "
            "Top up your balance via «Balance» ({balance} available)."
        ),
        "es": "Tiradas gratis del mes agotadas ({limit}). Recarga saldo ({balance}).",
        "pt": "Leituras grátis do mês esgotadas ({limit}). Recarregue saldo ({balance}).",
    },
    "tarot_local_interpretation": {
        "ru": (
            "Вопрос: {question}\n"
            "Выпали карты: {names}.\n\n"
            "В эзотерической интерпретации расклад может говорить так: {meanings}. "
            "Главный совет — смотреть не только на внешний знак, но и на выбор внутри тебя."
        ),
        "en": (
            "Question: {question}\n"
            "Cards drawn: {names}.\n\n"
            "Esoterically the spread may say: {meanings}. "
            "Main advice — look at the inner choice, not only the outer sign."
        ),
        "es": "Pregunta: {question}\nCartas: {names}.\n\n{meanings}",
        "pt": "Pergunta: {question}\nCartas: {names}.\n\n{meanings}",
    },
    "profile_not_collected": {
        "ru": "Профиль ещё не собран. Нажми /start и пройди короткую анкету.",
        "en": "Profile not set up yet. Tap /start and complete the short form.",
        "es": "Perfil no creado. Pulsa /start y completa la ficha.",
        "pt": "Perfil não criado. Toque /start e complete a ficha.",
    },
    "profile_not_collected_short": {
        "ru": "Профиль ещё не собран.",
        "en": "Profile not set up yet.",
        "es": "Perfil no creado.",
        "pt": "Perfil não criado.",
    },
    "profile_field_unknown": {
        "ru": "Неизвестное поле профиля.",
        "en": "Unknown profile field.",
        "es": "Campo de perfil desconocido.",
        "pt": "Campo de perfil desconhecido.",
    },
    "profile_empty_value": {
        "ru": "Напиши непустое значение.",
        "en": "Enter a non-empty value.",
        "es": "Escribe un valor no vacío.",
        "pt": "Digite um valor não vazio.",
    },
    "profile_updated": {
        "ru": "Обновлено «{label}»: {value}",
        "en": "Updated «{label}»: {value}",
        "es": "Actualizado «{label}»: {value}",
        "pt": "Atualizado «{label}»: {value}",
    },
    "profile_prompt_default": {
        "ru": "Напиши новое значение.",
        "en": "Enter the new value.",
        "es": "Escribe el nuevo valor.",
        "pt": "Digite o novo valor.",
    },
    "profile_not_specified": {
        "ru": "не указана",
        "en": "not specified",
        "es": "no indicada",
        "pt": "não informada",
    },
    "profile_title": {
        "ru": "Мой профиль\n\n{base}{extra}",
        "en": "My profile\n\n{base}{extra}",
        "es": "Mi perfil\n\n{base}{extra}",
        "pt": "Meu perfil\n\n{base}{extra}",
    },
    # Memory
    "memory_empty": {
        "ru": (
            "### 🧠 Память обо мне\n\n"
            "Пока записей нет — бот запоминает важное из переписки автоматически. "
            "Можешь добавить факты вручную кнопкой ниже."
        ),
        "en": (
            "### 🧠 My memory\n\n"
            "No entries yet — the bot remembers important things from chat automatically. "
            "You can add facts manually below."
        ),
        "es": "### 🧠 Mi memoria\n\nSin entradas aún — el bot recuerda automáticamente.",
        "pt": "### 🧠 Minha memória\n\nSem registros ainda — o bot lembra automaticamente.",
    },
    "memory_hint": {
        "ru": "Нажми на запись, чтобы открыть полностью:",
        "en": "Tap an entry to open:",
        "es": "Toca una entrada para abrirla:",
        "pt": "Toque um registro para abrir:",
    },
    "memory_detail": {
        "ru": (
            "🧠 Запись памяти\n\n"
            "Важность: {stars} ({importance}/5)\n"
            "Тип: {type}\n"
            "Добавлено: {when}{happened}\n\n"
            "{description}"
        ),
        "en": (
            "🧠 Memory entry\n\n"
            "Importance: {stars} ({importance}/5)\n"
            "Type: {type}\n"
            "Added: {when}{happened}\n\n"
            "{description}"
        ),
        "es": "🧠 Entrada\n\nImportancia: {stars}\nTipo: {type}\n{description}",
        "pt": "🧠 Registro\n\nImportância: {stars}\nTipo: {type}\n{description}",
    },
    "memory_happened_at": {
        "ru": "\nДата события: {date}",
        "en": "\nEvent date: {date}",
        "es": "\nFecha del evento: {date}",
        "pt": "\nData do evento: {date}",
    },
    "memory_too_short": {
        "ru": "Слишком коротко — напиши хотя бы несколько слов.",
        "en": "Too short — write at least a few words.",
        "es": "Muy corto — escribe al menos unas palabras.",
        "pt": "Muito curto — escreva algumas palavras.",
    },
    "memory_added": {
        "ru": "Запись добавлена в память.",
        "en": "Entry added to memory.",
        "es": "Entrada añadida a la memoria.",
        "pt": "Registro adicionado à memória.",
    },
    "memory_not_found": {
        "ru": "Запись не найдена",
        "en": "Entry not found",
        "es": "Entrada no encontrada",
        "pt": "Registro não encontrado",
    },
    "memory_deleted": {
        "ru": "Запись удалена",
        "en": "Entry deleted",
        "es": "Entrada eliminada",
        "pt": "Registro excluído",
    },
    "memory_add_prompt": {
        "ru": (
            "✏️ Напиши, что запомнить — одним сообщением.\n\n"
            "Например: «Работаю дизайнером, люблю йогу» или «Не напоминай про бывшего»."
        ),
        "en": (
            "✏️ Write what to remember — one message.\n\n"
            "E.g. «I'm a designer, love yoga» or «Don't remind me about my ex»."
        ),
        "es": "✏️ Escribe qué recordar — un mensaje.",
        "pt": "✏️ Escreva o que lembrar — uma mensagem.",
    },
    "mem_type_event": {"ru": "Событие", "en": "Event", "es": "Evento", "pt": "Evento"},
    "mem_type_goal": {"ru": "Цель", "en": "Goal", "es": "Meta", "pt": "Meta"},
    "mem_type_preference": {"ru": "Предпочтение", "en": "Preference", "es": "Preferencia", "pt": "Preferência"},
    "mem_type_relationship": {"ru": "Отношения", "en": "Relationship", "es": "Relación", "pt": "Relacionamento"},
    "mem_type_work": {"ru": "Работа", "en": "Work", "es": "Trabajo", "pt": "Trabalho"},
    "mem_type_health": {"ru": "Здоровье", "en": "Health", "es": "Salud", "pt": "Saúde"},
    "mem_type_money": {"ru": "Деньги", "en": "Money", "es": "Dinero", "pt": "Dinheiro"},
    "mem_type_other": {"ru": "Другое", "en": "Other", "es": "Otro", "pt": "Outro"},
    # Context builder
    "ctx_brevity_free": {
        "ru": "Отвечай коротко и по сути: 2–5 предложений, без воды и длинных списков.",
        "en": "Reply briefly: 2–5 sentences, no filler or long lists.",
        "es": "Responde breve: 2–5 frases, sin relleno.",
        "pt": "Responda breve: 2–5 frases, sem enchimento.",
    },
    "ctx_brevity_paid": {
        "ru": "Отвечай по делу, без лишней воды.",
        "en": "Reply to the point, no filler.",
        "es": "Responde al grano, sin relleno.",
        "pt": "Responda direto, sem enchimento.",
    },
    "ctx_reply_lang_ru": {
        "ru": "Всегда отвечай на языке пользователя.",
        "en": "Always reply in the user's language.",
        "es": "Responde siempre en el idioma del usuario.",
        "pt": "Responda sempre no idioma do usuário.",
    },
    "ctx_topic_scope": {
        "ru": (
            "Строго держись темы Arcana AI: эзотерика, астрология, таро, руны, камни, браслет, дзен, аура, ладонь, "
            "энергия, символы, самопознание. Не раскрывай название модели, разработчика или устройство ИИ. "
            "Не помогай с физикой, программированием, учёбой и прочими посторонними темами — мягко верни к эзотерике."
        ),
        "en": (
            "Stay strictly on Arcana AI topics: esoterics, astrology, tarot, runes, stones, bracelet, zen, aura, palm, "
            "energy, symbols, self-knowledge. Never reveal model name, vendor, or AI internals. "
            "Do not help with physics, programming, homework, or off-topic subjects — gently redirect to esoterics."
        ),
        "es": (
            "Mantente estrictamente en temas de Arcana AI: esoterismo, astrología, tarot, runas, piedras, pulsera, zen, "
            "aura, palma, energía, símbolos. Nunca reveles modelo, proveedor ni detalles técnicos de IA. "
            "No ayudes con física, programación u temas ajenos — redirige al esoterismo."
        ),
        "pt": (
            "Mantenha-se estritamente nos temas do Arcana AI: esoterismo, astrologia, tarot, runas, pedras, pulseira, zen, "
            "aura, palma, energia, símbolos. Nunca revele modelo, fornecedor ou detalhes técnicos de IA. "
            "Não ajude com física, programação ou temas externos — redirecione ao esoterismo."
        ),
    },
    "ctx_markdown_hint": {
        "ru": (
            "Rich-markdown используй умеренно: **жирный** и *курсив* для акцентов, списки `-` где нужно. "
            "Заголовки `###` — только в структурированных ответах (расклад, инструкция, новая большая тема). "
            "В живом диалоге, когда пользователь уточняет или продолжает разговор, отвечай обычным текстом "
            "без заголовка в начале — не начинай каждое сообщение с `###` или **заголовка**. Без HTML-тегов."
        ),
        "en": (
            "Use rich markdown sparingly: **bold** and *italic* for emphasis, `-` lists when helpful. "
            "Use `###` headings only for structured replies (readings, instructions, a major new topic). "
            "In ongoing dialogue, when the user follows up, reply in plain flowing text — "
            "do not start every message with a heading. No HTML tags."
        ),
        "es": (
            "Usa rich markdown con moderación: **negrita** y *cursiva* para énfasis, listas `-` cuando ayuden. "
            "Subtítulos `###` solo en respuestas estructuradas (tirada, instrucción, tema nuevo grande). "
            "En diálogo continuo responde en texto fluido, sin encabezado al inicio de cada mensaje. Sin HTML."
        ),
        "pt": (
            "Use rich markdown com moderação: **negrito** e *itálico* para ênfase, listas `-` quando fizer sentido. "
            "Títulos `###` só em respostas estruturadas (tiragem, instrução, tema novo grande). "
            "Em diálogo contínuo responda em texto fluido, sem título no início de cada mensagem. Sem HTML."
        ),
    },
    "ctx_tier": {
        "ru": "Тариф пользователя: {tier}.",
        "en": "User plan: {tier}.",
        "es": "Plan del usuario: {tier}.",
        "pt": "Plano do usuário: {tier}.",
    },
    "ctx_profile": {
        "ru": (
            "Профиль пользователя: "
            "имя={name}; пол={gender}; дата рождения={birth}; время={birth_time}; "
            "город рождения={birth_city}; семья={relationship}; дети={children}; "
            "сфера={profession}; цель={goal}; беспокоит={concern}; верит в={belief}."
        ),
        "en": (
            "User profile: "
            "name={name}; gender={gender}; birth={birth}; time={birth_time}; "
            "birth city={birth_city}; relationship={relationship}; children={children}; "
            "field={profession}; goal={goal}; concern={concern}; believes={belief}."
        ),
        "es": "Perfil: nombre={name}; género={gender}; nacimiento={birth}; ...",
        "pt": "Perfil: nome={name}; gênero={gender}; nascimento={birth}; ...",
    },
    "ctx_memories_header": {
        "ru": "Релевантная память:\n{lines}",
        "en": "Relevant memory:\n{lines}",
        "es": "Memoria relevante:\n{lines}",
        "pt": "Memória relevante:\n{lines}",
    },
    "ctx_people_header": {
        "ru": "Релевантные люди:\n{lines}",
        "en": "Relevant people:\n{lines}",
        "es": "Personas relevantes:\n{lines}",
        "pt": "Pessoas relevantes:\n{lines}",
    },
    # Handlers extras
    "chat_charged": {
        "ru": "Списано {charged} ₽",
        "en": "Charged {charged} ₽",
        "es": "Cobrado {charged} ₽",
        "pt": "Debitado {charged} ₽",
    },
    "chat_charged_infographic": {
        "ru": "включая инфографику {amount} ₽",
        "en": "including infographic {amount} ₽",
        "es": "incl. infografía {amount} ₽",
        "pt": "incl. infográfico {amount} ₽",
    },
    "chat_balance_after": {
        "ru": "Остаток на балансе: {balance}.",
        "en": "Balance remaining: {balance}.",
        "es": "Saldo restante: {balance}.",
        "pt": "Saldo restante: {balance}.",
    },
    "chat_last_free": {
        "ru": (
            "Это было последнее бесплатное сообщение в этом месяце ({limit}). "
            "Дальше ответы списываются с баланса (5–30 ₽ в зависимости от длины) — пополни его в разделе «Баланс»."
        ),
        "en": (
            "That was your last free message this month ({limit}). "
            "Further replies charge 5–30 ₽ from balance (by length) — top up in «Balance»."
        ),
        "es": "Último mensaje gratis del mes ({limit}). Luego 5–30 ₽ del saldo por respuesta.",
        "pt": "Última mensagem grátis do mês ({limit}). Depois 5–30 ₽ do saldo por resposta.",
    },
    "photo_processing_interrupted": {
        "ru": "Обработка фото прервалась. Попробуй отправить снимок ещё раз ✨",
        "en": "Photo processing was interrupted. Try sending again ✨",
        "es": "Procesamiento interrumpido. Intenta de nuevo ✨",
        "pt": "Processamento interrompido. Tente novamente ✨",
    },
    "photo_infographic_send_failed": {
        "ru": "Инфографика сгенерирована, но не удалось отправить изображение. Попробуй ещё раз.",
        "en": "Infographic generated but image couldn't be sent. Try again.",
        "es": "Infografía generada pero no se pudo enviar. Inténtalo de nuevo.",
        "pt": "Infográfico gerado mas não foi possível enviar. Tente novamente.",
    },
    "profile_edit_header": {
        "ru": (
            "{prefix}### Данные анкеты\n\n"
            "Нажми поле, которое хочешь изменить. Новое значение сразу попадёт в профиль и в контекст ИИ."
        ),
        "en": (
            "{prefix}### Profile data\n\n"
            "Tap a field to edit. The new value goes to your profile and AI context."
        ),
        "es": "{prefix}### Datos del perfil\n\nToca un campo para editar.",
        "pt": "{prefix}### Dados do perfil\n\nToque um campo para editar.",
    },
    "profile_pick_value": {
        "ru": "Выбери новое значение.\n{prompt}",
        "en": "Pick a new value.\n{prompt}",
        "es": "Elige un nuevo valor.\n{prompt}",
        "pt": "Escolha um novo valor.\n{prompt}",
    },
    "profile_type_value": {
        "ru": "{prompt}\n\nНапиши новое значение обычным сообщением в чат.",
        "en": "{prompt}\n\nType the new value as a normal message.",
        "es": "{prompt}\n\nEscribe el nuevo valor.",
        "pt": "{prompt}\n\nDigite o novo valor.",
    },
    "profile_concern_other": {
        "ru": "Напиши своими словами, что сейчас беспокоит больше всего.",
        "en": "In your own words, what concerns you most right now.",
        "es": "Con tus palabras, qué te preocupa más ahora.",
        "pt": "Com suas palavras, o que mais te preocupa agora.",
    },
    "referral_share_text": {
        "ru": (
            "🔗 Твоя личная ссылка:\n{link}\n\n"
            "Перешли её другу — с каждой его или её оплаты тебе будет приходить 40% на реферальный баланс. 💰"
        ),
        "en": (
            "🔗 Your personal link:\n{link}\n\n"
            "Share it — you get 40% of each friend's payment to your referral balance. 💰"
        ),
        "es": "🔗 Tu enlace:\n{link}\n\n40% de cada pago de amigos. 💰",
        "pt": "🔗 Seu link:\n{link}\n\n40% de cada pagamento de amigos. 💰",
    },
    "withdraw_min": {
        "ru": (
            "💸 Вывод доступен от {min}.\n"
            "Сейчас на балансе: {available}.\n\n"
            "Приглашай друзей по своей ссылке — 40% с каждой их оплаты твои. ✨"
        ),
        "en": (
            "💸 Withdrawal from {min}.\n"
            "Available: {available}.\n\n"
            "Invite friends — 40% of their payments is yours. ✨"
        ),
        "es": "💸 Retiro desde {min}. Disponible: {available}.",
        "pt": "💸 Saque a partir de {min}. Disponível: {available}.",
    },
    "withdraw_ask_amount": {
        "ru": (
            "💰 Доступно к выводу: {available}\n\n"
            "Напиши сумму в рублях (от {min}), или нажми кнопку ниже."
        ),
        "en": "💰 Available to withdraw: {available}\n\nEnter amount in ₽ (from {min}), or tap below.",
        "es": "💰 Disponible: {available}\n\nEscribe la suma (desde {min}).",
        "pt": "💰 Disponível: {available}\n\nDigite o valor (a partir de {min}).",
    },
    "withdraw_insufficient": {
        "ru": "Недостаточно средств для вывода.",
        "en": "Insufficient funds for withdrawal.",
        "es": "Fondos insuficientes para retirar.",
        "pt": "Fundos insuficientes para saque.",
    },
    "withdraw_wallet_missing": {
        "ru": "Сохранённый кошелёк не найден. Пришли адрес сообщением.",
        "en": "Saved wallet not found. Send the address in a message.",
        "es": "Billetera guardada no encontrada. Envía la dirección.",
        "pt": "Carteira salva não encontrada. Envie o endereço.",
    },
    "withdraw_wallet_ask_saved": {
        "ru": "💼 Куда отправить USDT (сеть TRC-20)?\n\nУ тебя сохранён кошелёк: {wallet}",
        "en": "💼 Where to send USDT (TRC-20)?\n\nSaved wallet: {wallet}",
        "es": "💼 ¿Dónde enviar USDT (TRC-20)?\n\nBilletera: {wallet}",
        "pt": "💼 Onde enviar USDT (TRC-20)?\n\nCarteira: {wallet}",
    },
    "withdraw_wallet_ask_new": {
        "ru": (
            "💼 Пришли адрес USDT-кошелька в сети TRC-20.\n\n"
            "Он начинается с «T» и состоит из 34 символов. "
            "Я сохраню его — в следующий раз вводить не придётся."
        ),
        "en": (
            "💼 Send your USDT wallet address (TRC-20).\n\n"
            "Starts with «T», 34 characters. I'll save it for next time."
        ),
        "es": "💼 Envía dirección USDT TRC-20. Empieza con «T», 34 caracteres.",
        "pt": "💼 Envie endereço USDT TRC-20. Começa com «T», 34 caracteres.",
    },
    "withdraw_wallet_change": {
        "ru": "✏️ Пришли новый адрес USDT-кошелька (сеть TRC-20).\nОн начинается с «T» и состоит из 34 символов.",
        "en": "✏️ Send new USDT wallet (TRC-20).\nStarts with «T», 34 characters.",
        "es": "✏️ Nueva billetera USDT TRC-20.",
        "pt": "✏️ Nova carteira USDT TRC-20.",
    },
    "withdraw_amount_invalid": {
        "ru": "Напиши сумму числом, например: 3500",
        "en": "Enter amount as a number, e.g. 3500",
        "es": "Escribe la suma como número, ej. 3500",
        "pt": "Digite o valor como número, ex. 3500",
    },
    "withdraw_amount_min": {
        "ru": "Минимальная сумма вывода — {min}. Напиши сумму побольше 🙂",
        "en": "Minimum withdrawal — {min}. Enter a larger amount 🙂",
        "es": "Mínimo de retiro — {min}.",
        "pt": "Mínimo de saque — {min}.",
    },
    "withdraw_amount_over": {
        "ru": "Недостаточно средств. Доступно: {available}. Напиши сумму поменьше.",
        "en": "Insufficient funds. Available: {available}. Enter a smaller amount.",
        "es": "Fondos insuficientes. Disponible: {available}.",
        "pt": "Fundos insuficientes. Disponível: {available}.",
    },
    "withdraw_wallet_invalid": {
        "ru": (
            "Это не похоже на адрес USDT TRC-20. 🤔\n"
            "Он начинается с «T» и состоит из 34 символов. Проверь и пришли ещё раз."
        ),
        "en": "Doesn't look like a USDT TRC-20 address. 🤔\nStarts with «T», 34 chars. Check and retry.",
        "es": "No parece dirección USDT TRC-20. 🤔",
        "pt": "Não parece endereço USDT TRC-20. 🤔",
    },
    "support_message": {
        "ru": (
            "<b>💬 Поддержка Arcana AI</b>\n\n"
            "Напиши нам, если что-то не работает, не пришла оплата, списание выглядит странно "
            "или просто нужен живой ответ по боту.\n\n"
            "Обычно полезно сразу прислать скрин и коротко описать, что нажимал."
        ),
        "en": (
            "<b>💬 Arcana AI support</b>\n\n"
            "Contact us about payments, bugs, unexpected charges, or any bot questions."
        ),
        "es": "💬 Contacta soporte Arcana AI.",
        "pt": "💬 Contate o suporte Arcana AI.",
    },
    "btn_open_support": {
        "ru": "💬 Открыть поддержку",
        "en": "💬 Open support",
        "es": "💬 Abrir soporte",
        "pt": "💬 Abrir suporte",
    },
    "rune_reversed_suffix": {
        "ru": " (перев.)",
        "en": " (rev.)",
        "es": " (inv.)",
        "pt": " (inv.)",
    },
    "stone_pick_failed": {
        "ru": "Не удалось подобрать камни",
        "en": "Could not pick stones",
        "es": "No se pudieron elegir piedras",
        "pt": "Não foi possível escolher pedras",
    },
    "voice_preset_female": {
        "ru": "Мистический женский",
        "en": "Mystical female",
        "es": "Femenino místico",
        "pt": "Feminino místico",
    },
    "voice_preset_male": {
        "ru": "Спокойный мужской",
        "en": "Calm male",
        "es": "Masculino calmado",
        "pt": "Masculino calmo",
    },
    "voice_preset_neutral": {
        "ru": "Мягкий нейтральный",
        "en": "Soft neutral",
        "es": "Neutro suave",
        "pt": "Neutro suave",
    },
    "field_name": {"ru": "Имя", "en": "Name", "es": "Nombre", "pt": "Nome"},
    "field_birth_date": {"ru": "Дата рождения", "en": "Birth date", "es": "Fecha de nacimiento", "pt": "Data de nascimento"},
    "field_birth_time": {"ru": "Время рождения", "en": "Birth time", "es": "Hora de nacimiento", "pt": "Hora de nascimento"},
    "field_birth_city": {"ru": "Город рождения", "en": "Birth city", "es": "Ciudad de nacimiento", "pt": "Cidade de nascimento"},
    "field_gender": {"ru": "Пол", "en": "Gender", "es": "Género", "pt": "Gênero"},
    "field_relationship": {"ru": "Семейное положение", "en": "Relationship status", "es": "Estado civil", "pt": "Estado civil"},
    "field_children": {"ru": "Дети", "en": "Children", "es": "Hijos", "pt": "Filhos"},
    "field_profession": {"ru": "Сфера / работа", "en": "Field / work", "es": "Ámbito / trabajo", "pt": "Área / trabalho"},
    "field_goal": {"ru": "Цель на 6 месяцев", "en": "6-month goal", "es": "Meta a 6 meses", "pt": "Meta em 6 meses"},
    "field_concern": {"ru": "Что беспокоит", "en": "Main concern", "es": "Preocupación", "pt": "Preocupação"},
    "field_belief": {"ru": "Во что веришь", "en": "Beliefs", "es": "Creencias", "pt": "Crenças"},
    "profile_summary_name": {"ru": "Имя", "en": "Name", "es": "Nombre", "pt": "Nome"},
    "profile_summary_birth": {"ru": "Дата рождения", "en": "Birth date", "es": "Fecha de nacimiento", "pt": "Data de nascimento"},
    "profile_summary_time": {"ru": "Время рождения", "en": "Birth time", "es": "Hora", "pt": "Hora"},
    "profile_summary_city": {"ru": "Город рождения", "en": "Birth city", "es": "Ciudad", "pt": "Cidade"},
    "profile_summary_goal": {"ru": "Цель на 6 месяцев", "en": "6-month goal", "es": "Meta 6 meses", "pt": "Meta 6 meses"},
    "profile_summary_concern": {"ru": "Сейчас беспокоит", "en": "Current concern", "es": "Preocupación actual", "pt": "Preocupação atual"},
    "profile_summary_belief": {"ru": "Ближе всего", "en": "Closest to", "es": "Más cercano a", "pt": "Mais próximo de"},
    "profile_summary_gender": {"ru": "Пол", "en": "Gender", "es": "Género", "pt": "Gênero"},
    "profile_summary_relationship": {"ru": "Семейное положение", "en": "Relationship", "es": "Relación", "pt": "Relacionamento"},
    "profile_summary_children": {"ru": "Дети", "en": "Children", "es": "Hijos", "pt": "Filhos"},
    "profile_summary_profession": {"ru": "Сфера", "en": "Field", "es": "Ámbito", "pt": "Área"},
    "profile_summary_archetype": {"ru": "Архетип", "en": "Archetype", "es": "Arquetipo", "pt": "Arquétipo"},
    "profile_summary_memories": {
        "ru": "Запомненных важных событий: {count}",
        "en": "Remembered important events: {count}",
        "es": "Eventos recordados: {count}",
        "pt": "Eventos lembrados: {count}",
    },
    "profile_line": {
        "ru": "{label}: {value}",
        "en": "{label}: {value}",
        "es": "{label}: {value}",
        "pt": "{label}: {value}",
    },
    "onboarding_archetype": {
        "ru": "Искатель",
        "en": "Seeker",
        "es": "Buscador",
        "pt": "Buscador",
    },
    "referral_new_user": {
        "ru": "новый пользователь",
        "en": "new user",
        "es": "nuevo usuario",
        "pt": "novo usuário",
    },
    "referral_friend": {
        "ru": "друг",
        "en": "friend",
        "es": "amigo",
        "pt": "amigo",
    },
    "referral_joined_notify": {
        "ru": (
            "🎉 По твоей ссылке присоединился {name}!\n\n"
            "Как только он или она пополнит баланс или оформит подписку — "
            "тебе начислится {percent}% на реферальный баланс. 💰"
        ),
        "en": (
            "🎉 {name} joined via your link!\n\n"
            "When they top up or subscribe — you get {percent}% to referral balance. 💰"
        ),
        "es": "🎉 {name} se unió por tu enlace. {percent}% cuando pague. 💰",
        "pt": "🎉 {name} entrou pelo seu link. {percent}% quando pagar. 💰",
    },
    "referral_payment_notify": {
        "ru": (
            "💰 {name} пополнил(а) баланс на {amount}!\n"
            "Тебе начислено {reward} ({percent}%) на реферальный баланс. ✨"
        ),
        "en": (
            "💰 {name} topped up {amount}!\n"
            "You earned {reward} ({percent}%) to referral balance. ✨"
        ),
        "es": "💰 {name} recargó {amount}. Ganaste {reward} ({percent}%). ✨",
        "pt": "💰 {name} recarregou {amount}. Você ganhou {reward} ({percent}%). ✨",
    },
    "referral_panel": {
        "ru": (
            "<b>🤝 Реферальная программа</b>\n"
            "<i>Приглашай друзей и получай процент с их оплат.</i>\n\n"
            "<pre>"
            "Доступно к выводу {available}\n"
            "Всего заработано  {total}\n"
            "Приглашено        {count}\n"
            "</pre>\n\n"
            "<b>Как это работает</b>\n"
            "1. Отправь другу свою ссылку.\n"
            "2. Друг регистрируется и пополняет баланс или оформляет подписку.\n"
            "3. Тебе начисляется <b>{percent}%</b> с каждой его оплаты.\n\n"
            "💸 Вывод от <b>{min_withdraw}</b> на USDT TRC-20. Выплаты — по пятницам.\n\n"
            "<b>Твоя ссылка</b>\n"
            "<code>{link}</code>"
        ),
        "en": (
            "<b>🤝 Referral program</b>\n\n"
            "<pre>"
            "Available {available}\n"
            "Earned    {total}\n"
            "Invited   {count}\n"
            "</pre>\n\n"
            "Share your link. When a friend pays, you receive <b>{percent}%</b>.\n"
            "Withdraw from <b>{min_withdraw}</b> in USDT TRC-20.\n\n"
            "<b>Your link</b>\n<code>{link}</code>"
        ),
        "es": (
            "🤝 Programa de referidos\n\n"
            "💰 Disponible: {available}\n"
            "📈 Total ganado: {total}\n"
            "👯 Amigos invitados: {count}\n\n"
            "{percent}% de cada pago. Retiro desde {min_withdraw} USDT.\n\n"
            "🔗 Enlace:\n{link}"
        ),
        "pt": (
            "🤝 Programa de indicação\n\n"
            "💰 Disponível: {available}\n"
            "📈 Total ganho: {total}\n"
            "👯 Amigos convidados: {count}\n\n"
            "{percent}% de cada pagamento. Saque a partir de {min_withdraw} USDT.\n\n"
            "🔗 Link:\n{link}"
        ),
    },
    "referral_stats_panel": {
        "ru": (
            "📊 Статистика рефералки\n\n"
            "📅 Сегодня:\n"
            "👥 Новых приглашённых: {joined_today}\n"
            "💰 Заработано: {earned_today}\n\n"
            "📈 Всего:\n"
            "👯 Приглашено: {count}\n"
            "💰 Заработано: {total}\n"
            "💵 Доступно к выводу: {available}"
        ),
        "en": (
            "📊 Referral statistics\n\n"
            "📅 Today:\n"
            "👥 New invites: {joined_today}\n"
            "💰 Earned: {earned_today}\n\n"
            "📈 All time:\n"
            "👯 Invited: {count}\n"
            "💰 Earned: {total}\n"
            "💵 Available to withdraw: {available}"
        ),
        "es": (
            "📊 Estadísticas de referidos\n\n"
            "📅 Hoy:\n"
            "👥 Nuevos: {joined_today}\n"
            "💰 Ganado: {earned_today}\n\n"
            "📈 Total:\n"
            "👯 Invitados: {count}\n"
            "💰 Ganado: {total}\n"
            "💵 Disponible: {available}"
        ),
        "pt": (
            "📊 Estatísticas de indicação\n\n"
            "📅 Hoje:\n"
            "👥 Novos: {joined_today}\n"
            "💰 Ganho: {earned_today}\n\n"
            "📈 Total:\n"
            "👯 Convidados: {count}\n"
            "💰 Ganho: {total}\n"
            "💵 Disponível: {available}"
        ),
    },
    "referral_list_title": {
        "ru": "👥 Твои приглашённые",
        "en": "👥 Your invited friends",
        "es": "👥 Tus invitados",
        "pt": "👥 Seus convidados",
    },
    "referral_list_sort": {
        "ru": "Сортировка: {sort}",
        "en": "Sort: {sort}",
        "es": "Orden: {sort}",
        "pt": "Ordem: {sort}",
    },
    "referral_sort_newest": {
        "ru": "сначала новые",
        "en": "newest first",
        "es": "más recientes",
        "pt": "mais recentes",
    },
    "referral_sort_oldest": {
        "ru": "сначала старые",
        "en": "oldest first",
        "es": "más antiguos",
        "pt": "mais antigos",
    },
    "referral_list_line": {
        "ru": "{index}. {name} · {date} · +{earned}",
        "en": "{index}. {name} · {date} · +{earned}",
        "es": "{index}. {name} · {date} · +{earned}",
        "pt": "{index}. {name} · {date} · +{earned}",
    },
    "referral_list_empty": {
        "ru": (
            "👥 Пока никого не пригласил.\n\n"
            "Отправь другу свою ссылку — здесь появится список с датой присоединения."
        ),
        "en": (
            "👥 No invited friends yet.\n\n"
            "Share your link — invited users will appear here with join dates."
        ),
        "es": "👥 Aún no hay invitados. Comparte tu enlace.",
        "pt": "👥 Ainda não há convidados. Compartilhe seu link.",
    },
    "referral_withdraw_accepted": {
        "ru": (
            "✅ Заявка на вывод {amount} принята!\n\n"
            "💼 Кошелёк: {wallet} (USDT, TRC-20)\n"
            "📅 Средства поступят в ближайшую пятницу — {payout_date}.\n\n"
            "Сумма уже зарезервирована и списана с реферального баланса."
        ),
        "en": (
            "✅ Withdrawal request for {amount} accepted!\n\n"
            "💼 Wallet: {wallet} (USDT, TRC-20)\n"
            "📅 Funds arrive on the next Friday — {payout_date}.\n\n"
            "The amount is reserved from your referral balance."
        ),
        "es": "✅ Retiro de {amount} aceptado. Cartera: {wallet}. Pago: {payout_date}.",
        "pt": "✅ Saque de {amount} aceito. Carteira: {wallet}. Pagamento: {payout_date}.",
    },
    "referral_withdraw_invalid_wallet": {
        "ru": (
            "Это не похоже на USDT-кошелёк сети TRC-20.\n"
            "Адрес начинается с «T» и состоит из 34 символов, например:\n"
            "TXk3…\n\nПроверь и пришли ещё раз."
        ),
        "en": (
            "This doesn't look like a USDT TRC-20 wallet.\n"
            "Address starts with «T» and has 34 characters.\n\nCheck and send again."
        ),
        "es": "No parece billetera USDT TRC-20. Empieza con «T», 34 caracteres.",
        "pt": "Não parece carteira USDT TRC-20. Começa com «T», 34 caracteres.",
    },
    "referral_withdraw_min_error": {
        "ru": "Минимальная сумма вывода — {min}.",
        "en": "Minimum withdrawal — {min}.",
        "es": "Retiro mínimo — {min}.",
        "pt": "Saque mínimo — {min}.",
    },
    "referral_withdraw_insufficient_error": {
        "ru": "Недостаточно средств. Доступно: {available}.",
        "en": "Insufficient funds. Available: {available}.",
        "es": "Fondos insuficientes. Disponible: {available}.",
        "pt": "Fundos insuficientes. Disponível: {available}.",
    },
    "referral_withdraw_pending_exists": {
        "ru": "У тебя уже есть заявка на вывод в обработке.",
        "en": "You already have a pending withdrawal request.",
        "es": "Ya tienes una solicitud de retiro pendiente.",
        "pt": "Você já tem uma solicitação de saque pendente.",
    },
    "tarot_daily_stale_marker": {
        "ru": "В эзотерической интерпретации это может означать",
        "en": "In esoteric terms this may mean",
        "es": "En términos esotéricos",
        "pt": "Em termos esotéricos",
    },
    "settings_panel": {
        "ru": (
            "<b>⚙️ Настройки</b>\n\n"
            "🌐 Язык: <b>{language}</b>\n\n"
            "🕒 Часовой пояс: <b>{timezone}</b>\n\n"
            "🌙 Тихие часы: <b>{quiet_start} – {quiet_end}</b>\n\n"
            "🔮 Карта дня по утрам: <b>{daily}</b>\n\n"
            "💌 Заботливые сообщения: <b>{proactive}</b>\n\n\n\n---\n\n\n\n"
            "<i>Карта дня</i> — каждое утро присылаю персональную карту с коротким разбором.\n\n"
            "<i>Заботливые сообщения</i> — иногда напоминаю о себе и предлагаю заглянуть, "
            "если давно не общались. В тихие часы не беспокою.\n\n"
            "Нажми кнопку ниже, чтобы изменить параметр или данные анкеты."
        ),
        "en": (
            "<b>⚙️ Settings</b>\n\n"
            "🌐 Language: <b>{language}</b>\n\n"
            "🕒 Timezone: <b>{timezone}</b>\n\n"
            "🌙 Quiet hours: <b>{quiet_start} – {quiet_end}</b>\n\n"
            "🔮 Morning daily card: <b>{daily}</b>\n\n"
            "💌 Caring messages: <b>{proactive}</b>\n\n\n\n---\n\n\n\n"
            "<i>Daily card</i> — every morning I send a personal card with a short reading.\n\n"
            "<i>Caring messages</i> — once in a while I check in if we haven't talked for a bit. "
            "I stay silent during quiet hours.\n\n"
            "Tap a button below to change a setting or profile data."
        ),
        "es": (
            "<b>⚙️ Ajustes</b>\n\n"
            "🌐 Idioma: <b>{language}</b>\n\n"
            "🕒 Zona horaria: <b>{timezone}</b>\n\n"
            "🌙 Horas silenciosas: <b>{quiet_start} – {quiet_end}</b>\n\n"
            "🔮 Carta del día por la mañana: <b>{daily}</b>\n\n"
            "💌 Mensajes de cuidado: <b>{proactive}</b>\n\n\n\n---\n\n\n\n"
            "<i>Carta del día</i> — cada mañana envío una carta personal con una breve lectura.\n\n"
            "<i>Mensajes de cuidado</i> — de vez en cuando te escribo si llevamos tiempo sin hablar. "
            "No molesto en horas silenciosas.\n\n"
            "Toca un botón abajo para cambiar un ajuste o los datos del perfil."
        ),
        "pt": (
            "<b>⚙️ Configurações</b>\n\n"
            "🌐 Idioma: <b>{language}</b>\n\n"
            "🕒 Fuso horário: <b>{timezone}</b>\n\n"
            "🌙 Horário silencioso: <b>{quiet_start} – {quiet_end}</b>\n\n"
            "🔮 Carta do dia de manhã: <b>{daily}</b>\n\n"
            "💌 Mensagens de cuidado: <b>{proactive}</b>\n\n\n\n---\n\n\n\n"
            "<i>Carta do dia</i> — toda manhã envio uma carta pessoal com uma breve leitura.\n\n"
            "<i>Mensagens de cuidado</i> — de vez em quando escrevo se ficamos um tempo sem falar. "
            "Não incomodo no horário silencioso.\n\n"
            "Toque um botão abaixo para alterar uma configuração ou os dados do perfil."
        ),
    },
    "settings_toggle_on": {"ru": "вкл", "en": "on", "es": "sí", "pt": "sim"},
    "settings_toggle_off": {"ru": "выкл", "en": "off", "es": "no", "pt": "não"},
}

PROFILE_FIELD_I18N: dict[str, str] = {
    "name": "field_name",
    "birth_date": "field_birth_date",
    "birth_time": "field_birth_time",
    "birth_city": "field_birth_city",
    "gender": "field_gender",
    "relationship_status": "field_relationship",
    "has_children": "field_children",
    "profession": "field_profession",
    "six_month_goal": "field_goal",
    "main_concern": "field_concern",
    "belief_system": "field_belief",
}

MEMORY_TYPE_I18N: dict[str, str] = {
    "event": "mem_type_event",
    "goal": "mem_type_goal",
    "preference": "mem_type_preference",
    "relationship": "mem_type_relationship",
    "work": "mem_type_work",
    "health": "mem_type_health",
    "money": "mem_type_money",
    "other": "mem_type_other",
}

SPENDING_FEATURE_I18N: dict[str, str] = {
    "chat": "spend_chat",
    "tarot_reading": "spend_tarot",
    "vision_aura": "spend_aura",
    "vision_palm": "spend_palm",
    "vision_custom": "spend_photo",
}

VOICE_PRESET_I18N: dict[str, str] = {
    "female_mystical": "voice_preset_female",
    "male_calm": "voice_preset_male",
    "neutral_soft": "voice_preset_neutral",
}
