"""
Новая система Архетипов 2.0. 
Старая система классов и навыков полностью удалена.
"""

from __future__ import annotations
from typing import Any

# Временная заглушка для совместимости со старыми импортами
PASSIVE_COMBAT_TABLE: dict[str, dict[str, float | int]] = {
    "wanderer": {"def_bonus": 2.0, "crit_bonus": 0.02, "dodge_bonus": 0.02, "mag_bonus_percent": 0, "mp_regen_turn": 2},
}

SKILL_DEFS_RAW: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {
    "wanderer": (
        {"key": "wn1", "name": "⚔️ Удар", "mp_cost": 5, "cooldown": 0, "power": 1.0, "kind": "phys"},
        {"key": "wn2", "name": "🛡️ Защита", "mp_cost": 0, "cooldown": 0, "power": 0.0, "kind": "phys"},
        {"key": "wn3", "name": "💨 Рывок", "mp_cost": 0, "cooldown": 0, "power": 0.0, "kind": "phys"},
    ),
}

def get_class(class_key: str) -> dict[str, Any] | None:
    return {"key": "wanderer", "skills": {}}

def get_subclass(subclass_key: str) -> dict[str, Any] | None:
    return None
