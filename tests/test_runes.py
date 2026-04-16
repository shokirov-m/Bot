"""Руны: слоты, бонус урона, синергии."""

from __future__ import annotations

from game.items.runes import (
    RuneData,
    calculate_elemental_bonus,
    get_synergy,
    max_rune_slots,
    rune_combat_extras,
    total_weapon_rune_flat_elemental_damage,
)


def test_max_rune_slots_by_rarity() -> None:
    assert max_rune_slots("common") == 0
    assert max_rune_slots("rare") == 1
    assert max_rune_slots("epic") == 2
    assert max_rune_slots("legendary") == 3


def test_weak_spot_multiplier() -> None:
    r = [RuneData("fire", 1)]
    # 8 * 1.5 = 12 vs fire monster
    assert calculate_elemental_bonus(r, "fire", None) >= 12


def test_flat_elemental_sum() -> None:
    runes = [RuneData("fire", 3)]
    assert total_weapon_rune_flat_elemental_damage(runes) == 15


def test_synergy_plasma() -> None:
    runes = [RuneData("fire", 2), RuneData("lightning", 2)]
    syn = get_synergy(runes)
    assert syn is not None
    assert syn["name"] == "Плазма"
    ex = rune_combat_extras(runes)
    assert ex["synergy_name"] == "Плазма"
