"""Additional i18n strings merged into app.bot.i18n._STRINGS."""

EXTRA_STRINGS: dict[str, dict[str, str]] = {
    "error_need_start": {
        "ru": "Сначала нажми /start, чтобы создать твой профиль.",
        "en": "Tap /start first to create your profile.",
        "es": "Primero pulsa /start para crear tu perfil.",
        "pt": "Toque /start primeiro para criar seu perfil.",
    },
    "error_need_start_short": {
        "ru": "Сначала нажми /start.",
        "en": "Tap /start first.",
        "es": "Primero pulsa /start.",
        "pt": "Toque /start primeiro.",
    },
    "error_finish_onboarding": {
        "ru": "Сначала давай закончим анкету — ответь на последний вопрос или нажми /start.",
        "en": "Let's finish your profile first — answer the last question or tap /start.",
        "es": "Primero terminemos la ficha — responde la última pregunta o pulsa /start.",
        "pt": "Primeiro vamos terminar a ficha — responda a última pergunta ou /start.",
    },
    "error_finish_onboarding_step": {
        "ru": "Сначала давай закончим анкету. Ответь на вопрос выше или нажми кнопку, если она есть.",
        "en": "Let's finish your profile first. Answer the question above or use a button if shown.",
        "es": "Primero terminemos la ficha. Responde arriba o usa un botón si aparece.",
        "pt": "Primeiro vamos terminar a ficha. Responda acima ou use um botão se houver.",
    },
    "error_finish_onboarding_alert": {
        "ru": "Сначала закончи анкету — /start",
        "en": "Finish your profile first — /start",
        "es": "Termina la ficha primero — /start",
        "pt": "Termine a ficha primeiro — /start",
    },
    "error_free_messages_ended": {
        "ru": "Бесплатные сообщения закончились. Ответ спишется с баланса.",
        "en": "Free messages used up. This reply will be charged from your balance.",
        "es": "Mensajes gratis agotados. La respuesta se cobrará del saldo.",
        "pt": "Mensagens grátis esgotadas. A resposta será debitada do saldo.",
    },
    "error_no_model_response": {
        "ru": "Не удалось получить ответ от модели. Попробуй ещё раз через минуту.",
        "en": "Could not get a reply from the model. Try again in a minute.",
        "es": "No se pudo obtener respuesta del modelo. Inténtalo en un minuto.",
        "pt": "Não foi possível obter resposta do modelo. Tente em um minuto.",
    },
    "error_generic": {
        "ru": "Что-то пошло не так. Попробуй ещё раз через минуту.",
        "en": "Something went wrong. Please try again in a minute.",
        "es": "Algo salió mal. Inténtalo de nuevo en un minuto.",
        "pt": "Algo deu errado. Tente novamente em um minuto.",
    },
    "error_process_message": {
        "ru": "Не удалось обработать сообщение. Попробуй ещё раз.",
        "en": "Could not process your message. Please try again.",
        "es": "No se pudo procesar tu mensaje. Inténtalo de nuevo.",
        "pt": "Não foi possível processar sua mensagem. Tente novamente.",
    },
    "error_photo_process": {
        "ru": "Не удалось обработать фото: {detail}",
        "en": "Could not process photo: {detail}",
        "es": "No se pudo procesar la foto: {detail}",
        "pt": "Não foi possível processar a foto: {detail}",
    },
    "error_photo_not_found": {
        "ru": "Фото не найдено. Пришли его ещё раз.",
        "en": "Photo not found. Please send it again.",
        "es": "Foto no encontrada. Envíala de nuevo.",
        "pt": "Foto não encontrada. Envie novamente.",
    },
    "error_photo_ask": {
        "ru": "Напиши, что хочешь узнать по этому фото.",
        "en": "Write what you want to know about this photo.",
        "es": "Escribe qué quieres saber sobre esta foto.",
        "pt": "Escreva o que quer saber sobre esta foto.",
    },
    "error_unknown_photo_mode": {
        "ru": "Неизвестный режим анализа.",
        "en": "Unknown analysis mode.",
        "es": "Modo de análisis desconocido.",
        "pt": "Modo de análise desconhecido.",
    },
    "error_photo_accept": {
        "ru": "Не удалось принять фото. Попробуй отправить ещё раз.",
        "en": "Could not accept the photo. Try sending again.",
        "es": "No se pudo aceptar la foto. Intenta enviarla de nuevo.",
        "pt": "Não foi possível aceitar a foto. Tente enviar novamente.",
    },
    "photo_received_prompt": {
        "ru": (
            "📸 Фото получено! Что хочешь узнать?\n"
            "Аура и ладонь — с инфографикой, 100 ₽ с баланса."
        ),
        "en": (
            "📸 Photo received! What would you like to know?\n"
            "Aura and palm — with infographic, 100 ₽ from balance."
        ),
        "es": (
            "📸 ¡Foto recibida! ¿Qué quieres saber?\n"
            "Aura y palma — con infografía, 100 ₽ del saldo."
        ),
        "pt": (
            "📸 Foto recebida! O que você quer saber?\n"
            "Aura e palma — com infográfico, 100 ₽ do saldo."
        ),
    },
    "error_voice_process": {
        "ru": "Не удалось обработать голосовое: {detail}",
        "en": "Could not process voice message: {detail}",
        "es": "No se pudo procesar el audio: {detail}",
        "pt": "Não foi possível processar o áudio: {detail}",
    },
    "error_voice_process_generic": {
        "ru": "Не удалось обработать голосовое. Попробуй ещё раз или напиши текстом.",
        "en": "Could not process voice message. Try again or type your message.",
        "es": "No se pudo procesar el audio. Inténtalo de nuevo o escribe texto.",
        "pt": "Não foi possível processar o áudio. Tente de novo ou escreva.",
    },
    "error_voice_send": {
        "ru": "Не удалось отправить голосовой файл.",
        "en": "Could not send voice reply.",
        "es": "No se pudo enviar respuesta de voz.",
        "pt": "Não foi possível enviar resposta de voz.",
    },
    "error_reading_not_found": {
        "ru": "Расклад не найден.",
        "en": "Reading not found.",
        "es": "Tirada no encontrada.",
        "pt": "Leitura não encontrada.",
    },
    "error_update_field": {
        "ru": "Не удалось обновить поле.",
        "en": "Could not update field.",
        "es": "No se pudo actualizar el campo.",
        "pt": "Não foi possível atualizar o campo.",
    },
    "error_open_readings": {
        "ru": "Не удалось открыть расклады. Попробуй ещё раз.",
        "en": "Could not open readings. Please try again.",
        "es": "No se pudieron abrir las tiradas. Inténtalo de nuevo.",
        "pt": "Não foi possível abrir leituras. Tente novamente.",
    },
    "error_pick_reading": {
        "ru": "Не удалось выбрать расклад. Попробуй ещё раз.",
        "en": "Could not select reading. Please try again.",
        "es": "No se pudo elegir la tirada. Inténtalo de nuevo.",
        "pt": "Não foi possível escolher a leitura. Tente novamente.",
    },
    "error_reading_limit": {
        "ru": "Лимит раскладов исчерпан",
        "en": "Daily reading limit reached",
        "es": "Límite de tiradas agotado",
        "pt": "Limite de leituras esgotado",
    },
    "reading_ask_question": {
        "ru": "Расклад: {label}\n\nНапиши свой вопрос обычным сообщением в чат — я сделаю расклад и объясню карты.",
        "en": "Reading: {label}\n\nSend your question as a normal message — I'll draw cards and explain them.",
        "es": "Tirada: {label}\n\nEscribe tu pregunta — sacaré cartas y las explicaré.",
        "pt": "Leitura: {label}\n\nEnvie sua pergunta — tirarei cartas e explicarei.",
    },
    "reading_prefix": {
        "ru": "Расклад: {label}\nВопрос: {question}\n\nКарты:\n{cards}\n\n",
        "en": "Reading: {label}\nQuestion: {question}\n\nCards:\n{cards}\n\n",
        "es": "Tirada: {label}\nPregunta: {question}\n\nCartas:\n{cards}\n\n",
        "pt": "Leitura: {label}\nPergunta: {question}\n\nCartas:\n{cards}\n\n",
    },
    "reading_ask_question_text": {
        "ru": "Напиши вопрос для расклада обычным сообщением.",
        "en": "Send your reading question as a normal message.",
        "es": "Escribe tu pregunta para la tirada.",
        "pt": "Envie sua pergunta para a leitura.",
    },
    "choose_photo_mode": {
        "ru": "Выбери вариант анализа кнопками под последним фото.",
        "en": "Choose analysis mode using the buttons under your last photo.",
        "es": "Elige el modo de análisis con los botones bajo la foto.",
        "pt": "Escolha o modo de análise pelos botões abaixo da foto.",
    },
    "error_field_unknown": {
        "ru": "Не удалось определить поле. Открой настройки и попробуй снова.",
        "en": "Could not identify field. Open settings and try again.",
        "es": "No se pudo identificar el campo. Abre ajustes e inténtalo.",
        "pt": "Não foi possível identificar o campo. Abra configurações.",
    },
    "error_no_ai_response": {
        "ru": "Не удалось получить ответ. Попробуй ещё раз.",
        "en": "Could not get a reply. Please try again.",
        "es": "No se pudo obtener respuesta. Inténtalo de nuevo.",
        "pt": "Não foi possível obter resposta. Tente novamente.",
    },
    "referral_invited": {
        "ru": "Тебя пригласил(а) {name}. Спасибо, что пришёл по рекомендации ✨",
        "en": "{name} invited you. Thanks for joining ✨",
        "es": "{name} te invitó. Gracias por unirte ✨",
        "pt": "{name} te convidou. Obrigado por entrar ✨",
    },
    "btn_balance_prefix": {
        "ru": "💰 Баланс:",
        "en": "💰 Balance:",
        "es": "💰 Saldo:",
        "pt": "💰 Saldo:",
    },
    "btn_pagination_back": {
        "ru": "← Назад",
        "en": "← Back",
        "es": "← Atrás",
        "pt": "← Voltar",
    },
    "btn_pagination_forward": {
        "ru": "Вперёд →",
        "en": "Forward →",
        "es": "Adelante →",
        "pt": "Avançar →",
    },
    "btn_support": {
        "ru": "💬 Поддержка",
        "en": "💬 Support",
        "es": "💬 Soporte",
        "pt": "💬 Suporte",
    },
    "btn_legal": {
        "ru": "📄 Юридическая информация",
        "en": "📄 Legal information",
        "es": "📄 Información legal",
        "pt": "📄 Informações legais",
    },
    "btn_profile_data": {
        "ru": "📝 Данные анкеты",
        "en": "📝 Profile data",
        "es": "📝 Datos del perfil",
        "pt": "📝 Dados do perfil",
    },
    "btn_memory": {
        "ru": "🧠 Память обо мне",
        "en": "🧠 My memory",
        "es": "🧠 Mi memoria",
        "pt": "🧠 Minha memória",
    },
    "btn_change_voice": {
        "ru": "🎙 Сменить голос",
        "en": "🎙 Change voice",
        "es": "🎙 Cambiar voz",
        "pt": "🎙 Mudar voz",
    },
    "btn_change_timezone": {
        "ru": "🕐 Сменить часовой пояс",
        "en": "🕐 Change timezone",
        "es": "🕐 Cambiar zona horaria",
        "pt": "🕐 Mudar fuso horário",
    },
    "btn_toggle_daily": {
        "ru": "🌅 Карта дня: вкл/выкл",
        "en": "🌅 Daily card: on/off",
        "es": "🌅 Carta del día: sí/no",
        "pt": "🌅 Carta do dia: sim/não",
    },
    "btn_toggle_proactive": {
        "ru": "🔔 Напоминания: вкл/выкл",
        "en": "🔔 Reminders: on/off",
        "es": "🔔 Recordatorios: sí/no",
        "pt": "🔔 Lembretes: sim/não",
    },
    "btn_memory_add": {
        "ru": "➕ Добавить запись",
        "en": "➕ Add entry",
        "es": "➕ Añadir entrada",
        "pt": "➕ Adicionar registro",
    },
    "btn_memory_delete": {
        "ru": "🗑 Удалить запись",
        "en": "🗑 Delete entry",
        "es": "🗑 Eliminar entrada",
        "pt": "🗑 Excluir registro",
    },
    "btn_back_to_list": {
        "ru": "← К списку",
        "en": "← Back to list",
        "es": "← Volver a la lista",
        "pt": "← Voltar à lista",
    },
    "btn_back_to_settings": {
        "ru": "← Настройки",
        "en": "← Settings",
        "es": "← Ajustes",
        "pt": "← Configurações",
    },
    "btn_back_to_settings_long": {
        "ru": "← Назад в настройки",
        "en": "← Back to settings",
        "es": "← Volver a ajustes",
        "pt": "← Voltar às configurações",
    },
    "btn_spending_history": {
        "ru": "📋 История трат",
        "en": "📋 Spending history",
        "es": "📋 Historial de gastos",
        "pt": "📋 Histórico de gastos",
    },
    "btn_referral_program": {
        "ru": "🤝 Реферальная программа",
        "en": "🤝 Referral program",
        "es": "🤝 Programa de referidos",
        "pt": "🤝 Programa de indicação",
    },
    "btn_my_invite_link": {
        "ru": "🔗 Моя ссылка-приглашение",
        "en": "🔗 My invite link",
        "es": "🔗 Mi enlace de invitación",
        "pt": "🔗 Meu link de convite",
    },
    "btn_share_friend": {
        "ru": "📤 Отправить другу",
        "en": "📤 Share with friend",
        "es": "📤 Enviar a un amigo",
        "pt": "📤 Enviar a um amigo",
    },
    "btn_withdraw": {
        "ru": "💸 Вывести средства",
        "en": "💸 Withdraw funds",
        "es": "💸 Retirar fondos",
        "pt": "💸 Sacar fundos",
    },
    "btn_withdraw_all": {
        "ru": "💸 Вывести всё ({amount})",
        "en": "💸 Withdraw all ({amount})",
        "es": "💸 Retirar todo ({amount})",
        "pt": "💸 Sacar tudo ({amount})",
    },
    "btn_wallet_saved": {
        "ru": "✅ На сохранённый ({short})",
        "en": "✅ To saved ({short})",
        "es": "✅ Al guardado ({short})",
        "pt": "✅ Para salvo ({short})",
    },
    "btn_wallet_new": {
        "ru": "✏️ Указать другой кошелёк",
        "en": "✏️ Enter another wallet",
        "es": "✏️ Indicar otra billetera",
        "pt": "✏️ Informar outra carteira",
    },
    "btn_back_to_billing": {
        "ru": "← Баланс",
        "en": "← Balance",
        "es": "← Saldo",
        "pt": "← Saldo",
    },
    "photo_mode_aura": {
        "ru": "🌈 Аура — 100 ₽",
        "en": "🌈 Aura — 100 ₽",
        "es": "🌈 Aura — 100 ₽",
        "pt": "🌈 Aura — 100 ₽",
    },
    "photo_mode_palm": {
        "ru": "🖐 Ладонь — 100 ₽",
        "en": "🖐 Palm — 100 ₽",
        "es": "🖐 Palma — 100 ₽",
        "pt": "🖐 Palma — 100 ₽",
    },
    "photo_mode_custom": {
        "ru": "💬 Свой вопрос по фото",
        "en": "💬 Custom photo question",
        "es": "💬 Pregunta personalizada",
        "pt": "💬 Pergunta personalizada",
    },
    "reading_love": {
        "ru": "💞 Любовь",
        "en": "💞 Love",
        "es": "💞 Amor",
        "pt": "💞 Amor",
    },
    "reading_relationship": {
        "ru": "💑 Отношения",
        "en": "💑 Relationship",
        "es": "💑 Relación",
        "pt": "💑 Relacionamento",
    },
    "reading_money": {
        "ru": "💸 Деньги",
        "en": "💸 Money",
        "es": "💸 Dinero",
        "pt": "💸 Dinheiro",
    },
    "reading_career": {
        "ru": "🚀 Карьера",
        "en": "🚀 Career",
        "es": "🚀 Carrera",
        "pt": "🚀 Carreira",
    },
    "reading_choice": {
        "ru": "🤔 Выбор решения",
        "en": "🤔 Decision",
        "es": "🤔 Decisión",
        "pt": "🤔 Decisão",
    },
    "reading_past_present_future": {
        "ru": "⏳ Прошлое / настоящее / будущее",
        "en": "⏳ Past / present / future",
        "es": "⏳ Pasado / presente / futuro",
        "pt": "⏳ Passado / presente / futuro",
    },
    "reading_compatibility": {
        "ru": "✨ Совместимость",
        "en": "✨ Compatibility",
        "es": "✨ Compatibilidad",
        "pt": "✨ Compatibilidade",
    },
    "reading_default": {
        "ru": "расклад",
        "en": "reading",
        "es": "tirada",
        "pt": "leitura",
    },
    "gender_male": {
        "ru": "мужской",
        "en": "male",
        "es": "masculino",
        "pt": "masculino",
    },
    "gender_female": {
        "ru": "женский",
        "en": "female",
        "es": "femenino",
        "pt": "feminino",
    },
    "gender_skip": {
        "ru": "не указывать",
        "en": "prefer not to say",
        "es": "no indicar",
        "pt": "não informar",
    },
    "rune_reversed_suffix": {
        "ru": " (перев.)",
        "en": " (rev.)",
        "es": " (inv.)",
        "pt": " (inv.)",
    },
    "share_referral_text": {
        "ru": "🔮 Попробуй AI-таролога — мне очень нравится!",
        "en": "🔮 Try this AI tarot bot — I love it!",
        "es": "🔮 Prueba este bot de tarot IA — ¡me encanta!",
        "pt": "🔮 Experimente este bot de tarot IA — adoro!",
    },
    "history_title": {
        "ru": "История раскладов",
        "en": "Reading history",
        "es": "Historial de tiradas",
        "pt": "Histórico de leituras",
    },
    "history_page": {
        "ru": "Страница {page} из {total}",
        "en": "Page {page} of {total}",
        "es": "Página {page} de {total}",
        "pt": "Página {page} de {total}",
    },
    "history_hint": {
        "ru": "Нажми на расклад, чтобы открыть полное толкование:",
        "en": "Tap a reading to see the full interpretation:",
        "es": "Toca una tirada para ver la interpretación completa:",
        "pt": "Toque uma leitura para ver a interpretação completa:",
    },
    "history_empty": {
        "ru": "Пока раскладов нет. Выбери «Сделать расклад» или просто задай вопрос в чате.",
        "en": "No readings yet. Pick «Tarot reading» or ask a question in chat.",
        "es": "Aún no hay tiradas. Elige «Tirada de tarot» o pregunta en el chat.",
        "pt": "Ainda não há leituras. Escolha «Leitura de tarot» ou pergunte no chat.",
    },
    "reading_format_header": {
        "ru": "Расклад: {label}\nВопрос: {question}\n\nКарты:\n{cards}\n\n{interpretation}",
        "en": "Reading: {label}\nQuestion: {question}\n\nCards:\n{cards}\n\n{interpretation}",
        "es": "Tirada: {label}\nPregunta: {question}\n\nCartas:\n{cards}\n\n{interpretation}",
        "pt": "Leitura: {label}\nPergunta: {question}\n\nCartas:\n{cards}\n\n{interpretation}",
    },
    "info_panel": {
        "ru": (
            "ℹ️ О боте Arcana AI\n\n"
            "Я — твой духовный наставник в Telegram: таро, поддержка в вопросах "
            "отношений, денег, карьеры и внутреннего роста.\n\n"
            "📌 Что умеет бот\n\n"
            "🔮 Сделать расклад — выбери тему, задай вопрос.\n"
            "🌅 Карта дня — короткий прогноз дня.\n"
            "🧘 Дзен — рефлексия без предсказаний.\n"
            "ᚠ Руны и 💎 камни — энергия и подбор.\n"
            "💬 Диалог — помню контекст.\n"
            "📸 Фото — аура, ладонь или свой вопрос.\n"
            "🎙 Голосовые — на Premium отвечаю голосом.\n"
            "📜 История, 💳 баланс, 🤝 рефералка, ⚙️ настройки.\n\n"
            "⚖️ Юридическая информация\n\n"
            "Используя бота, ты соглашаешься с офертой и политикой ПДн.\n"
            "📄 Документы: {legal_url}\n\n"
            "💬 Вопросы — кнопка «Поддержка» или arcaneai.online"
        ),
        "en": (
            "ℹ️ About Arcana AI\n\n"
            "Your spiritual guide on Telegram: tarot, relationships, money, career, inner growth.\n\n"
            "📌 Features\n\n"
            "🔮 Tarot readings · 🌅 Daily card · 🧘 Zen reflection\n"
            "ᚠ Runes & 💎 stones · 💬 Chat with memory\n"
            "📸 Photo aura/palm · 🎙 Voice on Premium\n"
            "📜 History · 💳 Balance · 🤝 Referrals · ⚙️ Settings\n\n"
            "⚖️ Legal\n\n"
            "By using the bot you agree to our terms and privacy policy.\n"
            "📄 Documents: {legal_url}\n\n"
            "💬 Support button or arcaneai.online"
        ),
        "es": (
            "ℹ️ Sobre Arcana AI\n\n"
            "Tu guía espiritual en Telegram: tarot, relaciones, dinero, carrera.\n\n"
            "📌 Funciones\n\n"
            "🔮 Tiradas · 🌅 Carta del día · 🧘 Zen\n"
            "ᚠ Runas y 💎 piedras · 💬 Chat con memoria\n"
            "📸 Foto · 🎙 Voz en Premium\n"
            "📜 Historial · 💳 Saldo · 🤝 Referidos · ⚙️ Ajustes\n\n"
            "⚖️ Legal\n\n"
            "Al usar el bot aceptas términos y privacidad.\n"
            "📄 Documentos: {legal_url}\n\n"
            "💬 Botón Soporte o arcaneai.online"
        ),
        "pt": (
            "ℹ️ Sobre Arcana AI\n\n"
            "Seu guia espiritual no Telegram: tarot, relações, dinheiro, carreira.\n\n"
            "📌 Recursos\n\n"
            "🔮 Leituras · 🌅 Carta do dia · 🧘 Zen\n"
            "ᚠ Runas e 💎 pedras · 💬 Chat com memória\n"
            "📸 Foto · 🎙 Voz no Premium\n"
            "📜 Histórico · 💳 Saldo · 🤝 Indicações · ⚙️ Config\n\n"
            "⚖️ Legal\n\n"
            "Ao usar o bot você aceita termos e privacidade.\n"
            "📄 Documentos: {legal_url}\n\n"
            "💬 Botão Suporte ou arcaneai.online"
        ),
    },
}

READING_TYPE_KEYS = (
    "love",
    "relationship",
    "money",
    "career",
    "choice",
    "past_present_future",
    "compatibility",
)

ONBOARDING_CHOICE_KEYS: dict[str, list[str]] = {
    "gender": ["gender_male", "gender_female", "gender_skip"],
}
