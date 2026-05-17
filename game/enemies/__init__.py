"""
Противники и каталоги врагов (этап B реорганизации).

Подпакеты:
  catalog   — JSON-карточки, registry
  floors    — спавны башни
  coliseum  — 50 бойцов колизея
  events    — золотой гоблин и мировые события
"""

from game.enemies.floors.spawns import (
    FloorMonsterSpawn,
    MonsterTemplate,
    build_spawns_for_floor,
)

__all__ = [
    "FloorMonsterSpawn",
    "MonsterTemplate",
    "build_spawns_for_floor",
]
