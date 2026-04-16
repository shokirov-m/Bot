"""
Руны: элементы, ранги, слоты по редкости оружия, синергии, бонус к урону/эффектам в бою.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Sequence

ELEMENTS: dict[str, dict[str, str]] = {
    "fire": {"name": "Пламени", "emoji": "🔥", "status_effect": "burn"},
    "ice": {"name": "Льда", "emoji": "❄️", "status_effect": "freeze"},
    "lightning": {"name": "Молнии", "emoji": "⚡", "status_effect": "paralyze"},
    "dark": {"name": "Тьмы", "emoji": "🌑", "status_effect": "fear"},
    "light": {"name": "Света", "emoji": "✨", "status_effect": "blind"},
    "earth": {"name": "Земли", "emoji": "🌿", "status_effect": "slow"},
}

# ранг: бонус к «элементальному» % урона, шанс статуса, вес дропа
RUNE_RANK_STATS: dict[int, dict[str, Any]] = {
    1: {"damage_bonus_percent": 8, "status_chance": 0.10, "drop_weight": 60},
    2: {"damage_bonus_percent": 15, "status_chance": 0.18, "drop_weight": 25},
    3: {"damage_bonus_percent": 25, "status_chance": 0.28, "drop_weight": 10},
    4: {"damage_bonus_percent": 40, "status_chance": 0.38, "drop_weight": 4},
    5: {"damage_bonus_percent": 60, "status_chance": 0.50, "drop_weight": 1},
}

_ROMAN = ("0", "I", "II", "III", "IV", "V")

# Ключи — frozenset уникальных стихий; «мастерство» обрабатывается отдельно по счётчику
SYNERGIES: dict[frozenset[str], dict[str, Any]] = {
    frozenset({"fire", "lightning"}): {
        "name": "Плазма",
        "bonus_percent": 20,
        "description": "+20% к суммарному элементальному бонусу",
    },
    frozenset({"ice", "earth"}): {
        "name": "Вечная мерзлота",
        "bonus_percent": 15,
        "armor_mult": 1.10,
        "description": "+15% к бонусу и +10% к защите от экипировки",
    },
    frozenset({"dark", "light"}): {
        "name": "Сумерки",
        "bonus_percent": 0,
        "crit_damage_bonus_percent": 30,
        "description": "+30% к урону при крите",
    },
}

MASTERY_SAME_ELEMENT_BONUS = 50  # при 2+ рунах одной стихии


@dataclass(frozen=True, slots=True)
class RuneData:
    element: str
    rank: int  # 1–5

    def __post_init__(self) -> None:
        if self.element not in ELEMENTS:
            raise ValueError(f"Неизвестная стихия: {self.element}")
        if not 1 <= self.rank <= 5:
            raise ValueError("Ранг руны 1–5")

    @property
    def damage_bonus_percent(self) -> int:
        return int(RUNE_RANK_STATS[self.rank]["damage_bonus_percent"])

    @property
    def status_chance(self) -> float:
        return float(RUNE_RANK_STATS[self.rank]["status_chance"])

    @property
    def display_name(self) -> str:
        meta = ELEMENTS[self.element]
        rom = _ROMAN[self.rank] if 0 <= self.rank < len(_ROMAN) else str(self.rank)
        return f"{meta['emoji']} Руна {meta['name']} {rom}"

    def as_dict(self) -> dict[str, Any]:
        return {"element": self.element, "rank": self.rank}

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> RuneData:
        return RuneData(
            element=str(raw.get("element", "earth")),
            rank=int(raw.get("rank", 1)),
        )


def max_rune_slots(rarity: str) -> int:
    """Число гнёзд под руны по редкости оружия."""
    m = {
        "common": 0,
        "uncommon": 1,
        "rare": 1,
        "epic": 2,
        "legendary": 3,
    }
    return int(m.get((rarity or "common").lower(), 0))


def get_synergy(runes: list[RuneData]) -> dict[str, Any] | None:
    """Первая подходящая синергия по набору рун (мастерство — отдельно)."""
    els = {r.element for r in runes}
    for key, data in SYNERGIES.items():
        if key <= els:
            return dict(data)
    return None


def _same_element_mastery_bonus(runes: list[RuneData]) -> int:
    counts: dict[str, int] = {}
    for r in runes:
        counts[r.element] = counts.get(r.element, 0) + 1
    if any(c >= 2 for c in counts.values()):
        return MASTERY_SAME_ELEMENT_BONUS
    return 0


def calculate_elemental_bonus(
    weapon_runes: Sequence[RuneData],
    monster_element: str,
    character_element: str | None,
) -> int:
    """
    Итоговый elemental_bonus_percent для formulas.physical_damage.
    Сумма бонусов рун; слабое место врага ×1.5 на руну; синергии; мастерство; +5% если стихия героя совпадает с любой руной.
    """
    mon = (monster_element or "earth").lower()
    total = 0
    for r in weapon_runes:
        b = r.damage_bonus_percent
        if r.element == mon:
            b = int(b * 1.5)
        total += b
    syn = get_synergy(list(weapon_runes))
    if syn:
        total += int(syn.get("bonus_percent", 0))
    total += _same_element_mastery_bonus(list(weapon_runes))
    if character_element:
        ce = character_element.lower()
        if any(r.element == ce for r in weapon_runes):
            total += 5
    return min(250, max(0, total))


def rune_combat_extras(
    weapon_runes: Sequence[RuneData],
) -> dict[str, Any]:
    """
    Доп. модификаторы боя: множитель брони от экипировки, бонус % к крит-урону.
    """
    crit_extra = 0
    armor_mult = 1.0
    synergy_name: str | None = None
    syn = get_synergy(list(weapon_runes))
    if syn:
        synergy_name = str(syn.get("name", ""))
        crit_extra = int(syn.get("crit_damage_bonus_percent", 0))
        armor_mult = float(syn.get("armor_mult", 1.0))
    return {
        "crit_damage_bonus_percent": crit_extra,
        "armor_mult": armor_mult,
        "synergy_name": synergy_name,
    }


def parse_weapon_runes(item_data: dict[str, Any] | None) -> list[RuneData]:
    """Считать вставленные руны с надетого оружия (rune_sockets)."""
    if not item_data:
        return []
    raw_list = item_data.get("rune_sockets")
    if not isinstance(raw_list, list):
        return []
    out: list[RuneData] = []
    for cell in raw_list:
        if not isinstance(cell, dict):
            continue
        try:
            out.append(RuneData.from_dict(cell))
        except (ValueError, TypeError, KeyError):
            continue
    return out


def ensure_rune_socket_list(item_data: dict[str, Any]) -> list[Any | None]:
    """Инициализировать rune_sockets под редкость оружия; вернуть изменяемый список в item_data."""
    rarity = str(item_data.get("rarity", "common"))
    n = max_rune_slots(rarity)
    rs = item_data.get("rune_sockets")
    if not isinstance(rs, list):
        rs = [None] * n
    else:
        rs = list(rs)
        while len(rs) < n:
            rs.append(None)
        rs = rs[:n]
    item_data["rune_sockets"] = rs
    return rs


def rune_item_payload(rune: RuneData) -> dict[str, Any]:
    """Предмет в сумку (kind=rune)."""
    return {
        "name": rune.display_name,
        "kind": "rune",
        "rarity": "uncommon" if rune.rank >= 3 else "common",
        "summary": f"Вставь в оружие в кузнице. {ELEMENTS[rune.element]['emoji']} ранг {rune.rank}.",
        "rune": rune.as_dict(),
    }


def extract_rune_from_item(item_data: dict[str, Any] | None) -> RuneData | None:
    if not item_data or item_data.get("kind") != "rune":
        return None
    raw = item_data.get("rune")
    if not isinstance(raw, dict):
        return None
    try:
        return RuneData.from_dict(raw)
    except (ValueError, TypeError, KeyError):
        return None


def roll_rune_drop(floor: int, is_boss: bool) -> RuneData | None:
    """Случайная руна с весами ранга по этажу; is_boss поднимает верхнюю границу ранга."""
    if random.random() > 0.08:
        return None
    f = max(1, min(100, int(floor)))
    if f <= 20:
        lo, hi = 1, 2
    elif f <= 60:
        lo, hi = 1, 3
    elif f <= 90:
        lo, hi = 2, 4
    else:
        lo, hi = 3, 5
    if is_boss:
        hi = min(5, hi + 1)
    ranks = list(range(lo, hi + 1))
    weights = [int(RUNE_RANK_STATS[r]["drop_weight"]) for r in ranks]
    rank = random.choices(ranks, weights=weights, k=1)[0]
    element = random.choice(list(ELEMENTS.keys()))
    return RuneData(element=element, rank=rank)
