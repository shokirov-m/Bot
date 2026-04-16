"""Кривая опыта и начисление уровней."""

from __future__ import annotations

from types import SimpleNamespace

from game.balance import PROGRESSION_LEVEL1_XP_NEEDED, PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2
from game.characters.progression import experience_needed_for_next_level, zone_multiplier_for_floor
from services.character_service import add_experience


def test_zone_multiplier_edges() -> None:
    assert zone_multiplier_for_floor(0) == 1.0
    assert zone_multiplier_for_floor(1) == 1.0
    assert zone_multiplier_for_floor(15) == 1.0
    assert zone_multiplier_for_floor(16) == 2.5
    assert zone_multiplier_for_floor(100) == 25.0


def test_experience_level1_threshold() -> None:
    assert experience_needed_for_next_level(1, 1) == PROGRESSION_LEVEL1_XP_NEEDED


def test_experience_level2_uses_divisor_vs_raw_formula() -> None:
    """С 2-го уровня порог = ceil(raw / divisor), не «как есть»."""
    floor = 1
    need = experience_needed_for_next_level(2, floor)
    mult = zone_multiplier_for_floor(floor)
    from game.balance import PROGRESSION_BASE_EXP

    n_next = 3
    raw = max(1, int(PROGRESSION_BASE_EXP * (n_next**2.2) * mult))
    assert need == max(1, raw // PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2)


def test_add_experience_single_level() -> None:
    char = SimpleNamespace(level=1, experience=0, floor_number=1, unspent_stat_points=0)
    gained = add_experience(char, PROGRESSION_LEVEL1_XP_NEEDED)
    assert gained == 1
    assert char.level == 2
    assert char.experience == 0
    assert char.unspent_stat_points == 5


def test_add_experience_multi_level_overflow() -> None:
    char = SimpleNamespace(level=1, experience=0, floor_number=1, unspent_stat_points=0)
    need1 = experience_needed_for_next_level(1, 1)
    need2 = experience_needed_for_next_level(2, 1)
    total = need1 + need2 + 10
    gained = add_experience(char, total)
    assert gained == 2
    assert char.level == 3
    assert char.experience == 10
    assert char.unspent_stat_points == 10


def test_add_experience_no_level() -> None:
    char = SimpleNamespace(level=2, experience=0, floor_number=1, unspent_stat_points=0)
    need = experience_needed_for_next_level(2, 1)
    gained = add_experience(char, need - 1)
    assert gained == 0
    assert char.level == 2
    assert char.experience == need - 1
