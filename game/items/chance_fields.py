"""
Шансовые модификаторы экипировки (доли 0..1 или проценты в данных предмета).
Общий разбор для агрегирования в профиле и для карточки одного предмета.
"""

from __future__ import annotations

from typing import Any

CHANCE_FIELDS: tuple[str, ...] = (
    "crit_bonus",
    "dodge_bonus",
    "stun_chance",
    "bleed_chance",
    "poison_chance",
    "burn_chance",
    "freeze_chance",
    "lifesteal_chance",
    "block_chance",
    "miss_reduction",
)


def coerce_equipment_chance(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return x / 100.0 if x > 1.0 else x


def empty_chance_map() -> dict[str, float]:
    return {k: 0.0 for k in CHANCE_FIELDS}


def chance_map_from_item_data(data: dict[str, Any] | None) -> dict[str, float]:
    """Все шансы из одного item_data (корень и stat_bonus)."""
    out = empty_chance_map()
    if not data:
        return out
    d = dict(data)
    for k in CHANCE_FIELDS:
        if k in d:
            out[k] += coerce_equipment_chance(d.get(k))
    sub = d.get("stat_bonus")
    if isinstance(sub, dict):
        for k in CHANCE_FIELDS:
            if k in sub:
                out[k] += coerce_equipment_chance(sub.get(k))
    return out


def merge_chance_maps(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {k: float(a.get(k, 0.0) or 0.0) + float(b.get(k, 0.0) or 0.0) for k in CHANCE_FIELDS}


def format_chance_map_html(bonuses: dict[str, float]) -> str:
    """HTML одной строкой; пустая строка если всё нули."""
    labels = {
        "crit_bonus": "💥 Крит",
        "dodge_bonus": "💨 Уклонение",
        "stun_chance": "⭐ Оглушение",
        "bleed_chance": "🩸 Кровотечение",
        "poison_chance": "☠️ Яд",
        "burn_chance": "🔥 Поджог",
        "freeze_chance": "❄️ Заморозка",
        "lifesteal_chance": "🩻 Вампиризм",
        "block_chance": "🛡️ Блок",
        "miss_reduction": "🎯 –Промах",
    }
    parts: list[str] = []
    for k in CHANCE_FIELDS:
        v = float(bonuses.get(k, 0.0) or 0.0)
        if v > 0.0:
            parts.append(f"{labels[k]}: +{v * 100:.1f}%")
    if not parts:
        return ""
    return " · ".join(parts)
