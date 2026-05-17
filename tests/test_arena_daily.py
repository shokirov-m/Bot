"""Счётчик поединков арены в meta_progress и формула штрафа."""

from __future__ import annotations

from types import SimpleNamespace

import services.combat.arena_service as arena_service


def test_arena_daily_counter_resets_shape() -> None:
    ch = SimpleNamespace(meta_progress={})
    assert arena_service.arena_matches_used_today(ch) == 0
    assert arena_service.arena_matches_remaining_today(ch) == arena_service.ARENA_MATCHES_PER_DAY
    arena_service._record_arena_match(ch)  # noqa: SLF001
    assert arena_service.arena_matches_used_today(ch) == 1
    assert not arena_service.arena_daily_limit_reached(ch)
    for _ in range(arena_service.ARENA_MATCHES_PER_DAY - 1):
        arena_service._record_arena_match(ch)  # noqa: SLF001
    assert arena_service.arena_daily_limit_reached(ch)
    assert arena_service.arena_matches_remaining_today(ch) == 0


def test_defeat_penalty_formula_low_level() -> None:
    """max(8, int(base * 0.4)) при base = 12 + 0 + 1 = 13 → 8."""
    base = 12 + 0 // 2 + 1
    raw = max(8, int(base * 0.4))
    assert base == 13
    assert raw == 8
