"""Юнит-тесты правил admin/anticheat.py (без БД)."""

from __future__ import annotations

from datetime import UTC, datetime

from admin import anticheat


def _ctx(tid: int = 1) -> dict:
    return {
        "telegram_id": tid,
        "username": "u",
        "floor": 5,
        "level": 10,
    }


def test_check_fight_speed_no_alert_below_threshold() -> None:
    assert anticheat.check_fight_speed(2, **_ctx()) is None


def test_check_fight_speed_alert_at_threshold() -> None:
    a = anticheat.check_fight_speed(anticheat.SPEED_MAX_FIGHTS_PER_10S, **_ctx())
    assert a is not None
    assert a.check_type == "speed"


def test_check_gold_gain_no_alert() -> None:
    assert anticheat.check_gold_gain(anticheat.ECONOMY_MAX_GOLD_GAIN_PER_HOUR, **_ctx()) is None


def test_check_gold_gain_alert() -> None:
    a = anticheat.check_gold_gain(anticheat.ECONOMY_MAX_GOLD_GAIN_PER_HOUR + 1, **_ctx())
    assert a is not None
    assert a.check_type == "economy"


def test_check_damage_below_ceiling() -> None:
    assert (
        anticheat.check_damage_value(
            100,
            strength=10,
            weapon_atk=5,
            **_ctx(),
        )
        is None
    )


def test_check_damage_impossible() -> None:
    a = anticheat.check_damage_value(
        999_999,
        strength=5,
        weapon_atk=1,
        **_ctx(),
    )
    assert a is not None
    assert a.check_type == "damage"


def test_check_floor_progress_no_jump() -> None:
    assert anticheat.check_floor_progress(5, 5, 1.0, **_ctx()) is None


def test_check_floor_progress_fast_climb() -> None:
    a = anticheat.check_floor_progress(1, 10, 5.0, **_ctx())
    assert a is not None
    assert a.check_type == "progress"


def test_check_skill_damage_within_ceiling() -> None:
    assert (
        anticheat.check_skill_damage_value(
            9000,
            kind="phys",
            strength=120,
            intelligence=10,
            weapon_atk=200,
            skill_power=1.65,
            **_ctx(),
        )
        is None
    )


def test_check_skill_damage_absurd() -> None:
    a = anticheat.check_skill_damage_value(
        999_999,
        kind="mag",
        strength=5,
        intelligence=8,
        weapon_atk=3,
        skill_power=1.2,
        **_ctx(),
    )
    assert a is not None
    assert a.check_type == "damage_skill"


def test_anticheat_alert_to_payload() -> None:
    al = anticheat.AnticheatAlert(
        severity="ALERT",
        check_type="speed",
        telegram_id=9,
        username=None,
        floor=1,
        level=2,
        description="x",
        value=3,
        expected_max=2,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    p = al.to_payload()
    assert p["telegram_id"] == 9
    assert "timestamp" in p
