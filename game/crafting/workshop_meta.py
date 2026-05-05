"""
Схема meta_progress['workshop_v1']: профессии, станки, очередь, чертежи, счётчики.
Миграция known_recipes (таверна) → known_blueprints один раз.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.crafting.recipes_data import PROF_BLACKSMITH, PROFESSION_KEYS, RECIPES
# Совпадает с services.tavern_service.META_KNOWN_RECIPES (не импортируем — циклы).
KNOWN_RECIPES_LEGACY_KEY = "known_recipes"

WORKSHOP_META_KEY = "workshop_v1"


def default_workshop_state() -> dict[str, Any]:
    return {
        "prof_levels": {k: 1 for k in PROFESSION_KEYS},
        "prof_xp": {k: 0 for k in PROFESSION_KEYS},
        "stations": {k: 1 for k in PROFESSION_KEYS},
        "known_blueprints": [],
        "active_crafts": [],
        "counters": {
            "crafts_done": 0,
            "orders_completed": 0,
            "gold_via_orders": 0,
            "first_craft_done": 0,
        },
        "talismans": {
            "top_blacksmith": False,
            "top_alchemist": False,
            "top_jeweler": False,
        },
        "migrated_known_recipes_v1": False,
        "free_blueprints_seeded_v1": False,
        "queue_bonus": 0,
        "status_profession": PROF_BLACKSMITH,
        "spec_profession": None,
        "spec_locked": False,
    }


def _fix_defaults(ws: dict[str, Any]) -> dict[str, Any]:
    d = default_workshop_state()
    for k, v in d.items():
        if k not in ws:
            ws[k] = v
    for pk in PROFESSION_KEYS:
        ws.setdefault("prof_levels", {})
        ws.setdefault("prof_xp", {})
        ws.setdefault("stations", {})
        ws["prof_levels"].setdefault(pk, 1)
        ws["prof_xp"].setdefault(pk, 0)
        ws["stations"].setdefault(pk, 1)
    if not isinstance(ws.get("known_blueprints"), list):
        ws["known_blueprints"] = []
    if not isinstance(ws.get("active_crafts"), list):
        ws["active_crafts"] = []
    if not isinstance(ws.get("counters"), dict):
        ws["counters"] = dict(default_workshop_state()["counters"])
    for ck, cv in default_workshop_state()["counters"].items():
        ws["counters"].setdefault(ck, cv)
    if not isinstance(ws.get("talismans"), dict):
        ws["talismans"] = dict(default_workshop_state()["talismans"])
    ws.setdefault("status_profession", PROF_BLACKSMITH)
    if ws.get("spec_profession") is not None:
        ws["spec_profession"] = str(ws["spec_profession"]).lower().strip()
    ws.setdefault("spec_locked", False)
    return ws


def get_workshop_state(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(WORKSHOP_META_KEY)
    if not isinstance(raw, dict):
        raw = {}
    ws = _fix_defaults(raw)
    changed = False
    if not ws.get("migrated_known_recipes_v1"):
        known_old = mp.get(KNOWN_RECIPES_LEGACY_KEY)
        if isinstance(known_old, list):
            kb = set(str(x) for x in ws["known_blueprints"])
            for rid in known_old:
                kb.add(str(rid))
            ws["known_blueprints"] = sorted(kb)
        ws["migrated_known_recipes_v1"] = True
        changed = True
    if not ws.get("free_blueprints_seeded_v1"):
        kb = set(str(x) for x in (ws.get("known_blueprints") or []))
        for r in RECIPES:
            if bool(r.get("requires_blueprint")):
                continue
            rid = str(r.get("id") or "").strip()
            if rid:
                kb.add(rid)
        ws["known_blueprints"] = sorted(kb)
        ws["free_blueprints_seeded_v1"] = True
        changed = True
    if changed:
        mp[WORKSHOP_META_KEY] = ws
        character.meta_progress = mp
        flag_modified(character, "meta_progress")
    return ws


def save_workshop_state(character: Character, ws: dict[str, Any]) -> None:
    mp = dict(character.meta_progress or {})
    mp[WORKSHOP_META_KEY] = _fix_defaults(ws)
    character.meta_progress = mp
    flag_modified(character, "meta_progress")


def prof_level(character: Character, profession: str) -> int:
    ws = get_workshop_state(character)
    return int(ws["prof_levels"].get(str(profession), 1))


def station_level(character: Character, profession: str) -> int:
    ws = get_workshop_state(character)
    return int(ws["stations"].get(str(profession), 1))


def known_blueprint_ids(character: Character) -> set[str]:
    ws = get_workshop_state(character)
    return {str(x) for x in (ws.get("known_blueprints") or [])}


def add_known_blueprint(character: Character, recipe_id: str) -> bool:
    """Добавить чертёж; True если новый."""
    rid = str(recipe_id).strip()
    if not rid:
        return False
    ws = get_workshop_state(character)
    cur = list(ws.get("known_blueprints") or [])
    if rid in cur:
        return False
    cur.append(rid)
    ws["known_blueprints"] = sorted(set(cur))
    save_workshop_state(character, ws)
    return True


def new_craft_slot_id() -> str:
    return uuid.uuid4().hex[:12]


def increment_counter(character: Character, key: str, n: int = 1) -> None:
    ws = get_workshop_state(character)
    c = dict(ws.get("counters") or {})
    c[key] = int(c.get(key, 0)) + int(n)
    ws["counters"] = c
    save_workshop_state(character, ws)


def set_talisman(character: Character, key: str, value: bool) -> None:
    ws = get_workshop_state(character)
    t = dict(ws.get("talismans") or {})
    t[key] = bool(value)
    ws["talismans"] = t
    save_workshop_state(character, ws)
