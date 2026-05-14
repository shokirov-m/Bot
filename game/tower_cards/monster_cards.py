"""
Карточки «башенной» колоды: монстры с этажей 1–20 (пул из build_spawns_for_floor).

Имя и эмодзи — из MONSTER_TEMPLATE_META; ATK/DEF — из каталога монстров с масштабом по этажу выпадения.
Стихия для дуэли нормализуется к fire / water / earth (см. duel_element).
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from game.data.monsters import MONSTER_TEMPLATE_META
from game.floors import floor_data, monster_catalog
from game.floors.monsters import FloorMonsterSpawn, build_spawns_for_floor
from utils.image_assets import monster_image_for_template

RARITY_STARS_RU: dict[str, str] = {
    "common": "⭐",
    "uncommon": "⭐⭐",
    "rare": "⭐⭐⭐",
    "epic": "⭐⭐⭐⭐",
    "legendary": "⭐⭐⭐⭐⭐",
    "mythic": "⭐⭐⭐⭐⭐⭐",
}

RARITY_ORDER: tuple[str, ...] = ("mythic", "legendary", "epic", "rare", "uncommon", "common")


def _build_pool_keys() -> frozenset[str]:
    keys: set[str] = set()
    for fl in range(1, 21):
        for s in build_spawns_for_floor(fl):
            keys.add(s.template.key)
    return frozenset(keys)


TW_POOL_KEYS: frozenset[str] = _build_pool_keys()
TW_POOL_TOTAL: int = len(TW_POOL_KEYS)


def base_template_key(template_key: str) -> str:
    k = (template_key or "").strip()
    if k.startswith("elite_"):
        return k[len("elite_") :]
    return k


def meta_row(template_key: str) -> dict[str, str] | None:
    bk = base_template_key(template_key)
    m = MONSTER_TEMPLATE_META.get(template_key) or MONSTER_TEMPLATE_META.get(bk)
    return m


def display_name(template_key: str) -> str:
    m = meta_row(template_key)
    if m:
        return str(m.get("display_name", template_key)).strip() or template_key
    return template_key


def emoji_for(template_key: str) -> str:
    m = meta_row(template_key)
    if m:
        return str(m.get("emoji", "👾"))
    return "👾"


def raw_element(template_key: str) -> str:
    m = meta_row(template_key)
    if m:
        return str(m.get("element", "earth")).strip().lower()
    return "earth"


def duel_element(raw: str) -> str:
    """Камень-ножницы-бумага в дуэли только fire / water / earth."""
    e = (raw or "earth").strip().lower()
    if e == "fire":
        return "fire"
    if e in ("water", "ice"):
        return "water"
    return "earth"


def tier_for_spawn(spawn: FloorMonsterSpawn, floor: int) -> str:
    if spawn.is_major_boss:
        return "mythic"
    if spawn.is_mini_boss:
        return "legendary"
    if spawn.is_elite:
        return "rare"
    if floor <= 7:
        return "common"
    if floor <= 14:
        return "uncommon"
    return "epic"


def pick_random_spawn_f1_20() -> tuple[int, FloorMonsterSpawn]:
    fl = random.randint(1, 20)
    spawns = build_spawns_for_floor(fl)
    return fl, random.choice(spawns)


def scaled_atk_def(template_key: str, floor: int) -> tuple[int, int]:
    cat = monster_catalog.get_definition(template_key)
    if cat is None:
        return 8, 3
    r = monster_catalog.floor_ratio(cat, int(floor))
    atk = max(1, int(float(cat.get("atk", 10)) * r))
    deff = max(0, int(float(cat.get("def", 2)) * r))
    return atk, deff


def portrait_path(template_key: str, floor: int) -> Path | None:
    zone = floor_data.get_zone_for_floor(int(floor))
    return monster_image_for_template(template_key, zone_key=zone.key)


def filtered_collection(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Только карты из пула 1–20 этажа (старые sticker id отбрасываем)."""
    return {k: dict(v) for k, v in raw.items() if k in TW_POOL_KEYS and isinstance(v, dict)}
