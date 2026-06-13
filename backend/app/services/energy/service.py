from __future__ import annotations

import random
from dataclasses import dataclass

from app.services.energy.catalog import (
    BRACELET_ROLE_LABELS,
    INTENT_KEYWORDS,
    RUNES,
    STONES,
    Rune,
    Stone,
)
from app.services.energy.localize import localize_rune, localize_stone
from app.bot.i18n import normalize_language, t


@dataclass
class DrawnRune:
    rune: Rune
    reversed: bool


@dataclass
class BraceletSlot:
    position: str
    role_label: str
    stone: Stone | None
    rune: Rune | None
    note: str


class EnergyService:
    def draw_runes(self, count: int = 3) -> list[DrawnRune]:
        picked = random.sample(list(RUNES), k=min(count, len(RUNES)))
        return [DrawnRune(rune=r, reversed=random.random() < 0.25) for r in picked]

    def detect_intent(self, text: str) -> str:
        lower = (text or "").lower()
        scores: dict[str, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score:
                scores[intent] = score
        if not scores:
            return "balance"
        return max(scores, key=scores.get)

    def recommend_stones(self, query: str, *, limit: int = 3) -> list[Stone]:
        intent = self.detect_intent(query)
        intent_map: dict[str, list[str]] = {
            "love": ["rose_quartz", "moonstone", "aventurine"],
            "protection": ["obsidian", "black_tourmaline", "hematite"],
            "money": ["citrine", "tiger_eye", "clear_quartz"],
            "calm": ["amethyst", "moonstone", "labradorite"],
            "focus": ["tiger_eye", "citrine", "lapis"],
            "intuition": ["labradorite", "amethyst", "moonstone"],
            "balance": ["clear_quartz", "jade", "aventurine"],
        }
        slugs = intent_map.get(intent, intent_map["balance"])
        by_slug = {s.slug: s for s in STONES}
        return [by_slug[slug] for slug in slugs if slug in by_slug][:limit]

    def recommend_rune_for_intent(self, query: str) -> Rune:
        intent = self.detect_intent(query)
        intent_runes = {
            "love": "gebo",
            "protection": "algiz",
            "money": "fehu",
            "calm": "isa",
            "focus": "tiwaz",
            "intuition": "perthro",
            "balance": "mannaz",
        }
        slug = intent_runes.get(intent, "dagaz")
        return next(r for r in RUNES if r.slug == slug)

    def build_bracelet_from_layout(
        self,
        layout: dict[str, Stone],
        clasp_rune: Rune,
        lang: str = "ru",
    ) -> list[BraceletSlot]:
        roles = BRACELET_ROLE_LABELS.get(lang) or BRACELET_ROLE_LABELS["ru"]
        center = layout["center"]
        left = layout["left"]
        right = layout["right"]
        clasp_stone = layout["clasp_stone"]
        lang = normalize_language(lang)
        center_loc = localize_stone(center, lang)
        left_loc = localize_stone(left, lang)
        right_loc = localize_stone(right, lang)
        clasp_stone_loc = localize_stone(clasp_stone, lang)
        clasp_rune_loc = localize_rune(clasp_rune, lang)
        return [
            BraceletSlot("center", roles["center"], center_loc, None, center_loc.properties),
            BraceletSlot("left", roles["left"], left_loc, None, left_loc.properties),
            BraceletSlot("right", roles["right"], right_loc, None, right_loc.properties),
            BraceletSlot(
                "clasp",
                roles["clasp"],
                clasp_stone_loc,
                clasp_rune_loc,
                f"{clasp_stone_loc.name} + {clasp_rune_loc.name}",
            ),
        ]

    def build_bracelet(self, query: str, lang: str = "ru") -> list[BraceletSlot]:
        roles = BRACELET_ROLE_LABELS.get(lang) or BRACELET_ROLE_LABELS["ru"]
        stones = self.recommend_stones(query, limit=3)
        center = stones[0] if stones else STONES[0]
        left = stones[1] if len(stones) > 1 else STONES[7]
        right = stones[2] if len(stones) > 2 else STONES[6]
        clasp_rune = self.recommend_rune_for_intent(query)
        clasp_stone = next(s for s in STONES if s.slug == "hematite")
        lang = normalize_language(lang)
        center_loc = localize_stone(center, lang)
        left_loc = localize_stone(left, lang)
        right_loc = localize_stone(right, lang)
        clasp_stone_loc = localize_stone(clasp_stone, lang)
        clasp_rune_loc = localize_rune(clasp_rune, lang)

        return [
            BraceletSlot("center", roles["center"], center_loc, None, center_loc.properties),
            BraceletSlot("left", roles["left"], left_loc, None, left_loc.properties),
            BraceletSlot("right", roles["right"], right_loc, None, right_loc.properties),
            BraceletSlot(
                "clasp",
                roles["clasp"],
                clasp_stone_loc,
                clasp_rune_loc,
                f"{clasp_stone_loc.name} + {clasp_rune_loc.name}",
            ),
        ]

    def format_runes_text(self, drawn: list[DrawnRune], lang: str = "ru") -> str:
        lang = normalize_language(lang)
        lines = []
        for item in drawn:
            rune = localize_rune(item.rune, lang)
            suffix = t("rune_reversed_suffix", lang) if item.reversed else ""
            lines.append(f"• {rune.name}{suffix} — {rune.meaning}")
        return "\n".join(lines)

    def format_stones_text(self, stones: list[Stone], lang: str = "ru") -> str:
        lang = normalize_language(lang)
        localized = [localize_stone(s, lang) for s in stones]
        return "\n".join(f"• **{s.name}** — {s.properties} ({s.energy})" for s in localized)

    def format_bracelet_text(self, slots: list[BraceletSlot], lang: str = "ru") -> str:
        lines = []
        for slot in slots:
            parts = []
            if slot.stone:
                parts.append(slot.stone.name)
            if slot.rune:
                parts.append(slot.rune.name)
            content = " + ".join(parts) if parts else "—"
            lines.append(f"**{slot.role_label}**\n   {content}\n   _{slot.note}_")
        return "\n\n".join(lines)

    def rune_lines_for_ai(self, drawn: list[DrawnRune], lang: str = "ru") -> str:
        lang = normalize_language(lang)
        lines = []
        for item in drawn:
            rune = localize_rune(item.rune, lang)
            reversed_note = t("rune_reversed_suffix", lang) if item.reversed else ""
            lines.append(
                f"- {rune.name} ({rune.slug}){reversed_note}: "
                f"{rune.meaning}; energy={rune.energy}; element={rune.element}"
            )
        return "\n".join(lines)

    def stone_lines_for_ai(self, stones: list[Stone], lang: str = "ru") -> str:
        lang = normalize_language(lang)
        localized = [localize_stone(s, lang) for s in stones]
        return "\n".join(
            f"- {s.name} ({s.slug}): {s.properties}; energy={s.energy}; chakra={s.chakra}"
            for s in localized
        )

    def bracelet_lines_for_ai(self, slots: list[BraceletSlot], lang: str = "ru") -> str:
        return "\n".join(
            f"- {slot.position}: "
            f"stone={slot.stone.name if slot.stone else '—'}, "
            f"rune={slot.rune.name if slot.rune else '—'}, note={slot.note}"
            for slot in slots
        )
