"""Точность/уклонение монстров и перелив ЛОВ у убийцы — формулы combat.formulas."""

from __future__ import annotations

import pytest

from game import balance as bal
from game.combat import formulas as f


def test_effective_dodge_subtracts_accuracy() -> None:
    d = 100
    raw = f.dodge_chance_percent(d, dodge_bonus_flat=0.0)
    eff = f.effective_dodge_chance_percent(
        d,
        dodge_bonus_flat=0.0,
        monster_accuracy=0.10,
        class_key="warrior",
    )
    assert eff == pytest.approx(raw - 0.10)


def test_effective_dodge_never_exceeds_raw() -> None:
    d = 150
    raw = f.dodge_chance_percent(d, dodge_bonus_flat=0.0)
    eff = f.effective_dodge_chance_percent(
        d,
        dodge_bonus_flat=0.0,
        monster_accuracy=0.0,
        class_key="wanderer",
    )
    assert eff <= raw + 1e-9


def test_miss_adds_monster_evasion() -> None:
    d = 80
    base = f.miss_chance_percent(d, extra_miss_chance=0.0)
    m1 = f.miss_chance_percent_vs_monster(d, monster_evasion=0.10, class_key="mage")
    assert m1 >= base + 0.09


def test_assassin_shreds_accuracy_and_evasion_overflow() -> None:
    dex_hi = f.min_dexterity_reaching_dodge_cap() + 50
    acc = 0.20
    ev = 0.18
    eff_acc = f.effective_monster_accuracy_on_player(acc, dex_hi, class_key="scout")
    eff_ev = f.effective_monster_evasion_against_player(ev, dex_hi, class_key="assassin")
    assert eff_acc < acc
    assert eff_ev < ev


def test_non_assassin_no_shred() -> None:
    dex_hi = f.min_dexterity_reaching_dodge_cap() + 80
    acc = 0.18
    ev = 0.15
    assert f.effective_monster_accuracy_on_player(acc, dex_hi, class_key="warrior") == pytest.approx(acc)
    assert f.effective_monster_evasion_against_player(ev, dex_hi, class_key="mage") == pytest.approx(ev)


def test_monster_spawn_accuracy_curve() -> None:
    from game.enemies.scaling import monster_accuracy_evasion_for_spawn
    from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate

    t = MonsterTemplate("k", "N", "🎭", "earth", "")
    spawn = FloorMonsterSpawn(slot_code="x", template=t, is_elite=False, is_mini_boss=False, is_major_boss=False)
    a1, e1 = monster_accuracy_evasion_for_spawn(6, spawn)
    a2, e2 = monster_accuracy_evasion_for_spawn(20, spawn)
    assert a2 >= a1
    assert e2 >= e1
    assert a2 <= float(bal.MONSTER_ACCURACY_CAP) + 1e-9
    assert e2 <= float(bal.MONSTER_EVASION_CAP) + 1e-9
