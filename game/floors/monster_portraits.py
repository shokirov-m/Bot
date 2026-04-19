"""Портрет монстра на экране боя: assets/monsters/{template_key}.png (+ элита → базовый ключ)."""

from __future__ import annotations

from pathlib import Path

from game.items.equipment.item_asset_paths import tower_bot_root

# Явный путь, если файл назван иначе (редко).
_BATTLE_PORTRAIT_OVERRIDES: dict[str, str] = {}


def combat_monster_portrait_path(template_key: str) -> str | None:
    """Путь к PNG для боя или None, если файла нет."""
    k = (template_key or "").strip()
    if not k:
        return None
    root = tower_bot_root()
    rel_ov = _BATTLE_PORTRAIT_OVERRIDES.get(k)
    if rel_ov:
        p = root / rel_ov
        if p.is_file():
            return str(p)
    base_k = k[7:] if k.startswith("elite_") else k
    for cand in (k, base_k):
        rel = Path("assets") / "monsters" / f"{cand}.png"
        p = root / rel
        if p.is_file():
            return str(p)
    return None
