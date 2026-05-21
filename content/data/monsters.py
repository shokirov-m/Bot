"""
ВСЕ МОНСТРЫ БАШНИ — редактируй ``game/data/monsters_catalog.json``.

Один файл JSON:
  • ``pools`` — порядок монстров в пуле по зонам (важен для UI).
  • ``monsters`` — для каждого ключа: поля каталога боя + ``zone``, ``display_name``, ``emoji``, ``blurb``.

Код ниже только загружает данные и отдаёт ``ALL_MONSTERS`` / реестр каталога.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent
_CATALOG_PATH = _DATA_DIR / "monsters_catalog.json"


def _merge_zone_packs(raw: dict[str, Any]) -> dict[str, Any]:
    """Пулы и монстры из content/data/packs/zones/*/monsters.json."""
    try:
        from game.data.packs import pack_monsters_merge

        pools_delta, monsters_delta = pack_monsters_merge()
    except Exception:
        return raw
    pools = dict(raw.get("pools") or {})
    monsters = dict(raw.get("monsters") or {})
    for zk, keys in pools_delta.items():
        if keys:
            pools[zk] = list(keys)
    for mid, row in monsters_delta.items():
        monsters[mid] = row
    return {"pools": pools, "monsters": monsters}


def _load_catalog() -> dict[str, Any]:
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return _merge_zone_packs(raw)


_RAW: dict[str, Any] = _load_catalog()

ZONE_POOL_KEYS: dict[str, tuple[str, ...]] = {
    zone: tuple(keys) for zone, keys in _RAW["pools"].items()
}

KEY_TO_ZONE: dict[str, str] = {
    mid: str(entry["zone"]) for mid, entry in _RAW["monsters"].items()
}

MONSTER_TEMPLATE_META: dict[str, dict[str, str]] = {
    mid: {
        "display_name": str(entry.get("display_name", "")),
        "emoji": str(entry.get("emoji", "")),
        "element": str(entry.get("element", "earth")),
        "blurb": str(entry.get("blurb", "")),
    }
    for mid, entry in _RAW["monsters"].items()
}


def _entry_to_row(mid: str, entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    out["key"] = mid
    dn = out.get("display_name")
    if dn:
        out["template_display_name"] = str(dn)
    return out


ALL_MONSTERS: dict[str, dict[str, Any]] = {
    mid: _entry_to_row(mid, dict(entry)) for mid, entry in _RAW["monsters"].items()
}


def _subset(keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    return {k: ALL_MONSTERS[k] for k in keys if k in ALL_MONSTERS}


FOREST_MONSTERS = _subset(ZONE_POOL_KEYS["forest_beginnings"])
SWAMP_MONSTERS = _subset(ZONE_POOL_KEYS["rotten_swamps"])
CAVES_MONSTERS = _subset(ZONE_POOL_KEYS["shadow_caves"])
ICY_PEAKS_MONSTERS = _subset(ZONE_POOL_KEYS["icy_peaks"])
DESERT_MONSTERS = _subset(ZONE_POOL_KEYS["desert_oblivion"])
VOLCANIC_MONSTERS = _subset(ZONE_POOL_KEYS["volcanic_ruins"])
BLOOD_SPIRE_MONSTERS = _subset(ZONE_POOL_KEYS.get("blood_spire", ()))
CHAOS_ABYSS_MONSTERS = _subset(ZONE_POOL_KEYS["chaos_abyss"])
ETERNITY_HALL_MONSTERS = _subset(ZONE_POOL_KEYS["eternity_hall"])
FINAL_BOSS = _subset(ZONE_POOL_KEYS.get("tower_warden", ()))


def get_monster(key: str) -> dict[str, Any] | None:
    return ALL_MONSTERS.get(key)


def monsters_for_zone(zone_key: str) -> list[dict[str, Any]]:
    return [m for m in ALL_MONSTERS.values() if m.get("zone") == zone_key]


_CATALOG_DROP = frozenset(
    {"key", "blurb", "emoji", "template_display_name", "zone", "display_name"},
)


def get_catalog_definitions() -> dict[str, dict[str, Any]]:
    """Поля карточки для боя/БД — без служебных полей редактора."""
    return {
        k: {kk: vv for kk, vv in v.items() if kk not in _CATALOG_DROP}
        for k, v in ALL_MONSTERS.items()
    }



def reload_monsters_catalog() -> None:
    """Перечитать monsters_catalog.json (после правки файла без перезапуска бота — только для отладки)."""
    global _RAW, ZONE_POOL_KEYS, KEY_TO_ZONE, MONSTER_TEMPLATE_META, ALL_MONSTERS
    global FOREST_MONSTERS, SWAMP_MONSTERS, CAVES_MONSTERS, ICY_PEAKS_MONSTERS
    global DESERT_MONSTERS, VOLCANIC_MONSTERS, BLOOD_SPIRE_MONSTERS, CHAOS_ABYSS_MONSTERS
    global ETERNITY_HALL_MONSTERS, FINAL_BOSS
    _RAW = _load_catalog()
    ZONE_POOL_KEYS = {zone: tuple(keys) for zone, keys in _RAW["pools"].items()}
    KEY_TO_ZONE = {mid: str(entry["zone"]) for mid, entry in _RAW["monsters"].items()}
    MONSTER_TEMPLATE_META = {
        mid: {
            "display_name": str(entry.get("display_name", "")),
            "emoji": str(entry.get("emoji", "")),
            "element": str(entry.get("element", "earth")),
            "blurb": str(entry.get("blurb", "")),
        }
        for mid, entry in _RAW["monsters"].items()
    }
    ALL_MONSTERS = {mid: _entry_to_row(mid, dict(entry)) for mid, entry in _RAW["monsters"].items()}
    FOREST_MONSTERS = _subset(ZONE_POOL_KEYS["forest_beginnings"])
    SWAMP_MONSTERS = _subset(ZONE_POOL_KEYS["rotten_swamps"])
    CAVES_MONSTERS = _subset(ZONE_POOL_KEYS["shadow_caves"])
    ICY_PEAKS_MONSTERS = _subset(ZONE_POOL_KEYS["icy_peaks"])
    DESERT_MONSTERS = _subset(ZONE_POOL_KEYS["desert_oblivion"])
    VOLCANIC_MONSTERS = _subset(ZONE_POOL_KEYS["volcanic_ruins"])
    BLOOD_SPIRE_MONSTERS = _subset(ZONE_POOL_KEYS.get("blood_spire", ()))
    CHAOS_ABYSS_MONSTERS = _subset(ZONE_POOL_KEYS["chaos_abyss"])
    ETERNITY_HALL_MONSTERS = _subset(ZONE_POOL_KEYS["eternity_hall"])
    FINAL_BOSS = _subset(ZONE_POOL_KEYS.get("tower_warden", ()))
    try:
        from game.enemies.catalog.registry import mr
        mr.reload_definitions()
    except Exception:
        pass

__all__ = [
    "ALL_MONSTERS",
    "CHAOS_ABYSS_MONSTERS",
    "CAVES_MONSTERS",
    "DESERT_MONSTERS",
    "ETERNITY_HALL_MONSTERS",
    "FINAL_BOSS",
    "FOREST_MONSTERS",
    "ICY_PEAKS_MONSTERS",
    "KEY_TO_ZONE",
    "MONSTER_TEMPLATE_META",
    "BLOOD_SPIRE_MONSTERS",
    "SWAMP_MONSTERS",
    "VOLCANIC_MONSTERS",
    "ZONE_POOL_KEYS",
    "get_catalog_definitions",
    "get_monster",
    "monsters_for_zone",
    "reload_monsters_catalog",
]
