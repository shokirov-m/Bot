"""Счётчик поражений от одного босса (этаж + шаблон) для более жёстких реплик."""

from __future__ import annotations

from typing import Any

from db.models.character import Character
from sqlalchemy.orm.attributes import flag_modified

META_BOSS_DEFEAT_STREAK = "boss_defeat_streak_v1"


def battle_key_from_combat_state(combat_state: dict[str, Any]) -> str:
    fl = int(combat_state.get("floor") or 0)
    m = combat_state.get("monster") or {}
    tk = str(m.get("template_key") or "").strip()
    return f"{fl}:{tk}"


def defeat_tier_for_battle(character: Character, combat_state: dict[str, Any]) -> int:
    mp = character.meta_progress or {}
    raw = mp.get(META_BOSS_DEFEAT_STREAK)
    if not isinstance(raw, dict):
        return 0
    k = battle_key_from_combat_state(combat_state)
    return max(0, min(10, int(raw.get(k, 0))))


def bump_defeat_streak(character: Character, combat_state: dict[str, Any]) -> None:
    m = combat_state.get("monster") or {}
    if not (m.get("is_major_boss") or m.get("is_mini_boss")):
        return
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_BOSS_DEFEAT_STREAK)
    d = dict(raw) if isinstance(raw, dict) else {}
    k = battle_key_from_combat_state(combat_state)
    d[k] = int(d.get(k, 0)) + 1
    mp[META_BOSS_DEFEAT_STREAK] = d
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass


def clear_defeat_streak(character: Character, combat_state: dict[str, Any]) -> None:
    m = combat_state.get("monster") or {}
    if not (m.get("is_major_boss") or m.get("is_mini_boss")):
        return
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_BOSS_DEFEAT_STREAK)
    if not isinstance(raw, dict):
        return
    d = dict(raw)
    k = battle_key_from_combat_state(combat_state)
    if k in d:
        del d[k]
    mp[META_BOSS_DEFEAT_STREAK] = d
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass
