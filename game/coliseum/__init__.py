"""PvE Колизей: последовательные бои, данные и хуки."""

from game.coliseum.coliseum_data import (
    COLISEUM_ENEMY_ATK_MULT,
    COLISEUM_TEMPLATE_KEY,
    ColiseumFighter,
    build_coliseum_monster_bundle,
    build_coliseum_spawn,
    coliseum_slot_code,
    fighter_by_id,
    normalized_battle_element,
    scaled_coliseum_atk,
)

__all__ = [
    "COLISEUM_ENEMY_ATK_MULT",
    "COLISEUM_TEMPLATE_KEY",
    "ColiseumFighter",
    "build_coliseum_monster_bundle",
    "build_coliseum_spawn",
    "coliseum_slot_code",
    "fighter_by_id",
    "normalized_battle_element",
    "scaled_coliseum_atk",
]
