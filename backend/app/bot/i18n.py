from __future__ import annotations

from app.bot.i18n_extra import EXTRA_STRINGS, ONBOARDING_CHOICE_KEYS, READING_TYPE_KEYS
from app.bot.i18n_services import SERVICE_STRINGS

SUPPORTED_LANGUAGES = ("ru", "en", "es", "pt")
FALLBACK_LANGUAGE = "en"

LANGUAGE_LABELS = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "pt": "🇧🇷 Português",
}

TELEGRAM_LANG_MAP = {
    "ru": "ru",
    "uk": "ru",
    "be": "ru",
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "de": "en",
    "fr": "en",
    "it": "en",
    "pl": "en",
    "nl": "en",
    "tr": "en",
    "es": "es",
    "es-es": "es",
    "es-419": "es",
    "es-mx": "es",
    "es-ar": "es",
    "pt": "pt",
    "pt-br": "pt",
    "pt-pt": "pt",
}


def normalize_language(code: str | None) -> str:
    if not code:
        return FALLBACK_LANGUAGE
    normalized = code.strip().lower().replace("_", "-")
    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    if normalized in TELEGRAM_LANG_MAP:
        return TELEGRAM_LANG_MAP[normalized]
    prefix = normalized.split("-", 1)[0]
    if prefix in SUPPORTED_LANGUAGES:
        return prefix
    if prefix in TELEGRAM_LANG_MAP:
        return TELEGRAM_LANG_MAP[prefix]
    return FALLBACK_LANGUAGE


def t(key: str, lang: str = "ru", **kwargs: str) -> str:
    lang = normalize_language(lang)
    table = _STRINGS.get(key)
    if not table:
        return key
    text = table.get(lang) or table.get("ru") or table.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def tf(key: str, lang: str = "ru", **kwargs: str) -> str:
    return t(key, lang, **kwargs)


def reading_type_labels(lang: str = "ru") -> dict[str, str]:
    lang = normalize_language(lang)
    return {key: t(f"reading_{key}", lang) for key in READING_TYPE_KEYS}


def reading_label(key: str, lang: str = "ru") -> str:
    return reading_type_labels(lang).get(key, t("reading_default", lang))


def reading_label_to_type(lang: str = "ru") -> dict[str, str]:
    """Map inline reading button labels to types (full label with emoji only)."""
    return {label.lower(): key for key, label in reading_type_labels(lang).items()}


def onboarding_choice_labels(step_key: str, lang: str = "ru") -> list[str]:
    lang = normalize_language(lang)
    keys = ONBOARDING_CHOICE_KEYS.get(step_key, [])
    return [t(key, lang) for key in keys]


def main_menu_text(lang: str = "ru") -> str:
    return t("main_menu_text", lang)


def readings_menu_text(lang: str = "ru") -> str:
    return t("readings_menu_text", lang)


def btn_readings(lang: str = "ru") -> str:
    return t("btn_readings", lang)


def btn_daily(lang: str = "ru") -> str:
    return t("btn_daily", lang)


def btn_history(lang: str = "ru") -> str:
    return t("btn_history", lang)


def btn_info(lang: str = "ru") -> str:
    return t("btn_info", lang)


def btn_support(lang: str = "ru") -> str:
    return t("btn_support", lang)


def btn_settings(lang: str = "ru") -> str:
    return t("btn_settings", lang)


def btn_language(lang: str = "ru") -> str:
    return t("btn_language", lang)


def btn_zen(lang: str = "ru") -> str:
    return t("btn_zen", lang)


def btn_energy(lang: str = "ru") -> str:
    return t("btn_energy", lang)


def menu_texts(lang: str = "ru") -> set[str]:
    return set(menu_actions(lang).keys())


def menu_actions(lang: str = "ru") -> dict[str, str]:
    return {
        btn_readings(lang): "readings",
        btn_daily(lang): "daily",
        btn_zen(lang): "zen",
        btn_energy(lang): "energy",
        btn_history(lang): "history",
        btn_info(lang): "info",
        btn_support(lang): "support",
        btn_settings(lang): "settings",
        btn_language(lang): "language",
        t("btn_home", lang): "home",
        # Старые подписи для пользователей со старой клавиатурой
        "🔮 Сделать расклад": "readings",
        "🌅 Карта дня": "daily",
        "👤 Мой профиль": "profile",
        "📜 История раскладов": "history",
        "ℹ️ Информация": "info",
        "💬 Поддержка": "support",
        "⚙️ Настройки": "settings",
        "Сделать расклад": "readings",
        "Карта дня": "daily",
        "Мой профиль": "profile",
        "История раскладов": "history",
        "Информация": "info",
        "Поддержка": "support",
        "Настройки": "settings",
        "Подписка и баланс": "billing",
        "🧘 Дзен": "zen",
        "ᚠ Руны · 💎 Камни": "energy",
    }


def onboarding_step_prompt(step_key: str, lang: str = "ru") -> str:
    lang = normalize_language(lang)
    steps = _ONBOARDING_STEPS.get(lang) or _ONBOARDING_STEPS["ru"]
    return steps.get(step_key, steps["name"])


def onboarding_welcome(lang: str = "ru") -> str:
    return t("onboarding_welcome", lang)


def onboarding_complete(lang: str = "ru") -> str:
    return t("onboarding_complete", lang)


def onboarding_resume(lang: str = "ru") -> str:
    return t("onboarding_resume", lang)


_ONBOARDING_STEPS: dict[str, dict[str, str]] = {
    "ru": {
        "name": "Как к тебе обращаться?",
        "gender": "Укажи пол.",
        "birth_date": "Напиши дату рождения в формате ДД.ММ.ГГГГ.",
        "birth_time": "Во сколько ты родился/родилась? Если не знаешь, напиши «не знаю».",
        "birth_city": "В каком городе ты родился/родилась?",
    },
    "en": {
        "name": "What should I call you?",
        "gender": "Please select your gender.",
        "birth_date": "Enter your birth date as DD.MM.YYYY.",
        "birth_time": "What time were you born? If unknown, type «unknown».",
        "birth_city": "What city were you born in?",
    },
    "es": {
        "name": "¿Cómo debo llamarte?",
        "gender": "Indica tu género.",
        "birth_date": "Escribe tu fecha de nacimiento DD.MM.AAAA.",
        "birth_time": "¿A qué hora naciste? Si no sabes, escribe «no sé».",
        "birth_city": "¿En qué ciudad naciste?",
    },
    "pt": {
        "name": "Como devo te chamar?",
        "gender": "Indique seu gênero.",
        "birth_date": "Digite sua data de nascimento DD.MM.AAAA.",
        "birth_time": "A que horas você nasceu? Se não souber, escreva «não sei».",
        "birth_city": "Em qual cidade você nasceu?",
    },
}


def all_menu_texts() -> set[str]:
    texts: set[str] = set()
    for lang in SUPPORTED_LANGUAGES:
        texts.update(menu_texts(lang))
    return texts


_STRINGS: dict[str, dict[str, str]] = {
    "main_menu_text": {
        "ru": (
            "✨ Что делаем дальше?\n\n"
            "Можно выбрать раздел кнопкой ниже или просто написать мне вопрос своими словами.\n\n"
            "Я отвечаю в эзотерическом формате:\n\n"
            "| | |\n"
            "| :--- | :--- |\n"
            "| 🔮 | таро |\n"
            "| 🃏 | символы |\n"
            "| ᚠ | руны |\n"
            "| 💎 | камни |\n"
            "| ✨ | аура |\n"
            "| 🖐 | ладонь |\n"
            "| 💕 | отношения |\n"
            "| 💰 | деньги |\n"
            "| 💼 | карьера |\n"
            "| 🧘 | внутреннее состояние |\n\n"
            "📸 Если пришлёшь фото, я предложу режим: аура, ладонь или свой вопрос по фото."
        ),
        "en": (
            "✨ What shall we do next?\n\n"
            "Pick a section below — or just message me like a personal spiritual guide.\n\n"
            "I answer in an esoteric format:\n\n"
            "| | |\n"
            "| :--- | :--- |\n"
            "| 🔮 | tarot |\n"
            "| 🃏 | symbols |\n"
            "| ᚠ | runes |\n"
            "| 💎 | stones |\n"
            "| ✨ | aura |\n"
            "| 🖐 | palm reading |\n"
            "| 💕 | relationships |\n"
            "| 💰 | money |\n"
            "| 💼 | career |\n"
            "| 🧘 | inner state |\n\n"
            "📸 Send a photo — I'll read your aura or palm lines."
        ),
        "es": (
            "✨ ¿Qué hacemos ahora?\n\n"
            "Elige una sección abajo — o escríbeme como a un guía espiritual personal.\n\n"
            "Respondo en formato esotérico:\n\n"
            "| | |\n"
            "| :--- | :--- |\n"
            "| 🔮 | tarot |\n"
            "| 🃏 | símbolos |\n"
            "| ᚠ | runas |\n"
            "| 💎 | piedras |\n"
            "| ✨ | aura |\n"
            "| 🖐 | palma |\n"
            "| 💕 | relaciones |\n"
            "| 💰 | dinero |\n"
            "| 💼 | carrera |\n"
            "| 🧘 | estado interior |\n\n"
            "📸 Puedes enviar una foto — leeré tu aura o las líneas de la palma."
        ),
        "pt": (
            "✨ O que fazemos agora?\n\n"
            "Escolha uma seção abaixo — ou me escreva como a um guia espiritual pessoal.\n\n"
            "Respondo em formato esotérico:\n\n"
            "| | |\n"
            "| :--- | :--- |\n"
            "| 🔮 | tarot |\n"
            "| 🃏 | símbolos |\n"
            "| ᚠ | runas |\n"
            "| 💎 | pedras |\n"
            "| ✨ | aura |\n"
            "| 🖐 | palma |\n"
            "| 💕 | relacionamentos |\n"
            "| 💰 | dinheiro |\n"
            "| 💼 | carreira |\n"
            "| 🧘 | estado interior |\n\n"
            "📸 Você pode enviar uma foto — leio sua aura ou linhas da palma."
        ),
    },
    "readings_menu_text": {
        "ru": (
            "🔮 Выбери тему расклада.\n\n"
            "После выбора напиши свой вопрос обычным сообщением — "
            "я вытяну карты и объясню, что они значат именно для тебя."
        ),
        "en": (
            "🔮 Choose a reading theme.\n\n"
            "Then send your question as a normal message — "
            "I'll draw cards and explain what they mean for you."
        ),
        "es": (
            "🔮 Elige el tema de la tirada.\n\n"
            "Luego escribe tu pregunta — "
            "sacaré cartas y explicaré qué significan para ti."
        ),
        "pt": (
            "🔮 Escolha o tema da leitura.\n\n"
            "Depois envie sua pergunta — "
            "tirarei cartas e explicarei o que significam para você."
        ),
    },
    "btn_readings": {
        "ru": "🔮 Сделать расклад",
        "en": "🔮 Tarot reading",
        "es": "🔮 Tirada de tarot",
        "pt": "🔮 Leitura de tarot",
    },
    "btn_daily": {
        "ru": "🌅 Карта дня",
        "en": "🌅 Daily card",
        "es": "🌅 Carta del día",
        "pt": "🌅 Carta do dia",
    },
    "btn_history": {
        "ru": "📜 История раскладов",
        "en": "📜 Reading history",
        "es": "📜 Historial de tiradas",
        "pt": "📜 Histórico de leituras",
    },
    "btn_info": {
        "ru": "ℹ️ Информация",
        "en": "ℹ️ Info",
        "es": "ℹ️ Información",
        "pt": "ℹ️ Informações",
    },
    "btn_support": {
        "ru": "💬 Поддержка",
        "en": "💬 Support",
        "es": "💬 Soporte",
        "pt": "💬 Suporte",
    },
    "btn_settings": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
        "es": "⚙️ Ajustes",
        "pt": "⚙️ Configurações",
    },
    "btn_language": {
        "ru": "🌐 Язык",
        "en": "🌐 Language",
        "es": "🌐 Idioma",
        "pt": "🌐 Idioma",
    },
    "language_changed": {
        "ru": "Язык изменён на {label}. Меню обновлено.",
        "en": "Language changed to {label}. Menu updated.",
        "es": "Idioma cambiado a {label}. Menú actualizado.",
        "pt": "Idioma alterado para {label}. Menu atualizado.",
    },
    "choose_language": {
        "ru": "🌐 Выбери язык интерфейса и ответов бота:",
        "en": "🌐 Choose interface and reply language:",
        "es": "🌐 Elige el idioma de la interfaz y las respuestas:",
        "pt": "🌐 Escolha o idioma da interface e das respostas:",
    },
    "btn_zen": {
        "ru": "🧘 Дзен",
        "en": "🧘 Zen",
        "es": "🧘 Zen",
        "pt": "🧘 Zen",
    },
    "btn_energy": {
        "ru": "ᚠ Руны · 💎 Камни",
        "en": "ᚠ Runes · 💎 Stones",
        "es": "ᚠ Runas · 💎 Piedras",
        "pt": "ᚠ Runas · 💎 Pedras",
    },
    "zen_menu_text": {
        "ru": "🧘 Дзен — взгляд внутрь себя\n\nБез предсказаний: мягкая рефлексия, вопросы, самонаблюдение. Может дополнять таро.",
        "en": "🧘 Zen — looking inward\n\nNo predictions: gentle reflection, questions, self-observation. Can complement tarot.",
        "es": "🧘 Zen — mirar hacia dentro\n\nSin predicciones: reflexión suave, preguntas, autoobservación.",
        "pt": "🧘 Zen — olhar para dentro\n\nSem previsões: reflexão suave, perguntas, autoobservação.",
    },
    "zen_daily_intro": {
        "ru": "🧘 Вопрос дня для самонаблюдения:",
        "en": "🧘 Today's question for self-observation:",
        "es": "🧘 Pregunta del día para autoobservación:",
        "pt": "🧘 Pergunta do dia para autoobservação:",
    },
    "zen_reflection_intro": {
        "ru": "🧘 Дзен-рефлексия",
        "en": "🧘 Zen reflection",
        "es": "🧘 Reflexión zen",
        "pt": "🧘 Reflexão zen",
    },
    "zen_ask_prompt": {
        "ru": "🧘 Напиши, что сейчас на душе — без фильтра. Я помогу посмотреть на это изнутри, без предсказаний.",
        "en": "🧘 Write what's on your mind — unfiltered. I'll help you look inward, without predictions.",
        "es": "🧘 Escribe lo que sientes — sin filtro. Te ayudo a mirar hacia dentro, sin predicciones.",
        "pt": "🧘 Escreva o que está no coração — sem filtro. Ajudo a olhar para dentro, sem previsões.",
    },
    "energy_menu_text": {
        "ru": (
            "ᚠ Руны и 💎 камни\n\n"
            "Руны — настрой и послание. Камни — энергия и свойства. "
            "Браслет — сочетание и расположение имеют значение."
        ),
        "en": (
            "ᚠ Runes and 💎 stones\n\n"
            "Runes — tone and message. Stones — energy and properties. "
            "Bracelet — combination and placement matter."
        ),
        "es": (
            "ᚠ Runas y 💎 piedras\n\n"
            "Runas — tono y mensaje. Piedras — energía y propiedades. "
            "Pulsera — la combinación y posición importan."
        ),
        "pt": (
            "ᚠ Runas e 💎 pedras\n\n"
            "Runas — tom e mensagem. Pedras — energia e propriedades. "
            "Pulseira — combinação e posição importam."
        ),
    },
    "rune_ask_prompt": {
        "ru": "ᚠ Напиши вопрос или намерение — я вытяну 3 руны и объясню их сочетание.",
        "en": "ᚠ Write your question or intention — I'll draw 3 runes and explain their combination.",
        "es": "ᚠ Escribe tu pregunta o intención — sacaré 3 runas y explicaré su combinación.",
        "pt": "ᚠ Escreva sua pergunta ou intenção — tirarei 3 runas e explicarei a combinação.",
    },
    "stone_ask_prompt": {
        "ru": (
            "💎 Опиши, что нужно — или просто напиши «подбери камни», "
            "и я выберу их по твоему soul-профилю (дата рождения, цели, контекст)."
        ),
        "en": (
            "💎 Describe what you need — or just write «pick stones for me» "
            "and I'll choose based on your soul profile."
        ),
        "es": (
            "💎 Describe qué necesitas — o escribe «elige piedras» "
            "y las seleccionaré según tu perfil soul."
        ),
        "pt": (
            "💎 Descreva o que precisa — ou escreva «escolha pedras» "
            "e selecionarei com base no seu perfil soul."
        ),
    },
    "bracelet_ask_prompt": {
        "ru": (
            "📿 Опиши намерение для браслета — или «подбери по профилю». "
            "ИИ выберет камни, руну и расположение (центр, бока, замок)."
        ),
        "en": (
            "📿 Describe your bracelet intention — or «pick for my profile». "
            "AI will choose stones, rune, and layout."
        ),
        "es": (
            "📿 Describe la intención del brazalete — o «elige por mi perfil». "
            "La IA elegirá piedras, runa y disposición."
        ),
        "pt": (
            "📿 Descreva a intenção da pulseira — ou «escolha pelo meu perfil». "
            "A IA escolherá pedras, runa e disposição."
        ),
    },
    "rune_result_header": {
        "ru": "ᚠ Выпали руны:",
        "en": "ᚠ Runes drawn:",
        "es": "ᚠ Runas sacadas:",
        "pt": "ᚠ Runas tiradas:",
    },
    "stone_result_header": {
        "ru": "💎 Подбор камней:",
        "en": "💎 Stone selection:",
        "es": "💎 Selección de piedras:",
        "pt": "💎 Seleção de pedras:",
    },
    "bracelet_result_header": {
        "ru": "📿 Схема браслета:",
        "en": "📿 Bracelet layout:",
        "es": "📿 Diseño del brazalete:",
        "pt": "📿 Layout da pulseira:",
    },
    "onboarding_welcome": {
        "ru": (
            "Добро пожаловать. Я буду твоим личным эзотерическим наставником: "
            "помогу с раскладами, прогнозами и бережно запомню важные события твоей истории.\n\n"
            "Сначала — пара базовых вопросов. Остальное узнаю постепенно в разговоре."
        ),
        "en": (
            "Welcome. I'll be your personal esoteric guide — tarot, insights, and I'll remember what matters.\n\n"
            "First, a few basic questions. I'll learn the rest through conversation."
        ),
        "es": (
            "Bienvenido. Seré tu guía esotérico personal — tarot, insights, y recordaré lo importante.\n\n"
            "Primero, unas preguntas básicas. El resto lo iré aprendiendo en la conversación."
        ),
        "pt": (
            "Bem-vindo. Serei seu guia esotérico pessoal — tarot, insights, e lembrarei do que importa.\n\n"
            "Primeiro, algumas perguntas básicas. O resto aprendo na conversa."
        ),
    },
    "onboarding_complete": {
        "ru": (
            "Готово — базовый профиль создан.\n\n"
            "Теперь можешь задать вопрос, попросить расклад, открыть карту дня или зайти в раздел Дзен. "
            "О целях и том, что волнует, спрошу по ходу."
        ),
        "en": (
            "Done — basic profile created.\n\n"
            "Ask a question, request a reading, open your daily card, or try Zen mode. "
            "I'll learn more about you naturally over time."
        ),
        "es": (
            "Listo — perfil básico creado.\n\n"
            "Pregunta, pide una tirada, abre la carta del día o prueba el modo Zen."
        ),
        "pt": (
            "Pronto — perfil básico criado.\n\n"
            "Pergunte, peça uma leitura, abra a carta do dia ou experimente o modo Zen."
        ),
    },
    "onboarding_resume": {
        "ru": "Продолжим анкету.",
        "en": "Let's continue your profile.",
        "es": "Continuemos la ficha.",
        "pt": "Vamos continuar a ficha.",
    },
    "onboarding_gate": {
        "ru": "Сначала давай закончим анкету — ответь на вопрос выше или нажми /start.",
        "en": "Let's finish your profile first — answer above or tap /start.",
        "es": "Primero terminemos la ficha — responde arriba o pulsa /start.",
        "pt": "Primeiro vamos terminar a ficha — responda acima ou /start.",
    },
    "error_telegram_profile": {
        "ru": "Не получилось определить Telegram-профиль. Попробуй еще раз.",
        "en": "Could not detect your Telegram profile. Please try again.",
        "es": "No se pudo detectar tu perfil de Telegram. Inténtalo de nuevo.",
        "pt": "Não foi possível detectar seu perfil do Telegram. Tente novamente.",
    },
    "welcome_back": {
        "ru": "С возвращением! Задай вопрос, выбери расклад, карту дня, дзен или руны с камнями.",
        "en": "Welcome back! Ask a question, pick a reading, daily card, zen, or runes & stones.",
        "es": "¡Bienvenido de nuevo! Pregunta, elige tirada, carta del día, zen o runas y piedras.",
        "pt": "Bem-vindo de volta! Pergunte, escolha leitura, carta do dia, zen ou runas e pedras.",
    },
    "onboarding_type_hint": {
        "ru": "Напиши ответ обычным сообщением в чат.",
        "en": "Type your answer as a normal message.",
        "es": "Escribe tu respuesta como mensaje normal.",
        "pt": "Digite sua resposta como mensagem normal.",
    },
    "first_daily_gift": {
        "ru": "🌅 А вот твоя первая карта дня — бесплатный подарок за знакомство ✨",
        "en": "🌅 Here's your first daily card — a free welcome gift ✨",
        "es": "🌅 Aquí está tu primera carta del día — regalo de bienvenida ✨",
        "pt": "🌅 Aqui está sua primeira carta do dia — presente de boas-vindas ✨",
    },
    "zen_default_system": {
        "ru": "Ты дзен-наставник для самонаблюдения.",
        "en": "You are a zen guide for self-observation.",
        "es": "Eres un guía zen para autoobservación.",
        "pt": "Você é um guia zen para autoobservação.",
    },
    "btn_home": {
        "ru": "🏠 На главную",
        "en": "🏠 Home",
        "es": "🏠 Inicio",
        "pt": "🏠 Início",
    },
    "btn_back": {
        "ru": "← Назад",
        "en": "← Back",
        "es": "← Atrás",
        "pt": "← Voltar",
    },
    "readings_left_today": {
        "ru": "Сегодня осталось раскладов: {left} из {limit}.",
        "en": "Readings left today: {left} of {limit}.",
        "es": "Tiradas restantes hoy: {left} de {limit}.",
        "pt": "Leituras restantes hoje: {left} de {limit}.",
    },
    "readings_left_month": {
        "ru": "Бесплатных раскладов в этом месяце: {left} из {limit}.",
        "en": "Free readings left this month: {left} of {limit}.",
        "es": "Tiradas gratis este mes: {left} de {limit}.",
        "pt": "Leituras grátis neste mês: {left} de {limit}.",
    },
    "btn_topup": {
        "ru": "💳 Пополнить баланс",
        "en": "💳 Top up balance",
        "es": "💳 Recargar saldo",
        "pt": "💳 Recarregar saldo",
    },
    "btn_referrals": {
        "ru": "🤝 Пригласить друга · 40%",
        "en": "🤝 Invite friend · 40%",
        "es": "🤝 Invitar amigo · 40%",
        "pt": "🤝 Convidar amigo · 40%",
    },
    "zen_btn_daily": {
        "ru": "✨ Вопрос дня",
        "en": "✨ Daily question",
        "es": "✨ Pregunta del día",
        "pt": "✨ Pergunta do dia",
    },
    "zen_btn_ask": {
        "ru": "💭 Спросить себя",
        "en": "💭 Ask yourself",
        "es": "💭 Pregúntate",
        "pt": "💭 Pergunte a si",
    },
    "energy_btn_runes": {
        "ru": "ᚠ Расклад рун",
        "en": "ᚠ Rune reading",
        "es": "ᚠ Tirada de runas",
        "pt": "ᚠ Leitura de runas",
    },
    "energy_btn_stones": {
        "ru": "💎 Подбор камней",
        "en": "💎 Stone picker",
        "es": "💎 Elegir piedras",
        "pt": "💎 Escolher pedras",
    },
    "energy_btn_bracelet": {
        "ru": "📿 Браслет",
        "en": "📿 Bracelet",
        "es": "📿 Brazalete",
        "pt": "📿 Pulseira",
    },
}

_STRINGS.update(EXTRA_STRINGS)
_STRINGS.update(SERVICE_STRINGS)
