"""
Бонусы к СИЛ/ЛОВ/ИНТ/ВЫН/УДА в данных предмета (экипировка).
"""

from __future__ import annotations

from typing import Any

from game.items import enchant as enchant_rules
from game.items.rarity_scaling import extra_stat_points_for_rarity_on_item

STAT_KEYS: tuple[str, ...] = ("str", "dex", "int", "vit", "luck")

_ITEM_ALIASES: dict[str, str] = {
    "strength": "str",
    "dexterity": "dex",
    "intelligence": "int",
    "vitality": "vit",
}


def empty_stat_bonus_map() -> dict[str, int]:
    return {k: 0 for k in STAT_KEYS}


def _enchant_flat_stat_bonus(out: dict[str, int], raw: dict[str, Any]) -> None:
    """Заточка даёт бонус к тем статам, что уже есть на предмете (и немного ВЫН чистой броне)."""
    e = enchant_rules.current_enchant_level(raw)
    if e <= 0:
        return
    kind = str(raw.get("kind") or "").lower()
    if kind in ("consumable", "rune"):
        return
    atk = int(raw.get("attack", raw.get("atk", 0)) or 0)
    defe = int(raw.get("defense", raw.get("armor", 0)) or 0)
    has_stat = any(out[k] > 0 for k in STAT_KEYS)
    if atk > 0:
        per = max(1, (e + 2) // 3)
        if has_stat:
            for k in STAT_KEYS:
                if out[k] > 0:
                    out[k] += per
        return
    per = max(1, (e + 1) // 2)
    if has_stat:
        for k in STAT_KEYS:
            if out[k] > 0:
                out[k] += per
    elif defe > 0 and kind in ("armor", "pants", "helmet", "gloves", "ring", "amulet"):
        out["vit"] += max(1, per)


def stat_bonuses_from_item_data(data: dict[str, Any] | None) -> dict[str, int]:
    """Суммарные бонусы одного предмета."""
    out = empty_stat_bonus_map()
    if not data:
        return out
    for k in STAT_KEYS:
        v = data.get(k)
        if v is not None:
            out[k] += int(v)
    for alias, k in _ITEM_ALIASES.items():
        v = data.get(alias)
        if v is not None:
            out[k] += int(v)
    nested = data.get("stat_bonus")
    if isinstance(nested, dict):
        for k in STAT_KEYS:
            v = nested.get(k)
            if v is not None:
                out[k] += int(v)
    extra = extra_stat_points_for_rarity_on_item(data)
    if extra and any(out[k] for k in STAT_KEYS):
        for k in STAT_KEYS:
            if out[k] > 0:
                out[k] += extra
    _enchant_flat_stat_bonus(out, data)
    return out


def format_item_stat_bonus_line(data: dict[str, Any] | None) -> str | None:
    """Одна строка для карточки предмета или None."""
    b = stat_bonuses_from_item_data(data)
    parts: list[str] = []
    labels = ("Сила", "Ловкость", "Интеллект", "Выносливость", "Удача")
    keys = STAT_KEYS
    for lab, k in zip(labels, keys, strict=True):
        if b[k]:
            sign = "+" if b[k] > 0 else ""
            parts.append(f"{sign}{b[k]} {lab}")
    if not parts:
        return None
    return "📈 " + " · ".join(parts)
