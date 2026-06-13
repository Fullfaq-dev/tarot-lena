"""Localized rune and stone display names."""

from __future__ import annotations

from app.bot.i18n import normalize_language
from app.services.energy.catalog import Rune, Stone

_RUNE_LOCALES: dict[str, dict[str, dict[str, str]]] = {
    "fehu": {
        "ru": {"name": "Феху", "meaning": "ресурс, начало, изобилие", "energy": "притяжение", "element": "огонь"},
        "en": {"name": "Fehu", "meaning": "resources, beginnings, abundance", "energy": "attraction", "element": "fire"},
        "es": {"name": "Fehu", "meaning": "recursos, inicio, abundancia", "energy": "atracción", "element": "fuego"},
        "pt": {"name": "Fehu", "meaning": "recursos, início, abundância", "energy": "atração", "element": "fogo"},
    },
    "uruz": {
        "ru": {"name": "Уруз", "meaning": "сила, здоровье, решимость", "energy": "опора", "element": "земля"},
        "en": {"name": "Uruz", "meaning": "strength, health, determination", "energy": "foundation", "element": "earth"},
        "es": {"name": "Uruz", "meaning": "fuerza, salud, determinación", "energy": "base", "element": "tierra"},
        "pt": {"name": "Uruz", "meaning": "força, saúde, determinação", "energy": "base", "element": "terra"},
    },
    "thurisaz": {
        "ru": {"name": "Турисаз", "meaning": "защита, преграда, пробуждение", "energy": "защита", "element": "огонь"},
        "en": {"name": "Thurisaz", "meaning": "protection, barrier, awakening", "energy": "protection", "element": "fire"},
        "es": {"name": "Thurisaz", "meaning": "protección, barrera, despertar", "energy": "protección", "element": "fuego"},
        "pt": {"name": "Thurisaz", "meaning": "proteção, barreira, despertar", "energy": "proteção", "element": "fogo"},
    },
    "ansuz": {
        "ru": {"name": "Ансуз", "meaning": "слово, озарение, связь", "energy": "ясность", "element": "воздух"},
        "en": {"name": "Ansuz", "meaning": "word, insight, connection", "energy": "clarity", "element": "air"},
        "es": {"name": "Ansuz", "meaning": "palabra, claridad, conexión", "energy": "claridad", "element": "aire"},
        "pt": {"name": "Ansuz", "meaning": "palavra, insight, conexão", "energy": "clareza", "element": "ar"},
    },
    "raidho": {
        "ru": {"name": "Раидо", "meaning": "путь, движение, ритм", "energy": "движение", "element": "воздух"},
        "en": {"name": "Raidho", "meaning": "journey, movement, rhythm", "energy": "movement", "element": "air"},
        "es": {"name": "Raidho", "meaning": "camino, movimiento, ritmo", "energy": "movimiento", "element": "aire"},
        "pt": {"name": "Raidho", "meaning": "caminho, movimento, ritmo", "energy": "movimento", "element": "ar"},
    },
    "kenaz": {
        "ru": {"name": "Кеназ", "meaning": "огонь творчества, свет внутри", "energy": "творчество", "element": "огонь"},
        "en": {"name": "Kenaz", "meaning": "creative fire, inner light", "energy": "creativity", "element": "fire"},
        "es": {"name": "Kenaz", "meaning": "fuego creativo, luz interior", "energy": "creatividad", "element": "fuego"},
        "pt": {"name": "Kenaz", "meaning": "fogo criativo, luz interior", "energy": "criatividade", "element": "fogo"},
    },
    "gebo": {
        "ru": {"name": "Гебо", "meaning": "дар, обмен, партнёрство", "energy": "гармония", "element": "воздух"},
        "en": {"name": "Gebo", "meaning": "gift, exchange, partnership", "energy": "harmony", "element": "air"},
        "es": {"name": "Gebo", "meaning": "regalo, intercambio, pareja", "energy": "armonía", "element": "aire"},
        "pt": {"name": "Gebo", "meaning": "dom, troca, parceria", "energy": "harmonia", "element": "ar"},
    },
    "wunjo": {
        "ru": {"name": "Вунйо", "meaning": "радость, целостность, успех", "energy": "радость", "element": "земля"},
        "en": {"name": "Wunjo", "meaning": "joy, wholeness, success", "energy": "joy", "element": "earth"},
        "es": {"name": "Wunjo", "meaning": "alegría, plenitud, éxito", "energy": "alegría", "element": "tierra"},
        "pt": {"name": "Wunjo", "meaning": "alegria, plenitude, sucesso", "energy": "alegria", "element": "terra"},
    },
    "hagalaz": {
        "ru": {"name": "Хагалаз", "meaning": "перелом, очищение, перемены", "energy": "трансформация", "element": "лёд"},
        "en": {"name": "Hagalaz", "meaning": "breakthrough, cleansing, change", "energy": "transformation", "element": "ice"},
        "es": {"name": "Hagalaz", "meaning": "quiebre, limpieza, cambio", "energy": "transformación", "element": "hielo"},
        "pt": {"name": "Hagalaz", "meaning": "ruptura, limpeza, mudança", "energy": "transformação", "element": "gelo"},
    },
    "nauthiz": {
        "ru": {"name": "Наутиз", "meaning": "нужда, терпение, внутренняя сила", "energy": "стойкость", "element": "огонь"},
        "en": {"name": "Nauthiz", "meaning": "need, patience, inner strength", "energy": "endurance", "element": "fire"},
        "es": {"name": "Nauthiz", "meaning": "necesidad, paciencia, fuerza interior", "energy": "resistencia", "element": "fuego"},
        "pt": {"name": "Nauthiz", "meaning": "necessidade, paciência, força interior", "energy": "resistência", "element": "fogo"},
    },
    "isa": {
        "ru": {"name": "Иса", "meaning": "пауза, зеркало, созревание", "energy": "покой", "element": "лёд"},
        "en": {"name": "Isa", "meaning": "pause, mirror, ripening", "energy": "stillness", "element": "ice"},
        "es": {"name": "Isa", "meaning": "pausa, espejo, maduración", "energy": "calma", "element": "hielo"},
        "pt": {"name": "Isa", "meaning": "pausa, espelho, amadurecimento", "energy": "calma", "element": "gelo"},
    },
    "jera": {
        "ru": {"name": "Йера", "meaning": "урожай, цикл, терпеливый результат", "energy": "цикл", "element": "земля"},
        "en": {"name": "Jera", "meaning": "harvest, cycle, patient results", "energy": "cycle", "element": "earth"},
        "es": {"name": "Jera", "meaning": "cosecha, ciclo, resultado paciente", "energy": "ciclo", "element": "tierra"},
        "pt": {"name": "Jera", "meaning": "colheita, ciclo, resultado paciente", "energy": "ciclo", "element": "terra"},
    },
    "eihwaz": {
        "ru": {"name": "Эйваз", "meaning": "устойчивость, переход, защита границ", "energy": "защита", "element": "земля"},
        "en": {"name": "Eihwaz", "meaning": "stability, transition, boundary protection", "energy": "protection", "element": "earth"},
        "es": {"name": "Eihwaz", "meaning": "estabilidad, transición, protección de límites", "energy": "protección", "element": "tierra"},
        "pt": {"name": "Eihwaz", "meaning": "estabilidade, transição, proteção de limites", "energy": "proteção", "element": "terra"},
    },
    "perthro": {
        "ru": {"name": "Перт", "meaning": "тайна, судьба, скрытое", "energy": "интуиция", "element": "вода"},
        "en": {"name": "Perthro", "meaning": "mystery, fate, the hidden", "energy": "intuition", "element": "water"},
        "es": {"name": "Perthro", "meaning": "misterio, destino, lo oculto", "energy": "intuición", "element": "agua"},
        "pt": {"name": "Perthro", "meaning": "mistério, destino, o oculto", "energy": "intuição", "element": "água"},
    },
    "algiz": {
        "ru": {"name": "Альгиз", "meaning": "щит, связь с высшим, охрана", "energy": "защита", "element": "воздух"},
        "en": {"name": "Algiz", "meaning": "shield, higher connection, guardianship", "energy": "protection", "element": "air"},
        "es": {"name": "Algiz", "meaning": "escudo, conexión superior, protección", "energy": "protección", "element": "aire"},
        "pt": {"name": "Algiz", "meaning": "escudo, conexão superior, proteção", "energy": "proteção", "element": "ar"},
    },
    "sowilo": {
        "ru": {"name": "Сол", "meaning": "солнце, победа, жизненная сила", "energy": "сила", "element": "огонь"},
        "en": {"name": "Sowilo", "meaning": "sun, victory, life force", "energy": "power", "element": "fire"},
        "es": {"name": "Sowilo", "meaning": "sol, victoria, fuerza vital", "energy": "poder", "element": "fuego"},
        "pt": {"name": "Sowilo", "meaning": "sol, vitória, força vital", "energy": "poder", "element": "fogo"},
    },
    "tiwaz": {
        "ru": {"name": "Тиваз", "meaning": "справедливость, мужество, цель", "energy": "воля", "element": "огонь"},
        "en": {"name": "Tiwaz", "meaning": "justice, courage, purpose", "energy": "will", "element": "fire"},
        "es": {"name": "Tiwaz", "meaning": "justicia, coraje, propósito", "energy": "voluntad", "element": "fuego"},
        "pt": {"name": "Tiwaz", "meaning": "justiça, coragem, propósito", "energy": "vontade", "element": "fogo"},
    },
    "berkano": {
        "ru": {"name": "Беркано", "meaning": "рост, забота, новое начало", "energy": "рост", "element": "земля"},
        "en": {"name": "Berkano", "meaning": "growth, care, new beginnings", "energy": "growth", "element": "earth"},
        "es": {"name": "Berkano", "meaning": "crecimiento, cuidado, nuevo inicio", "energy": "crecimiento", "element": "tierra"},
        "pt": {"name": "Berkano", "meaning": "crescimento, cuidado, novo início", "energy": "crescimento", "element": "terra"},
    },
    "ehwaz": {
        "ru": {"name": "Эхваз", "meaning": "партнёрство, доверие, движение вместе", "energy": "союз", "element": "земля"},
        "en": {"name": "Ehwaz", "meaning": "partnership, trust, moving together", "energy": "union", "element": "earth"},
        "es": {"name": "Ehwaz", "meaning": "asociación, confianza, avanzar juntos", "energy": "unión", "element": "tierra"},
        "pt": {"name": "Ehwaz", "meaning": "parceria, confiança, mover juntos", "energy": "união", "element": "terra"},
    },
    "mannaz": {
        "ru": {"name": "Манназ", "meaning": "человек, самопознание, сообщество", "energy": "осознанность", "element": "воздух"},
        "en": {"name": "Mannaz", "meaning": "humanity, self-knowledge, community", "energy": "awareness", "element": "air"},
        "es": {"name": "Mannaz", "meaning": "humanidad, autoconocimiento, comunidad", "energy": "conciencia", "element": "aire"},
        "pt": {"name": "Mannaz", "meaning": "humanidade, autoconhecimento, comunidade", "energy": "consciência", "element": "ar"},
    },
    "laguz": {
        "ru": {"name": "Лагуз", "meaning": "поток, интуиция, эмоции", "energy": "интуиция", "element": "вода"},
        "en": {"name": "Laguz", "meaning": "flow, intuition, emotions", "energy": "intuition", "element": "water"},
        "es": {"name": "Laguz", "meaning": "flujo, intuición, emociones", "energy": "intuición", "element": "agua"},
        "pt": {"name": "Laguz", "meaning": "fluxo, intuição, emoções", "energy": "intuição", "element": "água"},
    },
    "ingwaz": {
        "ru": {"name": "Ингваз", "meaning": "завершение, семя, внутренняя работа", "energy": "зрелость", "element": "земля"},
        "en": {"name": "Ingwaz", "meaning": "completion, seed, inner work", "energy": "maturity", "element": "earth"},
        "es": {"name": "Ingwaz", "meaning": "cierre, semilla, trabajo interior", "energy": "madurez", "element": "tierra"},
        "pt": {"name": "Ingwaz", "meaning": "conclusão, semente, trabalho interior", "energy": "maturidade", "element": "terra"},
    },
    "dagaz": {
        "ru": {"name": "Дагаз", "meaning": "прорыв, рассвет, ясность", "energy": "просветление", "element": "огонь"},
        "en": {"name": "Dagaz", "meaning": "breakthrough, dawn, clarity", "energy": "illumination", "element": "fire"},
        "es": {"name": "Dagaz", "meaning": "ruptura, amanecer, claridad", "energy": "iluminación", "element": "fuego"},
        "pt": {"name": "Dagaz", "meaning": "ruptura, amanhecer, clareza", "energy": "iluminação", "element": "fogo"},
    },
    "othala": {
        "ru": {"name": "Отала", "meaning": "род, корни, наследие", "energy": "корни", "element": "земля"},
        "en": {"name": "Othala", "meaning": "heritage, roots, inheritance", "energy": "roots", "element": "earth"},
        "es": {"name": "Othala", "meaning": "herencia, raíces, legado", "energy": "raíces", "element": "tierra"},
        "pt": {"name": "Othala", "meaning": "herança, raízes, legado", "energy": "raízes", "element": "terra"},
    },
}

_STONE_LOCALES: dict[str, dict[str, dict[str, str]]] = {
    "amethyst": {
        "ru": {"name": "Аметист", "properties": "спокойствие, интуиция, сон", "energy": "успокоение", "chakra": "коронная"},
        "en": {"name": "Amethyst", "properties": "calm, intuition, sleep", "energy": "soothing", "chakra": "crown"},
        "es": {"name": "Amatista", "properties": "calma, intuición, sueño", "energy": "calma", "chakra": "corona"},
        "pt": {"name": "Ametista", "properties": "calma, intuição, sono", "energy": "calma", "chakra": "coroa"},
    },
    "rose_quartz": {
        "ru": {"name": "Розовый кварц", "properties": "любовь к себе, нежность", "energy": "любовь", "chakra": "сердечная"},
        "en": {"name": "Rose quartz", "properties": "self-love, tenderness", "energy": "love", "chakra": "heart"},
        "es": {"name": "Cuarzo rosa", "properties": "amor propio, ternura", "energy": "amor", "chakra": "corazón"},
        "pt": {"name": "Quartzo rosa", "properties": "amor-próprio, ternura", "energy": "amor", "chakra": "coração"},
    },
    "obsidian": {
        "ru": {"name": "Обсидиан", "properties": "защита, очищение, правда", "energy": "защита", "chakra": "корневая"},
        "en": {"name": "Obsidian", "properties": "protection, cleansing, truth", "energy": "protection", "chakra": "root"},
        "es": {"name": "Obsidiana", "properties": "protección, limpieza, verdad", "energy": "protección", "chakra": "raíz"},
        "pt": {"name": "Obsidiana", "properties": "proteção, limpeza, verdade", "energy": "proteção", "chakra": "raiz"},
    },
    "citrine": {
        "ru": {"name": "Цитрин", "properties": "изобилие, радость, энергия солнца", "energy": "изобилие", "chakra": "солнечное сплетение"},
        "en": {"name": "Citrine", "properties": "abundance, joy, solar energy", "energy": "abundance", "chakra": "solar plexus"},
        "es": {"name": "Citrino", "properties": "abundancia, alegría, energía solar", "energy": "abundancia", "chakra": "plexo solar"},
        "pt": {"name": "Citrino", "properties": "abundância, alegria, energia solar", "energy": "abundância", "chakra": "plexo solar"},
    },
    "lapis": {
        "ru": {"name": "Лапис-лазури", "properties": "мудрость, правда, голос", "energy": "ясность", "chakra": "горловая"},
        "en": {"name": "Lapis lazuli", "properties": "wisdom, truth, voice", "energy": "clarity", "chakra": "throat"},
        "es": {"name": "Lapislázuli", "properties": "sabiduría, verdad, voz", "energy": "claridad", "chakra": "garganta"},
        "pt": {"name": "Lápis-lazúli", "properties": "sabedoria, verdade, voz", "energy": "clareza", "chakra": "garganta"},
    },
    "moonstone": {
        "ru": {"name": "Лунный камень", "properties": "циклы, интуиция", "energy": "интуиция", "chakra": "сакральная"},
        "en": {"name": "Moonstone", "properties": "cycles, intuition", "energy": "intuition", "chakra": "sacral"},
        "es": {"name": "Piedra lunar", "properties": "ciclos, intuición", "energy": "intuición", "chakra": "sacral"},
        "pt": {"name": "Pedra da lua", "properties": "ciclos, intuição", "energy": "intuição", "chakra": "sacral"},
    },
    "tiger_eye": {
        "ru": {"name": "Тигровый глаз", "properties": "уверенность, фокус", "energy": "сила", "chakra": "солнечное сплетение"},
        "en": {"name": "Tiger's eye", "properties": "confidence, focus", "energy": "strength", "chakra": "solar plexus"},
        "es": {"name": "Ojo de tigre", "properties": "confianza, enfoque", "energy": "fuerza", "chakra": "plexo solar"},
        "pt": {"name": "Olho de tigre", "properties": "confiança, foco", "energy": "força", "chakra": "plexo solar"},
    },
    "labradorite": {
        "ru": {"name": "Лабрадорит", "properties": "трансформация, защита ауры", "energy": "трансформация", "chakra": "третий глаз"},
        "en": {"name": "Labradorite", "properties": "transformation, aura protection", "energy": "transformation", "chakra": "third eye"},
        "es": {"name": "Labradorita", "properties": "transformación, protección del aura", "energy": "transformación", "chakra": "tercer ojo"},
        "pt": {"name": "Labradorita", "properties": "transformação, proteção da aura", "energy": "transformação", "chakra": "terceiro olho"},
    },
    "clear_quartz": {
        "ru": {"name": "Горный хрусталь", "properties": "усилитель, ясность", "energy": "усиление", "chakra": "коронная"},
        "en": {"name": "Clear quartz", "properties": "amplifier, clarity", "energy": "amplification", "chakra": "crown"},
        "es": {"name": "Cuarzo transparente", "properties": "amplificador, claridad", "energy": "amplificación", "chakra": "corona"},
        "pt": {"name": "Quartzo transparente", "properties": "amplificador, clareza", "energy": "amplificação", "chakra": "coroa"},
    },
    "black_tourmaline": {
        "ru": {"name": "Чёрный турмалин", "properties": "заземление, защита", "energy": "заземление", "chakra": "корневая"},
        "en": {"name": "Black tourmaline", "properties": "grounding, protection", "energy": "grounding", "chakra": "root"},
        "es": {"name": "Turmalina negra", "properties": "anclaje, protección", "energy": "anclaje", "chakra": "raíz"},
        "pt": {"name": "Turmalina negra", "properties": "aterramento, proteção", "energy": "aterramento", "chakra": "raiz"},
    },
    "carnelian": {
        "ru": {"name": "Карнеол", "properties": "действие, смелость, огонь", "energy": "действие", "chakra": "сакральная"},
        "en": {"name": "Carnelian", "properties": "action, courage, fire", "energy": "action", "chakra": "sacral"},
        "es": {"name": "Cornalina", "properties": "acción, valentía, fuego", "energy": "acción", "chakra": "sacral"},
        "pt": {"name": "Cornalina", "properties": "ação, coragem, fogo", "energy": "ação", "chakra": "sacral"},
    },
    "aventurine": {
        "ru": {"name": "Авентюрин", "properties": "удача, сердце, рост", "energy": "гармония", "chakra": "сердечная"},
        "en": {"name": "Aventurine", "properties": "luck, heart, growth", "energy": "harmony", "chakra": "heart"},
        "es": {"name": "Aventurina", "properties": "suerte, corazón, crecimiento", "energy": "armonía", "chakra": "corazón"},
        "pt": {"name": "Aventurina", "properties": "sorte, coração, crescimento", "energy": "harmonia", "chakra": "coração"},
    },
    "hematite": {
        "ru": {"name": "Гематит", "properties": "заземление, структура", "energy": "заземление", "chakra": "корневая"},
        "en": {"name": "Hematite", "properties": "grounding, structure", "energy": "grounding", "chakra": "root"},
        "es": {"name": "Hematita", "properties": "anclaje, estructura", "energy": "anclaje", "chakra": "raíz"},
        "pt": {"name": "Hematita", "properties": "aterramento, estrutura", "energy": "aterramento", "chakra": "raiz"},
    },
    "jade": {
        "ru": {"name": "Нефрит", "properties": "баланс, мягкая сила", "energy": "баланс", "chakra": "сердечная"},
        "en": {"name": "Jade", "properties": "balance, gentle strength", "energy": "balance", "chakra": "heart"},
        "es": {"name": "Jade", "properties": "equilibrio, fuerza suave", "energy": "equilibrio", "chakra": "corazón"},
        "pt": {"name": "Jade", "properties": "equilíbrio, força suave", "energy": "equilíbrio", "chakra": "coração"},
    },
}


def _pick_locale(table: dict[str, dict[str, str]], lang: str) -> dict[str, str]:
    lang = normalize_language(lang)
    return table.get(lang) or table.get("en") or table.get("ru") or {}


def localize_rune(rune: Rune, lang: str) -> Rune:
    loc = _pick_locale(_RUNE_LOCALES.get(rune.slug, {}), lang)
    if not loc:
        return rune
    return Rune(
        rune.slug,
        loc.get("name", rune.name),
        loc.get("meaning", rune.meaning),
        loc.get("energy", rune.energy),
        loc.get("element", rune.element),
    )


def localize_stone(stone: Stone, lang: str) -> Stone:
    loc = _pick_locale(_STONE_LOCALES.get(stone.slug, {}), lang)
    if not loc:
        return stone
    return Stone(
        stone.slug,
        loc.get("name", stone.name),
        loc.get("properties", stone.properties),
        loc.get("energy", stone.energy),
        loc.get("chakra", stone.chakra),
        stone.pairs_with,
    )


def runes_catalog_text(lang: str) -> str:
    from app.services.energy.catalog import RUNES

    lang = normalize_language(lang)
    lines = []
    for rune in RUNES:
        loc = localize_rune(rune, lang)
        lines.append(f"{loc.slug}: {loc.name} — {loc.meaning}")
    return "\n".join(lines)


def stones_catalog_text(lang: str) -> str:
    from app.services.energy.catalog import STONES

    lang = normalize_language(lang)
    lines = []
    for stone in STONES:
        loc = localize_stone(stone, lang)
        pairs = ", ".join(stone.pairs_with)
        lines.append(
            f"{loc.slug}: {loc.name} — {loc.properties}; "
            f"energy={loc.energy}; chakra={loc.chakra}; pairs_with={pairs}"
        )
    return "\n".join(lines)
