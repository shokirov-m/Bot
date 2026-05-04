"""
Временные зелья мастерской: бонус к стату на N побед (без боя — списывается в награде).
meta_progress['workshop_oil_v1'] = { "stat": "str", "value": 10, "battles": 5 }
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.items.stat_bonuses import STAT_KEYS, empty_stat_bonus_map

META_OIL = "workshop_oil_v1"
USE_TAG_OIL = "workshop_battle_oil"


def temporary_stat_bonus(character: Character) -> dict[str, int]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_OIL)
    if not isinstance(raw, dict):
        return empty_stat_bonus_map()
    if int(raw.get("battles", 0) or 0) <= 0:
        return empty_stat_bonus_map()
    stat = str(raw.get("stat") or "str").lower()
    if stat not in STAT_KEYS:
        stat = "str"
    val = max(0, int(raw.get("value", 0)))
    out = empty_stat_bonus_map()
    out[stat] = val
    return out


def apply_oil_from_item(character: Character, item_data: dict[str, Any]) -> tuple[bool, str]:
    """Активировать эффект расходника; предмет должен быть удалён вызывающим кодом."""
    stat = str(item_data.get("oil_stat") or "str").lower()
    if stat not in STAT_KEYS:
        stat = "str"
    val = max(1, int(item_data.get("oil_value", 10)))
    battles = max(1, int(item_data.get("oil_battles", 5)))
    mp = dict(character.meta_progress or {})
    mp[META_OIL] = {"stat": stat, "value": val, "battles": battles}
    character.meta_progress = mp
    flag_modified(character, "meta_progress")
    names = {"str": "СИЛ", "dex": "ЛОВ", "int": "ИНТ", "vit": "ВЫН", "luck": "УДА"}
    return True, f"Действует +{val} к {names.get(stat, stat)} на {battles} побед."


def on_battle_won(character: Character) -> None:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_OIL)
    if not isinstance(raw, dict):
        return
    left = int(raw.get("battles", 0) or 0)
    if left <= 0:
        if META_OIL in mp:
            del mp[META_OIL]
            character.meta_progress = mp
            flag_modified(character, "meta_progress")
        return
    left -= 1
    if left <= 0:
        mp.pop(META_OIL, None)
    else:
        raw["battles"] = left
        mp[META_OIL] = raw
    character.meta_progress = mp
    flag_modified(character, "meta_progress")
