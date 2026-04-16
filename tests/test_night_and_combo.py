from __future__ import annotations

from game.combat import night_mode
from game.combat import engine


def test_night_hours_utc() -> None:
    assert night_mode.is_night_utc_at_hour(22) is True
    assert night_mode.is_night_utc_at_hour(23) is True
    assert night_mode.is_night_utc_at_hour(0) is True
    assert night_mode.is_night_utc_at_hour(5) is True
    assert night_mode.is_night_utc_at_hour(6) is False
    assert night_mode.is_night_utc_at_hour(12) is False
    assert night_mode.is_night_utc_at_hour(21) is False


def test_apply_night_monster_bundle() -> None:
    m = {"hp": 100, "max_hp": 100, "atk": 50}
    night_mode.apply_night_to_monster_bundle(m)
    assert m["hp"] == 120
    assert m["max_hp"] == 120
    assert m["atk"] == 60


def test_combo_three_strikes_then_bonus() -> None:
    state: dict = {"combo_streak": 0, "combo_next_mult": 1.0}
    logs: list[str] = []

    d1 = engine.combo_apply_outgoing_damage(state, 10, logs)
    assert d1 == 10
    assert state["combo_streak"] == 1
    assert state["combo_next_mult"] == 1.0

    d2 = engine.combo_apply_outgoing_damage(state, 10, logs)
    assert d2 == 10
    assert state["combo_streak"] == 2

    d3 = engine.combo_apply_outgoing_damage(state, 10, logs)
    assert d3 == 10
    assert state["combo_streak"] == 0
    assert abs(state["combo_next_mult"] - engine.COMBO_BONUS_MULT) < 1e-9
    assert any("x3" in x.lower() for x in logs)

    logs.clear()
    d4 = engine.combo_apply_outgoing_damage(state, 100, logs)
    assert d4 == 115
    assert state["combo_next_mult"] == 1.0
    assert state["combo_streak"] == 1
    assert logs and ("+15%" in logs[-1] or any("+15%" in x for x in logs))


def test_combo_break_on_hurt() -> None:
    state: dict = {"combo_streak": 2, "combo_next_mult": 1.15}
    engine.combo_break_on_player_hurt(state)
    assert state["combo_streak"] == 0
    assert state["combo_next_mult"] == 1.0


def test_combo_disabled_in_tutorial() -> None:
    state: dict = {"is_tutorial": True, "combo_streak": 0, "combo_next_mult": 1.0}
    logs: list[str] = []
    for _ in range(5):
        engine.combo_apply_outgoing_damage(state, 10, logs)
    assert state["combo_streak"] == 0
    assert state["combo_next_mult"] == 1.0
