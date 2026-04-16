"""Логика расчёта минут до следующего тика стамины."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from game.economy.stamina import compute_minutes_to_next_regen


def test_minutes_full_stamina_zero() -> None:
    assert compute_minutes_to_next_regen(stamina=20, last_regen_at=None, now=datetime.now(UTC)) == 0


def test_minutes_after_deadline_zero() -> None:
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    last = now - timedelta(seconds=4000)
    assert compute_minutes_to_next_regen(stamina=0, last_regen_at=last, now=now) == 0


def test_minutes_before_deadline_positive() -> None:
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    last = now - timedelta(seconds=1000)
    m = compute_minutes_to_next_regen(stamina=0, last_regen_at=last, now=now)
    assert m >= 1
