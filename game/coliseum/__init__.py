"""PvE Колизей: последовательные бои, данные и хуки."""

import game.coliseum.coliseum_data as _coliseum_data

# Каноническое имя — COLISEUM_ENEMY_ATK_MULT. Старые деплои могли иметь только опечатку COLOSSEUM_*.
if hasattr(_coliseum_data, "COLISEUM_ENEMY_ATK_MULT"):
    COLISEUM_ENEMY_ATK_MULT = _coliseum_data.COLISEUM_ENEMY_ATK_MULT
elif hasattr(_coliseum_data, "COLOSSEUM_ENEMY_ATK_MULT"):
    COLISEUM_ENEMY_ATK_MULT = _coliseum_data.COLOSSEUM_ENEMY_ATK_MULT
else:
    COLISEUM_ENEMY_ATK_MULT = 2.5

from game.coliseum.coliseum_data import (
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
