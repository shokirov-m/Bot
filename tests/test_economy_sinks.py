from __future__ import annotations

from types import SimpleNamespace

from game.economy import sinks as s


def test_lottery_ticket_cost_scales() -> None:
    assert s.lottery_ticket_cost_gold(3) < s.lottery_ticket_cost_gold(91)


def test_borrow_increases_debt() -> None:
    c = SimpleNamespace(meta_progress={}, gold=0, floor_number=31, level=10)
    assert s.moneylender_debt(c) == 0
    d = s.debt_for_borrow(200)
    assert d > 200
    assert d == int(200 * 1.30) + max(0, 200 // 55)


def test_garnish_victory_pays_debt() -> None:
    c = SimpleNamespace(meta_progress={s.META_ML_DEBT: 500})
    net, note = s.garnish_victory_gold_for_debt(c, 100)
    assert net < 100
    assert s.moneylender_debt(c) == 500 - (100 - net)
    assert "Ростовщик" in note


def test_garnish_skips_without_debt() -> None:
    c = SimpleNamespace(meta_progress={})
    net, note = s.garnish_victory_gold_for_debt(c, 80)
    assert net == 80
    assert note == ""


def test_lottery_draw_bounds() -> None:
    cost = 50
    for _ in range(30):
        dg, dr, code = s.run_lottery_draw(cost)
        assert dr in (0, 1)
        assert -cost <= dg <= cost * 8
        assert code in ("blank", "small_win", "nice_win", "rune_pair", "jackpot")


def test_escape_then_pop_xp_multiplier() -> None:
    c = SimpleNamespace(meta_progress={})
    assert s.pop_next_win_xp_multiplier(c) == 1.0
    s.set_escape_success_xp_penalty(c)
    assert c.meta_progress.get(s.META_NEXT_WIN_XP_MULT) == 0.9
    assert abs(s.pop_next_win_xp_multiplier(c) - 0.9) < 1e-6
    assert s.META_NEXT_WIN_XP_MULT not in c.meta_progress
    assert s.pop_next_win_xp_multiplier(c) == 1.0
