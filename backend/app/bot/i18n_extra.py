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
        "ru": "Бесплатные сообщения закончились. Ответ спишется с баланса (5–30 ₽ в зависимости от длины).",
        "en": "Free messages used up. This reply will charge 5–30 ₽ from your balance (by length).",
        "es": "Mensajes gratis agotados. La respuesta costará 5–30 ₽ del saldo.",
        "pt": "Mensagens grátis esgotadas. A resposta debitará 5–30 ₽ do saldo.",
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
    "vision_custom_default_question": {
        "ru": "Что ты видишь на этом фото?",
        "en": "What do you see in this photo?",
        "es": "¿Qué ves en esta foto?",
        "pt": "O que você vê nesta foto?",
    },
    "vision_custom_instruction": {
        "ru": (
            "{question}\n\n"
            "Ответь по сути вопроса, опираясь на изображение. "
            "2–5 предложений, markdown **жирный** *курсив*, без HTML."
        ),
        "en": (
            "{question}\n\n"
            "Answer the question based on the image. "
            "2–5 sentences, markdown **bold** *italic*, no HTML."
        ),
        "es": "{question}\n\nResponde según la imagen. 2–5 frases, markdown **negrita** *cursiva*.",
        "pt": "{question}\n\nResponda com base na imagem. 2–5 frases, markdown **negrito** *itálico*.",
    },
    "vision_analysis_prefix": {
        "ru": "Анализ: {label}",
        "en": "Analysis: {label}",
        "es": "Análisis: {label}",
        "pt": "Análise: {label}",
    },
    "vision_json_retry": {
        "ru": (
            "Предыдущий ответ не удалось разобрать. Верни ТОЛЬКО JSON для режима {mode}.\n"
            "Предыдущий ответ:\n{raw}"
        ),
        "en": (
            "Could not parse the previous reply. Return ONLY JSON for mode {mode}.\n"
            "Previous reply:\n{raw}"
        ),
        "es": "No se pudo analizar la respuesta. Devuelve SOLO JSON para {mode}.\n{raw}",
        "pt": "Não foi possível analisar a resposta. Retorne APENAS JSON para {mode}.\n{raw}",
    },
    "vision_json_strict": {
        "ru": "Верни только JSON-объект. Поле interpretation обязательно. Без markdown и текста вне JSON.",
        "en": "Return a JSON object only. Field interpretation is required. No markdown or text outside JSON.",
        "es": "Devuelve solo JSON. Campo interpretation obligatorio.",
        "pt": "Retorne apenas JSON. Campo interpretation obrigatório.",
    },
    "vision_fallback_system": {
        "ru": (
            "Ты эзотерический таролог в Telegram. "
            "Ответь 2-4 предложения с markdown **жирный** *курсив*. "
            "Только эзотерика, без медицины и оценки внешности. "
            "Не называй модель и не уходи от темы."
        ),
        "en": (
            "You are an esoteric tarot guide in Telegram. "
            "Reply in 2-4 sentences with markdown **bold** *italic*. "
            "Esoteric only, no medical claims or appearance judgment. "
            "Never name your AI model or go off-topic."
        ),
        "es": "Guía esotérico en Telegram. 2-4 frases, markdown, sin medicina.",
        "pt": "Guia esotérico no Telegram. 2-4 frases, markdown, sem medicina.",
    },
    "vision_model_no_response": {
        "ru": "Модель не вернула ответ по фото. Попробуй ещё раз через минуту.",
        "en": "The model returned no photo reply. Try again in a minute.",
        "es": "El modelo no respondió. Inténtalo en un minuto.",
        "pt": "O modelo não respondeu. Tente novamente em um minuto.",
    },
    "vision_incomplete_response": {
        "ru": "Модель вернула неполный ответ",
        "en": "The model returned an incomplete reply",
        "es": "Respuesta incompleta del modelo",
        "pt": "Resposta incompleta do modelo",
    },
    "vision_task_create_failed": {
        "ru": "Не удалось создать задачу генерации",
        "en": "Could not create generation task",
        "es": "No se pudo crear la tarea de generación",
        "pt": "Não foi possível criar a tarefa de geração",
    },
    "vision_no_image_url": {
        "ru": "Генератор не вернул ссылку на изображение",
        "en": "Generator did not return an image URL",
        "es": "El generador no devolvió URL de imagen",
        "pt": "O gerador não retornou URL da imagem",
    },
    "vision_generation_failed": {
        "ru": "Генерация инфографики не удалась",
        "en": "Infographic generation failed",
        "es": "Falló la generación de infografía",
        "pt": "Falha na geração do infográfico",
    },
    "vision_generation_timeout": {
        "ru": "Превышено время ожидания инфографики",
        "en": "Infographic generation timed out",
        "es": "Tiempo de espera agotado para la infografía",
        "pt": "Tempo esgotado para o infográfico",
    },
    "vision_palm_summary_default": {
        "ru": "Хиромантический разбор ладони",
        "en": "Esoteric palm reading",
        "es": "Lectura esotérica de la palma",
        "pt": "Leitura esotérica da palma",
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
    "reading_question_label": {
        "ru": "Вопрос",
        "en": "Question",
        "es": "Pregunta",
        "pt": "Pergunta",
    },
    "reading_position_n": {
        "ru": "Карта {n}",
        "en": "Card {n}",
        "es": "Carta {n}",
        "pt": "Carta {n}",
    },
    "table_position": {
        "ru": "Позиция",
        "en": "Position",
        "es": "Posición",
        "pt": "Posição",
    },
    "table_card": {
        "ru": "Карта",
        "en": "Card",
        "es": "Carta",
        "pt": "Carta",
    },
    "table_rune": {
        "ru": "Руна",
        "en": "Rune",
        "es": "Runa",
        "pt": "Runa",
    },
    "table_meaning": {
        "ru": "Значение",
        "en": "Meaning",
        "es": "Significado",
        "pt": "Significado",
    },
    "table_energy": {
        "ru": "Энергия",
        "en": "Energy",
        "es": "Energía",
        "pt": "Energia",
    },
    "table_stone": {
        "ru": "Камень",
        "en": "Stone",
        "es": "Piedra",
        "pt": "Pedra",
    },
    "table_properties": {
        "ru": "Свойства",
        "en": "Properties",
        "es": "Propiedades",
        "pt": "Propriedades",
    },
    "table_chakra": {
        "ru": "Чакра",
        "en": "Chakra",
        "es": "Chakra",
        "pt": "Chakra",
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
    "btn_referral_stats": {
        "ru": "📊 Статистика",
        "en": "📊 Statistics",
        "es": "📊 Estadísticas",
        "pt": "📊 Estatísticas",
    },
    "btn_referral_invited_list": {
        "ru": "👥 Список приглашённых",
        "en": "👥 Invited friends",
        "es": "👥 Invitados",
        "pt": "👥 Convidados",
    },
    "btn_back_to_referrals": {
        "ru": "← Рефералка",
        "en": "← Referrals",
        "es": "← Referidos",
        "pt": "← Indicações",
    },
    "btn_back_to_referral_stats": {
        "ru": "← Статистика",
        "en": "← Statistics",
        "es": "← Estadísticas",
        "pt": "← Estatísticas",
    },
    "btn_sort_newest": {
        "ru": "📅 Сначала новые",
        "en": "📅 Newest first",
        "es": "📅 Más recientes",
        "pt": "📅 Mais recentes",
    },
    "btn_sort_oldest": {
        "ru": "📅 Сначала старые",
        "en": "📅 Oldest first",
        "es": "📅 Más antiguos",
        "pt": "📅 Mais antigos",
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
    # --- AI orchestrator prompts ---
    "ai_zen_prompt": {
        "ru": "Режим дзен-рефлексии. Ответь на сообщение пользователя:\n{text}",
        "en": "Zen reflection mode. Reply to the user's message:\n{text}",
        "es": "Modo reflexión zen. Responde al mensaje del usuario:\n{text}",
        "pt": "Modo reflexão zen. Responda à mensagem do usuário:\n{text}",
    },
    "ai_zen_stored": {
        "ru": "🧘 Дзен-рефлексия: {text}",
        "en": "🧘 Zen reflection: {text}",
        "es": "🧘 Reflexión zen: {text}",
        "pt": "🧘 Reflexão zen: {text}",
    },
    "ai_rune_prompt": {
        "ru": (
            "Пользователю уже показана таблица рун. Дай только толкование (до 6 предложений), "
            "не перечисляй руны заново.\n"
            "Вопрос: {question}\nРуны:\n{runes}\n"
            "Объясни энергию сочетания и дай практический совет. Учитывай перевёрнутые руны."
        ),
        "en": (
            "The user already sees a rune table. Give interpretation only (up to 6 sentences), "
            "do not list runes again.\n"
            "Question: {question}\nRunes:\n{runes}\n"
            "Explain the combined energy and give practical advice. Note reversed runes."
        ),
        "es": (
            "El usuario ya ve una tabla de runas. Solo interpretación (hasta 6 frases), "
            "no repitas las runas.\n"
            "Pregunta: {question}\nRunas:\n{runes}\n"
            "Explica la energía combinada y da un consejo práctico."
        ),
        "pt": (
            "O usuário já vê uma tabela de runas. Apenas interpretação (até 6 frases), "
            "não repita as runas.\n"
            "Pergunta: {question}\nRunas:\n{runes}\n"
            "Explique a energia combinada e dê um conselho prático."
        ),
    },
    "ai_rune_stored": {
        "ru": "ᚠ Руны. Вопрос: {question}\nРуны: {names}",
        "en": "ᚠ Runes. Question: {question}\nRunes: {names}",
        "es": "ᚠ Runas. Pregunta: {question}\nRunas: {names}",
        "pt": "ᚠ Runas. Pergunta: {question}\nRunas: {names}",
    },
    "ai_stone_reason_hint": {
        "ru": "\nКраткое обоснование подбора: {reason}",
        "en": "\nBrief selection rationale: {reason}",
        "es": "\nBreve justificación: {reason}",
        "pt": "\nBreve justificativa: {reason}",
    },
    "ai_stone_default_query": {
        "ru": "подбор по профилю soul",
        "en": "pick based on soul profile",
        "es": "elegir según perfil soul",
        "pt": "escolher pelo perfil soul",
    },
    "ai_stone_profile_short": {
        "ru": "по профилю",
        "en": "by profile",
        "es": "por perfil",
        "pt": "pelo perfil",
    },
    "ai_stone_prompt": {
        "ru": (
            "Ты уже подобрал для этого пользователя камни из каталога.{reason_hint}\n"
            "Запрос: {query}\nКамни:\n{stones}\n\n"
            "Объясни персонально (до 6 предложений): почему именно они этому человеку с учётом профиля, "
            "как их энергии дополняют друг друга, как носить или использовать."
        ),
        "en": (
            "You already picked stones from the catalog for this user.{reason_hint}\n"
            "Request: {query}\nStones:\n{stones}\n\n"
            "Explain personally (up to 6 sentences): why these stones fit this person, "
            "how their energies complement each other, how to wear or use them."
        ),
        "es": (
            "Ya elegiste piedras del catálogo para este usuario.{reason_hint}\n"
            "Solicitud: {query}\nPiedras:\n{stones}\n\n"
            "Explica personalmente (hasta 6 frases): por qué encajan, cómo usarlas."
        ),
        "pt": (
            "Você já escolheu pedras do catálogo para este usuário.{reason_hint}\n"
            "Pedido: {query}\nPedras:\n{stones}\n\n"
            "Explique pessoalmente (até 6 frases): por que combinam, como usar."
        ),
    },
    "ai_stone_stored": {
        "ru": "💎 Камни. Запрос: {query}\nПодбор: {names}",
        "en": "💎 Stones. Request: {query}\nSelection: {names}",
        "es": "💎 Piedras. Solicitud: {query}\nSelección: {names}",
        "pt": "💎 Pedras. Pedido: {query}\nSeleção: {names}",
    },
    "ai_bracelet_reason_hint": {
        "ru": "\nОбоснование: {reason}",
        "en": "\nRationale: {reason}",
        "es": "\nJustificación: {reason}",
        "pt": "\nJustificativa: {reason}",
    },
    "ai_bracelet_default_query": {
        "ru": "по профилю soul",
        "en": "based on soul profile",
        "es": "según perfil soul",
        "pt": "pelo perfil soul",
    },
    "ai_bracelet_profile_short": {
        "ru": "по профилю",
        "en": "by profile",
        "es": "por perfil",
        "pt": "pelo perfil",
    },
    "ai_bracelet_prompt": {
        "ru": (
            "Ты подобрал схему браслета для этого пользователя.{reason_hint}\n"
            "Намерение: {query}\nРасположение:\n{layout}\n\n"
            "Объясни (до 7 предложений): почему камни и руна стоят именно так для этого человека, "
            "как сочетать, на что обратить внимание при ношении."
        ),
        "en": (
            "You picked a bracelet layout for this user.{reason_hint}\n"
            "Intention: {query}\nLayout:\n{layout}\n\n"
            "Explain (up to 7 sentences): why stones and rune are placed this way, "
            "how to combine them, what to notice when wearing."
        ),
        "es": (
            "Elegiste un diseño de pulsera para este usuario.{reason_hint}\n"
            "Intención: {query}\nDisposición:\n{layout}\n\n"
            "Explica (hasta 7 frases): por qué están así y cómo usarlos."
        ),
        "pt": (
            "Você escolheu um layout de pulseira para este usuário.{reason_hint}\n"
            "Intenção: {query}\nLayout:\n{layout}\n\n"
            "Explique (até 7 frases): por que estão assim e como usar."
        ),
    },
    "ai_bracelet_stored": {
        "ru": "📿 Браслет. Намерение: {query}",
        "en": "📿 Bracelet. Intention: {query}",
        "es": "📿 Brazalete. Intención: {query}",
        "pt": "📿 Pulseira. Intenção: {query}",
    },
    "ai_tarot_prompt": {
        "ru": (
            "Пользователю уже показаны карты в таблице. Дай только толкование (до 5 предложений), "
            "не перечисляй карты заново.\n"
            "Тип: {reading_type}\nВопрос: {question}\nКарты:\n{cards}\n"
            "Свяжи с вопросом и дай один практический совет."
        ),
        "en": (
            "The user already sees the cards in a table. Give interpretation only (up to 5 sentences), "
            "do not list the cards again.\n"
            "Type: {reading_type}\nQuestion: {question}\nCards:\n{cards}\n"
            "Connect to the question and give one practical tip."
        ),
        "es": (
            "El usuario ya ve las cartas en una tabla. Solo interpretación (hasta 5 frases), "
            "no repitas las cartas.\n"
            "Tipo: {reading_type}\nPregunta: {question}\nCartas:\n{cards}\n"
            "Conecta con la pregunta y da un consejo práctico."
        ),
        "pt": (
            "O usuário já vê as cartas numa tabela. Apenas interpretação (até 5 frases), "
            "não repita as cartas.\n"
            "Tipo: {reading_type}\nPergunta: {question}\nCartas:\n{cards}\n"
            "Conecte à pergunta e dê uma dica prática."
        ),
    },
    "ai_tarot_stored": {
        "ru": "Расклад «{label}». Вопрос: {question}\nКарты: {cards}",
        "en": "Reading «{label}». Question: {question}\nCards: {cards}",
        "es": "Tirada «{label}». Pregunta: {question}\nCartas: {cards}",
        "pt": "Leitura «{label}». Pergunta: {question}\nCartas: {cards}",
    },
    "ai_pick_stones_system": {
        "ru": (
            "Ты эксперт по камням и энергетике в Telegram-боте.\n"
            "Подбери 2–4 камня из каталога для пользователя.\n\n"
            "Правила:\n"
            "1. Если в запросе есть конкретная тема — опирайся на неё.\n"
            "2. Если запрос общий — опирайся на профиль soul в контексте.\n"
            "3. Камни должны дополнять друг друга.\n"
            "4. stone_slugs — только slug из каталога, 2–4 штуки.\n"
            "5. Ответь ТОЛЬКО JSON без markdown:\n"
            '{{"stone_slugs":["slug1","slug2"],"reason_short":"одна строка"}}'
            "\n\nКаталог:\n{catalog}"
        ),
        "en": (
            "You are a stones and energy expert in a Telegram bot.\n"
            "Pick 2–4 stones from the catalog for the user.\n\n"
            "Rules:\n"
            "1. If the request has a specific theme — use it.\n"
            "2. If general — use the soul profile in context.\n"
            "3. Stones should complement each other.\n"
            "4. stone_slugs — catalog slugs only, 2–4 items.\n"
            "5. Reply ONLY with JSON, no markdown:\n"
            '{{"stone_slugs":["slug1","slug2"],"reason_short":"one line"}}'
            "\n\nCatalog:\n{catalog}"
        ),
        "es": (
            "Eres experto en piedras y energía en un bot de Telegram.\n"
            "Elige 2–4 piedras del catálogo.\n"
            "Responde SOLO JSON:\n"
            '{{"stone_slugs":["slug1","slug2"],"reason_short":"una línea"}}'
            "\n\nCatálogo:\n{catalog}"
        ),
        "pt": (
            "Você é especialista em pedras e energia em um bot Telegram.\n"
            "Escolha 2–4 pedras do catálogo.\n"
            "Responda APENAS JSON:\n"
            '{{"stone_slugs":["slug1","slug2"],"reason_short":"uma linha"}}'
            "\n\nCatálogo:\n{catalog}"
        ),
    },
    "ai_pick_stones_default_query": {
        "ru": "подбери камни исходя из моего профиля",
        "en": "pick stones based on my profile",
        "es": "elige piedras según mi perfil",
        "pt": "escolha pedras pelo meu perfil",
    },
    "ai_pick_stones_user": {
        "ru": "Запрос пользователя: {query}\n\nВыбери камни. Верни только JSON.",
        "en": "User request: {query}\n\nPick stones. Return JSON only.",
        "es": "Solicitud: {query}\n\nElige piedras. Solo JSON.",
        "pt": "Pedido: {query}\n\nEscolha pedras. Apenas JSON.",
    },
    "ai_pick_stones_retry": {
        "ru": (
            "Предыдущий ответ не удалось разобрать. Верни только валидный JSON.\n"
            "Запрос: {query}\nПредыдущий ответ:\n{raw}"
        ),
        "en": (
            "Could not parse previous answer. Return valid JSON only.\n"
            "Request: {query}\nPrevious:\n{raw}"
        ),
        "es": "No se pudo parsear. Solo JSON válido.\nSolicitud: {query}\nAnterior:\n{raw}",
        "pt": "Não foi possível parsear. Apenas JSON válido.\nPedido: {query}\nAnterior:\n{raw}",
    },
    "ai_pick_bracelet_system": {
        "ru": (
            "Ты эксперт по камням, рунам и браслетам-оберегам.\n"
            "Подбери схему браслета из каталога.\n"
            "Позиции: center, left, right, clasp_stone, clasp_rune_slug.\n"
            "Ответь ТОЛЬКО JSON:\n"
            '{{"center":"slug","left":"slug","right":"slug","clasp_stone":"slug",'
            '"clasp_rune_slug":"slug","reason_short":"одна строка"}}'
            "\n\nКамни:\n{stones}\n\nРуны:\n{runes}"
        ),
        "en": (
            "You are an expert on stones, runes, and talisman bracelets.\n"
            "Pick a bracelet layout from the catalog.\n"
            "Positions: center, left, right, clasp_stone, clasp_rune_slug.\n"
            "Reply ONLY JSON:\n"
            '{{"center":"slug","left":"slug","right":"slug","clasp_stone":"slug",'
            '"clasp_rune_slug":"slug","reason_short":"one line"}}'
            "\n\nStones:\n{stones}\n\nRunes:\n{runes}"
        ),
        "es": (
            "Experto en piedras, runas y pulseras.\n"
            "Elige diseño. Solo JSON.\n"
            "{{\"center\":\"slug\",...}}\n\nPiedras:\n{stones}\n\nRunas:\n{runes}"
        ),
        "pt": (
            "Especialista em pedras, runas e pulseiras.\n"
            "Escolha layout. Apenas JSON.\n"
            "{{\"center\":\"slug\",...}}\n\nPedras:\n{stones}\n\nRunas:\n{runes}"
        ),
    },
    "ai_pick_bracelet_default_query": {
        "ru": "баланс и защита по моему профилю",
        "en": "balance and protection for my profile",
        "es": "equilibrio y protección según mi perfil",
        "pt": "equilíbrio e proteção pelo meu perfil",
    },
    "ai_pick_bracelet_user": {
        "ru": "Намерение для браслета: {query}\nВерни только JSON.",
        "en": "Bracelet intention: {query}\nReturn JSON only.",
        "es": "Intención del brazalete: {query}\nSolo JSON.",
        "pt": "Intenção da pulseira: {query}\nApenas JSON.",
    },
    "ai_vision_json_system": {
        "ru": (
            "Ты анализируешь фото для эзотерического Telegram-бота.\n"
            "Ответь ТОЛЬКО JSON-объектом, без markdown.\n"
            "interpretation — 2-4 предложения на языке пользователя, markdown **жирный** *курсив*.\n\n"
            'Для aura: {"interpretation":"...", "aura_color":"english color phrase", '
            '"aura_title":"short title", "image_summary":"1-2 sentences for image caption"}\n'
            'Для palm: {"interpretation":"...", "palm_lines":[{"name":"Heart line","note":"brief"},...], '
            '"image_summary":"brief caption"}'
        ),
        "en": (
            "You analyze photos for an esoteric Telegram bot.\n"
            "Reply ONLY with a JSON object, no markdown wrapper.\n"
            "interpretation — 2-4 sentences in the user's language, markdown **bold** *italic*.\n\n"
            'For aura: {"interpretation":"...", "aura_color":"english color phrase", '
            '"aura_title":"short title", "image_summary":"1-2 sentences"}\n'
            'For palm: {"interpretation":"...", "palm_lines":[{"name":"Heart line","note":"brief"},...], '
            '"image_summary":"brief caption"}'
        ),
        "es": (
            "Analizas fotos para un bot esotérico.\n"
            "Responde SOLO JSON.\n"
            'aura: {"interpretation":"...", "aura_color":"...", "aura_title":"...", "image_summary":"..."}'
        ),
        "pt": (
            "Você analisa fotos para um bot esotérico.\n"
            "Responda APENAS JSON.\n"
            'aura: {"interpretation":"...", "aura_color":"...", "aura_title":"...", "image_summary":"..."}'
        ),
    },
    "ai_vision_analysis_aura": {
        "ru": (
            "Проанализируй фото как эзотерическую ауру (развлекательная интерпретация). "
            "Определи цвет энергетического поля, заголовок и описание для инфографики. "
            "Учитывай пол из профиля. Без оценки внешности — только символика."
        ),
        "en": (
            "Analyze the photo as an esoteric aura (entertainment interpretation). "
            "Determine energy field color, title, and description for an infographic. "
            "Use gender from profile. No appearance judgment — symbolism only."
        ),
        "es": "Analiza la foto como aura esotérica. Color, título y descripción para infografía.",
        "pt": "Analise a foto como aura esotérica. Cor, título e descrição para infográfico.",
    },
    "ai_vision_analysis_palm": {
        "ru": (
            "Проанализируй фото ладони как эзотерическую хиромантию (развлекательно). "
            "Опиши линии сердца, ума, жизни и судьбы с краткими пояснениями."
        ),
        "en": (
            "Analyze the palm photo as esoteric palmistry (entertainment). "
            "Describe heart, head, life, and fate lines with brief notes."
        ),
        "es": "Analiza la palma como quiromancia esotérica. Líneas del corazón, mente, vida y destino.",
        "pt": "Analise a palma como quiromancia esotérica. Linhas do coração, mente, vida e destino.",
    },
    "ai_vision_image_base": {
        "ru": (
            "Do NOT copy the reference photo 1:1. Transform and stylize. "
            "Pure white background, black-on-white design, thin elegant lines, rounded cards, "
            "luxury minimal aesthetic, lots of whitespace. All text labels in Russian."
        ),
        "en": (
            "Do NOT copy the reference photo 1:1. Transform and stylize. "
            "Pure white background, black-on-white design, thin elegant lines, rounded cards, "
            "luxury minimal aesthetic, lots of whitespace. All text labels in English."
        ),
        "es": (
            "Do NOT copy the reference photo 1:1. Transform and stylize. "
            "Pure white background, minimal design. All text labels in Spanish."
        ),
        "pt": (
            "Do NOT copy the reference photo 1:1. Transform and stylize. "
            "Pure white background, minimal design. All text labels in Portuguese."
        ),
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

ONBOARDING_CHOICE_STEPS = frozenset(ONBOARDING_CHOICE_KEYS)
