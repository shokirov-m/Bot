"""PvE Колизей: последовательные бои, данные и хуки."""

from game.coliseum.coliseum_data import (
    COLISEUM_TEMPLATE_KEY,
    ColiseumFighter,
    build_coliseum_monster_bundle,
    build_coliseum_spawn,
    coliseum_slot_code,
    fighter_by_id,
    normalized_battle_element,
)

__all__ = [
    "COLISEUM_TEMPLATE_KEY",
    "ColiseumFighter",
    "build_coliseum_monster_bundle",
    "build_coliseum_spawn",
    "coliseum_slot_code",
    "fighter_by_id",
    "normalized_battle_element",
]
