"""Детерминированные проверки урона при фиксированном random."""

from __future__ import annotations

from unittest.mock import patch

from game.combat import formulas


@patch("game.combat.formulas.random.uniform", return_value=1.0)
def test_physical_damage_no_defense(mock_uniform) -> None:
    # base = 10*2+8 = 28, rolled 28, defense 5 -> 23
    assert formulas.physical_damage(10, 8, 5) == 23


@patch("game.combat.formulas.random.uniform", return_value=0.85)
def test_physical_damage_minimum_roll(mock_uniform) -> None:
    # base 28 * 0.85 = 23.8 -> 23 int, -5 def = 18
    assert formulas.physical_damage(10, 8, 5) == 18


def test_physical_damage_range_mid() -> None:
    lo, hi = formulas.physical_damage_range(10, 8, enemy_defense=0)
    assert lo <= hi
    assert lo >= 1
