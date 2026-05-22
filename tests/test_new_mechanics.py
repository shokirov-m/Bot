"""Регрессия: мастера зоны, библиотека, испытания этажа."""

from __future__ import annotations

from types import SimpleNamespace

from game.locations import grimoire_library as lib
from game.tower.quests import pack_npc_quests as pqn
from game.tower.trials import floor_trial as ft
import services.progression.pack_npc_quest_service as pack_svc


def _char(*, floor: int = 5, highest: int = 20, meta: dict | None = None):
    return SimpleNamespace(
        floor_number=floor,
        highest_floor_reached=highest,
        display_name="Тестер",
        meta_progress=meta or {},
        gold=500_000,
        level=60,
        class_key="warrior",
    )


def test_greeting_uses_display_name():
    npc = {"greeting_by_reputation": {"neutral": "Привет, {player_name}!"}}
    line = pack_svc.greeting_line(_char(), npc)
    assert "Тестер" in line


def test_hub_floor_shows_all_npc_quests():
    from game.data.packs import load_zone_pack

    pack = load_zone_pack("forest_beginnings")
    entries = (pack.get("npcs") or {}).get("entries") or []
    assert entries
    npc = entries[0]
    hub = int((npc.get("floors_hub") or [5])[0])
    quests = pqn.quests_for_npc_on_floor(npc, hub)
    assert len(quests) >= len(npc.get("quests") or [])


def test_library_floor_ok_requires_hub():
    c = _char(floor=9001, highest=20)
    assert lib.library_unlocked(c)
    assert lib.library_floor_ok(c, 9001)
    c2 = _char(floor=18, highest=20)
    assert not lib.library_floor_ok(c2, 18)


def test_trial_meta_per_floor_persists():
    c = _char(floor=61, highest=70, meta={
        ft.META_KEY: {
            "61": {
                "floor": 61,
                "grounds_open": ["ft_g00"],
                "grounds_cleared": ["ft_g00"],
                "completed": False,
                "progress_pct": 10,
            },
        },
    })
    ft.ensure_started(c)
    st61 = ft._trial_meta(c, 61)
    assert st61 is not None
    assert "ft_g00" in (st61.get("grounds_cleared") or [])

    c.floor_number = 60
    ft.ensure_started(c)
    st61_after = ft._trial_meta(c, 61)
    assert st61_after is not None
    assert "ft_g00" in (st61_after.get("grounds_cleared") or [])


def test_trial_checkmark_only_cleared_grounds():
    c = _char(
        floor=61,
        highest=70,
        meta={
            ft.META_KEY: {
                "61": {
                    "floor": 61,
                    "grounds_open": ["ft_g00", "ft_g01"],
                    "grounds_cleared": ["ft_g00"],
                    "ground_progress": {"ft_g01": {"wins": 1}},
                    "completed": False,
                },
            },
        },
    )
    cleared = ft.trial_cleared_slots_for_ui(c)
    assert "ft_g00" in cleared
    assert "ft_g01" not in cleared
