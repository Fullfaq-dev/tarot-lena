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
        "ru": "Бесплатные сообщения закончились ({used}/{limit}). Пополни баланс или подключи Plus/Premium — нажми «Баланс».",
        "en": "Free messages used up ({used}/{limit}). Top up or get Plus/Premium — tap «Balance».",
        "es": "Mensajes gratis agotados ({used}/{limit}). Recarga o Plus/Premium — «Saldo».",
        "pt": "Mensagens grátis esgotadas ({used}/{limit}). Recarregue ou Plus/Premium — «Saldo».",
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
    "billing_panel": {
        "ru": (
            "💳 Подписка и баланс\n\n"
            "⭐ Тариф: {tier}\n"
            "💰 Баланс: {balance}\n"
            "🤝 Реферальный баланс: {ref_balance}\n"
            "💬 Бесплатных сообщений: {free_left} из {free_limit}\n"
            "🔮 Бесплатных раскладов: {readings_left} из 3\n\n"
            "✨ Plus — {plus_price}/мес: безлимитный чат.\n"
            "👑 Premium — {premium_price}/мес: безлимитный чат и голосовые ответы.\n\n"
            "🤝 Приглашай друзей и получай 40% с их оплат. Вывод от {min_withdraw} в USDT."
        ),
        "en": (
            "💳 Subscription & balance\n\n"
            "⭐ Plan: {tier}\n"
            "💰 Balance: {balance}\n"
            "🤝 Referral balance: {ref_balance}\n"
            "💬 Free messages: {free_left} of {free_limit}\n"
            "🔮 Free readings: {readings_left} of 3\n\n"
            "✨ Plus — {plus_price}/mo: unlimited chat.\n"
            "👑 Premium — {premium_price}/mo: unlimited chat + voice replies.\n\n"
            "🤝 Invite friends — 40% of their payments. Withdraw from {min_withdraw} USDT."
        ),
        "es": (
            "💳 Suscripción y saldo\n\n"
            "⭐ Plan: {tier}\n"
            "💰 Saldo: {balance}\n"
            "🤝 Saldo referidos: {ref_balance}\n"
            "💬 Mensajes gratis: {free_left} de {free_limit}\n"
            "🔮 Tiradas gratis: {readings_left} de 3\n\n"
            "✨ Plus — {plus_price}/mes: chat ilimitado.\n"
            "👑 Premium — {premium_price}/mes: chat + voz.\n\n"
            "🤝 Invita amigos — 40% de sus pagos. Retiro desde {min_withdraw} USDT."
        ),
        "pt": (
            "💳 Assinatura e saldo\n\n"
            "⭐ Plano: {tier}\n"
            "💰 Saldo: {balance}\n"
            "🤝 Saldo indicação: {ref_balance}\n"
            "💬 Mensagens grátis: {free_left} de {free_limit}\n"
            "🔮 Leituras grátis: {readings_left} de 3\n\n"
            "✨ Plus — {plus_price}/mês: chat ilimitado.\n"
            "👑 Premium — {premium_price}/mês: chat + voz.\n\n"
            "🤝 Convide amigos — 40% dos pagamentos. Saque a partir de {min_withdraw} USDT."
        ),
    },
    "tier_free": {"ru": "Бесплатный", "en": "Free", "es": "Gratis", "pt": "Grátis"},
    "billing_spending_empty": {
        "ru": (
            "📋 История трат\n\n"
            "Пока списаний с баланса нет — траты появятся после платных ответов, "
            "раскладов и генерации инфографики."
        ),
        "en": (
            "📋 Spending history\n\n"
            "No charges yet — they appear after paid replies, readings, and infographics."
        ),
        "es": "📋 Historial de gastos\n\nAún no hay cargos.",
        "pt": "📋 Histórico de gastos\n\nAinda não há cobranças.",
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
        "ru": "Ссылка на оплату {amount} ₽:\n{url}\n\nПосле успешной оплаты баланс обновится автоматически.",
        "en": "Payment link for {amount} ₽:\n{url}\n\nBalance updates automatically after payment.",
        "es": "Enlace de pago {amount} ₽:\n{url}\n\nEl saldo se actualiza tras el pago.",
        "pt": "Link de pagamento {amount} ₽:\n{url}\n\nSaldo atualiza após pagamento.",
    },
    "billing_sub_link": {
        "ru": "Подписка {label} — {amount} ₽/мес.\nСсылка на оплату:\n{url}\n\nПосле оплаты тариф активируется автоматически.",
        "en": "{label} subscription — {amount} ₽/mo.\nPayment link:\n{url}\n\nPlan activates after payment.",
        "es": "Suscripción {label} — {amount} ₽/mes.\nEnlace:\n{url}",
        "pt": "Assinatura {label} — {amount} ₽/mês.\nLink:\n{url}",
    },
    "billing_unknown_tier": {
        "ru": "Неизвестный тариф.",
        "en": "Unknown plan.",
        "es": "Plan desconocido.",
        "pt": "Plano desconhecido.",
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
            "🧠 Память обо мне\n\n"
            "Пока записей нет — бот запоминает важное из переписки автоматически. "
            "Можешь добавить факты вручную кнопкой ниже."
        ),
        "en": (
            "🧠 My memory\n\n"
            "No entries yet — the bot remembers important things from chat automatically. "
            "You can add facts manually below."
        ),
        "es": "🧠 Mi memoria\n\nSin entradas aún — el bot recuerda automáticamente.",
        "pt": "🧠 Minha memória\n\nSem registros ainda — o bot lembra automaticamente.",
    },
    "memory_list_header": {
        "ru": "🧠 Память обо мне\nСортировка: сначала более важные записи.\n{page}\n\nНажми на запись, чтобы открыть полностью:\n",
        "en": "🧠 My memory\nSorted by importance.\n{page}\n\nTap an entry to open:\n",
        "es": "🧠 Mi memoria\nOrdenadas por importancia.\n{page}\n\nToca una entrada:\n",
        "pt": "🧠 Minha memória\nOrdenadas por importância.\n{page}\n\nToque um registro:\n",
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
            "Дальше ответы списываются с баланса — пополни его в разделе «Баланс»."
        ),
        "en": (
            "That was your last free message this month ({limit}). "
            "Further replies charge your balance — top up in «Balance»."
        ),
        "es": "Último mensaje gratis del mes ({limit}). Luego se cobra del saldo.",
        "pt": "Última mensagem grátis do mês ({limit}). Depois debita do saldo.",
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
            "{prefix}Данные анкеты\n\n"
            "Нажми поле, которое хочешь изменить. Новое значение сразу попадёт в профиль и в контекст ИИ."
        ),
        "en": (
            "{prefix}Profile data\n\n"
            "Tap a field to edit. The new value goes to your profile and AI context."
        ),
        "es": "{prefix}Datos del perfil\n\nToca un campo para editar.",
        "pt": "{prefix}Dados do perfil\n\nToque um campo para editar.",
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
        "ru": "💬 Напиши в поддержку Arcana AI — поможем с оплатой, багами и любыми вопросами по боту.",
        "en": "💬 Contact Arcana AI support — billing, bugs, and any bot questions.",
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
            "🤝 Реферальная программа\n\n"
            "💰 Доступно к выводу: {available}\n"
            "📈 Всего заработано: {total}\n"
            "👯 Приглашено друзей: {count}\n\n"
            "Как это работает:\n"
            "1️⃣ Отправь другу свою ссылку\n"
            "2️⃣ Он или она пополняет баланс или оформляет подписку\n"
            "3️⃣ Тебе сразу падает {percent}% от каждой оплаты\n\n"
            "💸 Вывод от {min_withdraw} на USDT (сеть TRC-20). Выплаты — каждую пятницу.\n\n"
            "🔗 Твоя ссылка:\n{link}"
        ),
        "en": (
            "🤝 Referral program\n\n"
            "💰 Available to withdraw: {available}\n"
            "📈 Total earned: {total}\n"
            "👯 Friends invited: {count}\n\n"
            "How it works:\n"
            "1️⃣ Share your link\n"
            "2️⃣ Friend tops up or subscribes\n"
            "3️⃣ You get {percent}% of each payment\n\n"
            "💸 Withdraw from {min_withdraw} in USDT (TRC-20). Payouts every Friday.\n\n"
            "🔗 Your link:\n{link}"
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
            "Настройки\n\n"
            "Язык: {language}\n"
            "Голос ответов: {voice}\n"
            "Часовой пояс: {timezone}\n"
            "Тихие часы: {quiet_start} – {quiet_end}\n"
            "Карта дня утром: {daily}\n"
            "Проактивные сообщения: {proactive}\n\n"
            "Нажми кнопку ниже, чтобы изменить параметр или данные анкеты."
        ),
        "en": (
            "Settings\n\n"
            "Language: {language}\n"
            "Voice: {voice}\n"
            "Timezone: {timezone}\n"
            "Quiet hours: {quiet_start} – {quiet_end}\n"
            "Morning daily card: {daily}\n"
            "Proactive messages: {proactive}\n\n"
            "Tap a button below to change a setting or profile data."
        ),
        "es": (
            "Ajustes\n\n"
            "Idioma: {language}\n"
            "Voz: {voice}\n"
            "Zona horaria: {timezone}\n"
            "Horas silenciosas: {quiet_start} – {quiet_end}\n"
            "Carta del día por la mañana: {daily}\n"
            "Mensajes proactivos: {proactive}\n\n"
            "Toca un botón abajo para cambiar un ajuste o los datos del perfil."
        ),
        "pt": (
            "Configurações\n\n"
            "Idioma: {language}\n"
            "Voz: {voice}\n"
            "Fuso horário: {timezone}\n"
            "Horário silencioso: {quiet_start} – {quiet_end}\n"
            "Carta do dia de manhã: {daily}\n"
            "Mensagens proativas: {proactive}\n\n"
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
