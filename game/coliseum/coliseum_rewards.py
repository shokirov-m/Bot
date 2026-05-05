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
    # skill_meta — ключ навыка колизея для meta_progress["coliseum_skills"];
    # в payload: label_ru и ровно одно из str_flat/dex_flat/int_flat/vit_flat/luck_flat (плоский бонус).
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
    """Кольцо награды (fid кратен 5, не чемпион). Статы растут с глубиной колизея."""
    t = int(tier)
    defense = min(8 + t * 2, 72)
    hp_bonus = min(25 + t * 8, 520)
    luck = min(1 + t // 10, 8)
    rarity = "epic" if t >= 35 else "rare"
    return {
        "name": f"Печать Колизея ({t})",
        "kind": "ring",
        "defense": defense,
        "hp_bonus": hp_bonus,
        "luck": luck,
        "summary": f"Награда арены за победу над гладиатором №{t}.",
        "rarity": rarity,
    }


def _skill_meta_for_fid(fid: int) -> LootEntry:
    """Пассив «урок колизея»: постоянный бонус к одному стату (читается stat_bonus_service)."""
    sk = f"col_skill_{fid}"
    stats_cycle = ("vit", "str", "dex", "int", "luck")
    stat = stats_cycle[(fid - 1) % len(stats_cycle)]
    val = min(1 + (fid - 1) // 4, 14)
    return {
        "kind": "skill_meta",
        "skill_key": sk,
        "skill_payload": {"label_ru": f"Урок Колизея №{fid}", f"{stat}_flat": val},
    }


# Автогенерация дефолтного лута; ключевые ярусы переопределены ниже
def _default_loot_for_index(fid: int) -> LootEntry:
    if fid % 10 == 0:
        return {"kind": "title", "title_key": f"coliseum_champion_{fid}"}
    if fid % 5 == 0:
        return {"kind": "equipment", "item_data": _ring_coliseum(fid)}
    if fid % 3 == 0:
        # Обычные эликсиры 28–50 % HP в зависимости от номера боя
        pct = min(28 + (fid * fid) // 120, 50)
        return {"kind": "consumable", "item_data": _pot_hp_pct(f"Эликсир триумфа ({fid})", pct)}
    return _skill_meta_for_fid(fid)


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
        "kind": "ring",
        "defense": 42,
        "hp_bonus": 240,
        "vit": 6,
        "summary": "Трофей предфинального чемпиона Колизея.",
        "rarity": "epic",
    },
}


def loot_for_fighter_id(fid: int) -> LootEntry | None:
    return COLISEUM_LOOT.get(f"loot_{int(fid)}")
