"""Простые контракты NPC хаба (прогресс в meta shadow_market_quests_v1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character

META_QUESTS = "shadow_market_quests_v1"


def _q(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_QUESTS)
    return dict(raw) if isinstance(raw, dict) else {}


def _save(character: Character, data: dict[str, Any]) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_QUESTS] = data
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass


def quest_status(character: Character, quest_key: str) -> str:
    return str(_q(character).get(quest_key, "new"))


def start_quest(character: Character, quest_key: str) -> None:
    d = _q(character)
    if d.get(quest_key) == "done":
        return
    d[quest_key] = "active"
    _save(character, d)


def complete_quest(character: Character, quest_key: str, reward_gold: int) -> str:
    d = _q(character)
    d[quest_key] = "done"
    _save(character, d)
    character.gold = int(character.gold) + int(reward_gold)
    return f"Контракт закрыт: +{reward_gold} 💰"
