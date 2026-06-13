from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rune:
    slug: str
    name: str
    meaning: str
    energy: str
    element: str


@dataclass(frozen=True)
class Stone:
    slug: str
    name: str
    properties: str
    energy: str
    chakra: str
    pairs_with: tuple[str, ...]


BRACELET_ROLE_LABELS = {
    "ru": {
        "center": "Центр — главный камень намерения",
        "left": "Слева — защита и баланс",
        "right": "Справа — притяжение и действие",
        "clasp": "У замка — заземление (руна или камень)",
    },
    "en": {
        "center": "Center — main intention stone",
        "left": "Left — protection and balance",
        "right": "Right — attraction and action",
        "clasp": "At clasp — grounding (rune or stone)",
    },
    "es": {
        "center": "Centro — piedra principal de intención",
        "left": "Izquierda — protección y equilibrio",
        "right": "Derecha — atracción y acción",
        "clasp": "En el cierre — anclaje (runa o piedra)",
    },
    "pt": {
        "center": "Centro — pedra principal da intenção",
        "left": "Esquerda — proteção e equilíbrio",
        "right": "Direita — atração e ação",
        "clasp": "No fecho — aterramento (runa ou pedra)",
    },
}

RUNES: tuple[Rune, ...] = (
    Rune("fehu", "Феху", "ресурс, начало, изобилие", "притяжение", "огонь"),
    Rune("uruz", "Уруз", "сила, здоровье, решимость", "опора", "земля"),
    Rune("thurisaz", "Турисаз", "защита, преграда, пробуждение", "защита", "огонь"),
    Rune("ansuz", "Ансуз", "слово, озарение, связь", "ясность", "воздух"),
    Rune("raidho", "Раидо", "путь, движение, ритм", "движение", "воздух"),
    Rune("kenaz", "Кеназ", "огонь творчества, свет внутри", "творчество", "огонь"),
    Rune("gebo", "Гебо", "дар, обмен, партнёрство", "гармония", "воздух"),
    Rune("wunjo", "Вунйо", "радость, целостность, успех", "радость", "земля"),
    Rune("hagalaz", "Хагалаз", "перелом, очищение, перемены", "трансформация", "лёд"),
    Rune("nauthiz", "Наутиз", "нужда, терпение, внутренняя сила", "стойкость", "огонь"),
    Rune("isa", "Иса", "пауза, зеркало, созревание", "покой", "лёд"),
    Rune("jera", "Йера", "урожай, цикл, терпеливый результат", "цикл", "земля"),
    Rune("eihwaz", "Эйваз", "устойчивость, переход, защита границ", "защита", "земля"),
    Rune("perthro", "Перт", "тайна, судьба, скрытое", "интуиция", "вода"),
    Rune("algiz", "Альгиз", "щит, связь с высшим, охрана", "защита", "воздух"),
    Rune("sowilo", "Сол", "солнце, победа, жизненная сила", "сила", "огонь"),
    Rune("tiwaz", "Тиваз", "справедливость, мужество, цель", "воля", "огонь"),
    Rune("berkano", "Беркано", "рост, забота, новое начало", "рост", "земля"),
    Rune("ehwaz", "Эхваз", "партнёрство, доверие, движение вместе", "союз", "земля"),
    Rune("mannaz", "Манназ", "человек, самопознание, сообщество", "осознанность", "воздух"),
    Rune("laguz", "Лагуз", "поток, интуиция, эмоции", "интуиция", "вода"),
    Rune("ingwaz", "Ингваз", "завершение, семя, внутренняя работа", "зрелость", "земля"),
    Rune("dagaz", "Дагаз", "прорыв, рассвет, ясность", "просветление", "огонь"),
    Rune("othala", "Отала", "род, корни, наследие", "корни", "земля"),
)

STONES: tuple[Stone, ...] = (
    Stone("amethyst", "Аметист", "спокойствие, интуиция, сон", "успокоение", "коронная", ("clear_quartz", "labradorite")),
    Stone("rose_quartz", "Розовый кварц", "любовь к себе, нежность", "любовь", "сердечная", ("amethyst", "moonstone")),
    Stone("obsidian", "Обсидиан", "защита, очищение, правда", "защита", "корневая", ("black_tourmaline", "hematite")),
    Stone("citrine", "Цитрин", "изобилие, радость, энергия солнца", "изобилие", "солнечное сплетение", ("clear_quartz", "tiger_eye")),
    Stone("lapis", "Лапис-лазури", "мудрость, правда, голос", "ясность", "горловая", ("clear_quartz",)),
    Stone("moonstone", "Лунный камень", "циклы, интуиция", "интуиция", "сакральная", ("rose_quartz", "labradorite")),
    Stone("tiger_eye", "Тигровый глаз", "уверенность, фокус", "сила", "солнечное сплетение", ("citrine", "carnelian")),
    Stone("labradorite", "Лабрадорит", "трансформация, защита ауры", "трансформация", "третий глаз", ("amethyst", "moonstone")),
    Stone("clear_quartz", "Горный хрусталь", "усилитель, ясность", "усиление", "коронная", ("amethyst", "citrine")),
    Stone("black_tourmaline", "Чёрный турмалин", "заземление, защита", "заземление", "корневая", ("obsidian", "hematite")),
    Stone("carnelian", "Карнеол", "действие, смелость, огонь", "действие", "сакральная", ("tiger_eye", "citrine")),
    Stone("aventurine", "Авентюрин", "удача, сердце, рост", "гармония", "сердечная", ("rose_quartz", "jade")),
    Stone("hematite", "Гематит", "заземление, структура", "заземление", "корневая", ("obsidian", "black_tourmaline")),
    Stone("jade", "Нефрит", "баланс, мягкая сила", "баланс", "сердечная", ("aventurine", "rose_quartz")),
)

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "love": ("любов", "отношен", "сердц", "партн", "love", "heart", "relationship", "amor", "corazón"),
    "protection": ("защит", "негатив", "страх", "protect", "protección", "proteção"),
    "money": ("деньг", "изобил", "доход", "money", "abundance", "dinero", "dinheiro"),
    "calm": ("спокой", "тревог", "стресс", "calm", "peace", "ansiedad", "ansiedade"),
    "focus": ("фокус", "цел", "карьер", "focus", "goal", "carrera", "carreira"),
    "intuition": ("интуиц", "духов", "медитац", "intuition", "spiritual", "intuición"),
}

RUNE_BY_SLUG = {rune.slug: rune for rune in RUNES}
STONE_BY_SLUG = {stone.slug: stone for stone in STONES}
