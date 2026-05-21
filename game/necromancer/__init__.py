"""Некромант: призыв скелетов вместо наёмников."""

from game.necromancer.service import (
    NECROMANCER_CLASS_KEY,
    NECROMANCER_COST_GOLD,
    NECROMANCER_MIN_LEVEL,
    build_skeleton_companions,
    can_purchase_necromancer,
    clear_merc_party_for_necromancer,
    ensure_necro_meta,
    get_party_skeleton_keys,
    is_necromancer,
    purchase_necromancer,
    set_party_skeleton_keys,
    skeleton_role_label,
    unlocked_skeleton_keys,
)

__all__ = [
    "NECROMANCER_CLASS_KEY",
    "NECROMANCER_COST_GOLD",
    "NECROMANCER_MIN_LEVEL",
    "build_skeleton_companions",
    "can_purchase_necromancer",
    "clear_merc_party_for_necromancer",
    "ensure_necro_meta",
    "get_party_skeleton_keys",
    "is_necromancer",
    "purchase_necromancer",
    "set_party_skeleton_keys",
    "skeleton_role_label",
    "unlocked_skeleton_keys",
]
