"""Бонусы характеристик с предметов (item_data)."""

from __future__ import annotations

from game.items.stat_bonuses import stat_bonuses_from_item_data


def test_stat_bonuses_flat_and_nested_and_aliases() -> None:
    d = {
        "str": 2,
        "strength": 1,
        "stat_bonus": {"dex": 1, "luck": 2},
    }
    b = stat_bonuses_from_item_data(d)
    assert b["str"] == 3
    assert b["dex"] == 1
    assert b["luck"] == 2
    assert b["int"] == 0
    assert b["vit"] == 0
