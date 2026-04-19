"""
Все монстры в одном формате (как JSON-пример): id, name, level, hp, atk, def, exp, gold, …

Источник данных: game.data.monsters (файлы JSON + enrich).
"""

from __future__ import annotations

import copy
from typing import Any

from game.data.monsters import get_catalog_definitions

_MONSTER_DEFINITIONS: dict[str, dict[str, Any]] | None = None


def get_all_definitions() -> dict[str, dict[str, Any]]:
    """Полный словарь id → карточка монстра."""
    global _MONSTER_DEFINITIONS
    if _MONSTER_DEFINITIONS is None:
        _MONSTER_DEFINITIONS = get_catalog_definitions()
    return _MONSTER_DEFINITIONS


ICE_ELEMENTAL_OVERRIDE: dict[str, Any] = copy.deepcopy(
    get_catalog_definitions()["ice_elemental"],
)


__all__ = ["get_all_definitions", "ICE_ELEMENTAL_OVERRIDE"]
