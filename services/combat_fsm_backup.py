"""
Резерв к состояния боя в character.meta (JSON) — если FSM (Memory/Redis) сброшен,
а в чате остались кнопки, колбэк сможет восстановить ход.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any

from db.models.character import Character

META_KEY = "combat_recover_v1"
_MAX_AGE_SEC = 8 * 3600
_VERSION = 1


def _json_safe(d: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(d, default=str))


def _flag_meta(character: Character) -> None:
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(character, "meta_progress")
    except Exception:
        pass


def clear_combat_backup(character: Character) -> None:
    mp = dict(character.meta_progress or {})
    if META_KEY not in mp:
        return
    del mp[META_KEY]
    character.meta_progress = mp
    _flag_meta(character)


def persist_combat_backup(character: Character, combat_state: dict[str, Any]) -> None:
    if not isinstance(combat_state, dict) or not combat_state:
        return
    try:
        # SkillDef не сериализуется в JSON нормально (default=str → мусор); в бою всегда
        # подставляем battle_skills_tuple в handle_combat_callback.
        to_store = dict(combat_state)
        to_store.pop("combat_skills", None)
        payload = {
            "v": _VERSION,
            "t": int(time.time()),
            "cid": int(character.id),
            "c": _json_safe(to_store),
        }
    except (TypeError, ValueError, RecursionError):
        return
    mp = dict(character.meta_progress or {})
    mp[META_KEY] = payload
    character.meta_progress = mp
    _flag_meta(character)


def try_restore_combat_backup(character: Character) -> dict[str, Any] | None:
    """Возврат — глубокая копия combat-словаря либо None (нет / просрочен / неверный герой)."""
    mp = character.meta_progress or {}
    raw = mp.get(META_KEY)
    if not isinstance(raw, dict):
        return None
    if int(raw.get("cid", 0) or 0) != int(character.id):
        return None
    if int(time.time()) - int(raw.get("t", 0) or 0) > _MAX_AGE_SEC:
        return None
    c = raw.get("c")
    if not isinstance(c, dict) or "monster" not in c or "player_hp" not in c:
        return None
    return copy.deepcopy(c)


def combat_backup_failure_reason(character: Character) -> str:
    """Короткий код причины, почему try_restore вернул None (для логов отладки)."""
    mp = character.meta_progress or {}
    raw = mp.get(META_KEY)
    if not isinstance(raw, dict):
        return "no_meta_key"
    if int(raw.get("cid", 0) or 0) != int(character.id):
        return "cid_mismatch"
    if int(time.time()) - int(raw.get("t", 0) or 0) > _MAX_AGE_SEC:
        return "expired"
    c = raw.get("c")
    if not isinstance(c, dict):
        return "c_not_dict"
    if "monster" not in c or "player_hp" not in c:
        return "c_incomplete"
    return "unknown"
