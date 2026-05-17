"""Regression: floor-1 city guard quest tier + unified XP curve."""
from __future__ import annotations

from game.balance import PROGRESSION_BASE_EXP, PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2
from game.tower.progression import floor_data
from game.quests.city_quests import city_quest_template
from services.progression.character_service import experience_needed_for_next_level


def test_floor1_city_quest_not_endgame_values() -> None:
    assert floor_data.get_city_for_floor(1) is not None
    tpl = city_quest_template(1)
    assert tpl is not None
    assert tpl.quest_key == "city_task_1"
    assert tpl.kills_needed == 1
    assert tpl.reward_gold <= 50
    assert tpl.reward_xp <= 50


def test_experience_formula_unified_level_1_and_2() -> None:
    n2 = max(1, int(PROGRESSION_BASE_EXP * (2**2.2)))
    need_1 = max(1, n2 // PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2)
    assert experience_needed_for_next_level(1, 1) == need_1
    n3 = max(1, int(PROGRESSION_BASE_EXP * (3**2.2)))
    need_2 = max(1, n3 // PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2)
    assert experience_needed_for_next_level(2, 1) == need_2
