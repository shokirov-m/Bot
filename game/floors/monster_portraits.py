"""Локальные портреты для отдельных мини-боссов / боссов (экран боя)."""

from __future__ import annotations

from pathlib import Path

from game.items.equipment.item_asset_paths import tower_bot_root

_BATTLE_PORTRAIT_FILES: dict[str, str] = {
    "mini_alpha_wolf": "assets/monsters/mini_alpha_wolf.png",
    "boss_ancient_treant": "assets/monsters/boss_ancient_treant.png",
}


def combat_monster_portrait_path(template_key: str) -> str | None:
    """Путь к PNG для боя или None, если файла нет."""
    rel = _BATTLE_PORTRAIT_FILES.get((template_key or "").strip())
    if rel is None:
        return None
    p = tower_bot_root() / rel
    if p.is_file():
        return str(p)
    return None
