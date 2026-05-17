"""
Золотой гоблин: правила этажа и сборка спавна (без БД / планировщика).
"""

from __future__ import annotations

from game.data.monsters import MONSTER_TEMPLATE_META
from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate

TEMPLATE_KEY = "golden_goblin"
SLOT_CODE = "gg"
FLOOR_MIN = 5
FLOOR_MAX = 25


def floor_accepts_golden_goblin_event(floor_number: int) -> bool:
    fl = int(floor_number)
    if fl < FLOOR_MIN or fl > FLOOR_MAX:
        return False
    from game.tower.mechanics import registry as mech
    from game.tower.progression import floor_data as fd_mod

    if mech.is_scenario_floor(fl):
        return False
    if fd_mod.is_major_boss_floor(fl) or fd_mod.is_mini_boss_floor(fl):
        return False
    return True


def build_spawn() -> FloorMonsterSpawn:
    meta = MONSTER_TEMPLATE_META[TEMPLATE_KEY]
    tpl = MonsterTemplate(
        key=TEMPLATE_KEY,
        name=str(meta.get("display_name", "Золотой гоблин")),
        emoji=str(meta.get("emoji", "💰")),
        element=str(meta.get("element", "earth")),
        blurb=str(meta.get("blurb", "")),
    )
    return FloorMonsterSpawn(
        slot_code=SLOT_CODE,
        template=tpl,
        is_elite=False,
        is_mini_boss=False,
        is_major_boss=False,
    )
