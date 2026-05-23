"""Souls currency for necromancer."""

from __future__ import annotations

import random

import pytest

from game.necromancer import souls as souls_mod
from game.necromancer.service import is_necromancer


@pytest.fixture(autouse=True)
def _noop_flag_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("game.necromancer.service.flag_modified", lambda *args, **kwargs: None)


class _FakeCharacter:
    __slots__ = ("class_key", "meta_progress", "stat_intelligence")

    def __init__(self, *, necro: bool = True, souls: int = 0) -> None:
        self.class_key = "necromancer" if necro else "mage"
        self.stat_intelligence = 50
        self.meta_progress = {"necromancer_v1": {"souls": souls, "skeleton_unlocks": ["skel_tank"]}}


def test_non_necromancer_no_souls() -> None:
    ch = _FakeCharacter(necro=False)
    assert souls_mod.get_souls(ch) == 0  # type: ignore[arg-type]
    assert souls_mod.maybe_grant_soul_on_victory(ch) == 0  # type: ignore[arg-type]


def test_add_and_spend_souls() -> None:
    ch = _FakeCharacter(souls=5)
    assert souls_mod.add_souls(ch, 3) == 8  # type: ignore[arg-type]
    assert souls_mod.spend_souls(ch, 4) is True  # type: ignore[arg-type]
    assert souls_mod.get_souls(ch) == 4  # type: ignore[arg-type]


def test_soul_drop_chance(monkeypatch: pytest.MonkeyPatch) -> None:
    ch = _FakeCharacter()
    monkeypatch.setattr(random, "random", lambda: 0.1)
    assert souls_mod.maybe_grant_soul_on_victory(ch) == 1  # type: ignore[arg-type]
    monkeypatch.setattr(random, "random", lambda: 0.9)
    before = souls_mod.get_souls(ch)  # type: ignore[arg-type]
    assert souls_mod.maybe_grant_soul_on_victory(ch) == 0  # type: ignore[arg-type]
    assert souls_mod.get_souls(ch) == before  # type: ignore[arg-type]
