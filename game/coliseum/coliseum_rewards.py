"""
Награды Колизея по ключам loot_id (loot_1 … loot_50).
Типы: equipment | consumable | title | skill_meta (пассив в meta_progress.coliseum_skills).
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class LootEntry(TypedDict, total=False):
    kind: Literal["equipment", "consumable", "title", "skill_meta"]
    # equipment / consumable — item_data для сумки
    item_data: dict[str, Any]
    # title — ключ TitleDef
    title_key: str
    # skill_meta — ключ навыка колизея для meta_progress["coliseum_skills"]
    skill_key: str
    skill_payload: dict[str, Any]


def _pot_hp_pct(name: str, pct: int) -> dict[str, Any]:
    return {
        "name": name,
        "use_tag": "heal_hp_pct",
        "use_value": pct,
        "kind": "consumable",
        "rarity": "common",
    }


def _ring_coliseum(tier: int) -> dict[str, Any]:
    return {
        "name": f"Печать Колизея ({tier})",
        "slot": "ring",
        "kind": "armor",
        "defense": min(2 + tier // 5, 40),
        "hp_bonus": min(15 + tier * 3, 220),
        "rarity": "rare" if tier < 25 else "epic",
    }


# Автогенерация дефолтного лута; ключевые ярусы переопределены ниже
def _default_loot_for_index(fid: int) -> LootEntry:
    if fid % 10 == 0:
        return {"kind": "title", "title_key": f"coliseum_champion_{fid}"}
    if fid % 5 == 0:
        return {"kind": "equipment", "item_data": _ring_coliseum(fid)}
    if fid % 3 == 0:
        return {"kind": "consumable", "item_data": _pot_hp_pct(f"Эликсир триумфа ({fid})", min(35 + fid, 55))}
    sk = f"col_skill_{fid}"
    return {
        "kind": "skill_meta",
        "skill_key": sk,
        "skill_payload": {"label_ru": f"Урок Колизея #{fid}", "xp_bonus_pct_floor": min(1 + fid // 10, 5)},
    }


COLISEUM_LOOT: dict[str, LootEntry] = {}

for i in range(1, 51):
    lid = f"loot_{i}"
    COLISEUM_LOOT[lid] = _default_loot_for_index(i)

# Переопределения финала и босс-трофеев
COLISEUM_LOOT["loot_50"] = {"kind": "title", "title_key": "coliseum_godslayer"}
COLISEUM_LOOT["loot_49"] = {
    "kind": "equipment",
    "item_data": {
        "name": "Часы Кроноса",
        "slot": "ring",
        "kind": "armor",
        "defense": 35,
        "hp_bonus": 180,
        "rarity": "epic",
    },
}


def loot_for_fighter_id(fid: int) -> LootEntry | None:
    return COLISEUM_LOOT.get(f"loot_{int(fid)}")
