"""Хелперы квестов NPC из JSON-паков зон."""

from __future__ import annotations

from typing import Any

from game.data.packs import load_zone_pack

_PROF_MAP: dict[str, str] = {
    "alchemy": "alchemist",
    "smithing": "blacksmith",
    "jewelry": "jeweler",
    "herbalism": "alchemist",
    "hunting": "blacksmith",
}


def workshop_profession_key(pack_profession: str) -> str:
    return _PROF_MAP.get(str(pack_profession or "").lower().strip(), "blacksmith")


def material_label(zone_key: str, material_id: str) -> str:
    pack = load_zone_pack(zone_key)
    ent = (pack.get("materials") or {}).get("entries") or {}
    row = ent.get(material_id) if isinstance(ent, dict) else None
    if isinstance(row, dict):
        return str(row.get("name_ru") or material_id)
    return str(material_id)


def blueprint_label(zone_key: str, blueprint_id: str) -> str:
    pack = load_zone_pack(zone_key)
    ent = (pack.get("blueprints") or {}).get("entries") or {}
    row = ent.get(blueprint_id) if isinstance(ent, dict) else None
    if isinstance(row, dict):
        return str(row.get("name_ru") or blueprint_id)
    return str(blueprint_id)


def quests_for_npc_on_floor(npc: dict[str, Any], floor: int) -> list[dict[str, Any]]:
    """Квесты NPC, доступные на данном этаже."""
    fl = int(floor)
    out: list[dict[str, Any]] = []
    for q in npc.get("quests") or []:
        if not isinstance(q, dict):
            continue
        floors = q.get("floors")
        if isinstance(floors, list) and fl not in {int(x) for x in floors}:
            continue
        out.append(dict(q))
    return out
