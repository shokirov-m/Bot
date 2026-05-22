"""Загрузка JSON-паков зон из content/data/packs/."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from game.core.paths import data_root

_PACKS_ROOT = data_root() / "packs"
_ZONES_DIR = _PACKS_ROOT / "zones"


def packs_root() -> Path:
    return _PACKS_ROOT


def zone_pack_dir(zone_key: str) -> Path:
    return _ZONES_DIR / zone_key


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


@lru_cache(maxsize=64)
def load_registry(*, reload: bool = False) -> dict[str, Any]:
    if reload:
        load_registry.cache_clear()
    return _read_json(_PACKS_ROOT / "registry.json")


@lru_cache(maxsize=32)
def load_zone_pack(zone_key: str, *, reload: bool = False) -> dict[str, Any]:
    if reload:
        load_zone_pack.cache_clear()
        trial_for_floor.cache_clear()
    base = zone_pack_dir(zone_key)
    if not base.is_dir():
        return {}
    trials_dir = base / "trials"
    trials: dict[str, Any] = {}
    if trials_dir.is_dir():
        for p in sorted(trials_dir.glob("floor_*.json")):
            stem = p.stem.replace("floor_", "")
            trials[stem] = _read_json(p)
    return {
        "zone_key": zone_key,
        "zone": _read_json(base / "zone.json"),
        "monsters": _read_json(base / "monsters.json"),
        "npcs": _read_json(base / "npcs.json"),
        "materials": _read_json(base / "materials.json"),
        "blueprints": _read_json(base / "blueprints.json"),
        "trials": trials,
    }


def list_zone_pack_keys() -> tuple[str, ...]:
    reg = load_registry()
    zones = reg.get("zones")
    if isinstance(zones, list) and zones:
        return tuple(str(z) for z in zones)
    if not _ZONES_DIR.is_dir():
        return ()
    return tuple(
        sorted(
            p.name
            for p in _ZONES_DIR.iterdir()
            if p.is_dir() and (p / "zone.json").is_file()
        )
    )


@lru_cache(maxsize=256)
def trial_for_floor(zone_key: str, floor_number: int) -> dict[str, Any]:
    pack = load_zone_pack(zone_key)
    trials = pack.get("trials") or {}
    key = str(int(floor_number))
    row = trials.get(key)
    return dict(row) if isinstance(row, dict) else {}


def zone_pack_hub_floor(zone_key: str) -> int | None:
    """Этаж «привала мастеров» зоны из zone.json (hub_floor)."""
    pack = load_zone_pack(zone_key)
    zone = pack.get("zone") or {}
    hub = zone.get("hub_floor")
    return int(hub) if isinstance(hub, int) else None


def npcs_hub_on_floor(zone_key: str, floor_number: int) -> list[dict[str, Any]]:
    """NPC с floors_hub — только на этаже-привале зоны (поручения, не бой)."""
    pack = load_zone_pack(zone_key)
    npcs_raw = pack.get("npcs") or {}
    entries = npcs_raw.get("entries")
    if not isinstance(entries, list):
        return []
    fl = int(floor_number)
    out: list[dict[str, Any]] = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        hub_floors = row.get("floors_hub")
        if isinstance(hub_floors, list) and fl in {int(x) for x in hub_floors}:
            out.append(dict(row))
    return out


def npcs_for_floor(zone_key: str, floor_number: int) -> list[dict[str, Any]]:
    pack = load_zone_pack(zone_key)
    npcs_raw = pack.get("npcs") or {}
    entries = npcs_raw.get("entries")
    if not isinstance(entries, list):
        return []
    fl = int(floor_number)
    out: list[dict[str, Any]] = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        hub_floors = row.get("floors_hub")
        if isinstance(hub_floors, list) and fl in {int(x) for x in hub_floors}:
            out.append(dict(row))
            continue
        floors = row.get("floors")
        if isinstance(floors, list):
            if fl not in {int(x) for x in floors}:
                continue
        else:
            fr = row.get("floor_from")
            to = row.get("floor_to")
            if isinstance(fr, int) and isinstance(to, int) and not (fr <= fl <= to):
                continue
        out.append(dict(row))
    return out


def pack_monsters_merge() -> tuple[dict[str, tuple[str, ...]], dict[str, dict[str, Any]]]:
    """
    (pools_delta, monsters_delta) для слияния с monsters_catalog.json.
    pools: zone_key -> tuple of monster ids
    monsters: id -> catalog row
    """
    pools: dict[str, tuple[str, ...]] = {}
    monsters: dict[str, dict[str, Any]] = {}
    for zk in list_zone_pack_keys():
        pack = load_zone_pack(zk)
        m = pack.get("monsters") or {}
        pool = m.get("pool")
        if isinstance(pool, list):
            pools[zk] = tuple(str(x) for x in pool)
        ent = m.get("entries")
        if isinstance(ent, dict):
            for mid, row in ent.items():
                if isinstance(row, dict):
                    monsters[str(mid)] = dict(row)
    return pools, monsters


def reload_all_packs() -> None:
    load_registry.cache_clear()
    load_zone_pack.cache_clear()
    trial_for_floor.cache_clear()
