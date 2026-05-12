"""
Точечные тесты для доработок: boss streak, таверна по городам, слияние звёзд, префиксы лога.
"""

from __future__ import annotations

from game.combat import boss_streak
from game.combat import engine as combat_engine
from game.items import enchant as enchant_rules
from game.locations import tavern as tavern_loc
from services import forge_service


class _FakeCharacter:
    __slots__ = ("meta_progress",)

    def __init__(self) -> None:
        self.meta_progress: dict = {}


def _boss_state(floor: int, template_key: str, *, major: bool = True, mini: bool = False) -> dict:
    return {
        "floor": floor,
        "monster": {
            "template_key": template_key,
            "is_major_boss": major,
            "is_mini_boss": mini,
        },
    }


def test_battle_key_from_combat_state() -> None:
    st = _boss_state(20, "boss_slime_king")
    assert boss_streak.battle_key_from_combat_state(st) == "20:boss_slime_king"


def test_defeat_tier_empty() -> None:
    ch = _FakeCharacter()
    st = _boss_state(10, "orc")
    assert boss_streak.defeat_tier_for_battle(ch, st) == 0  # type: ignore[arg-type]


def test_bump_and_tier_and_clear() -> None:
    ch = _FakeCharacter()
    st = _boss_state(10, "orc")
    boss_streak.bump_defeat_streak(ch, st)  # type: ignore[arg-type]
    assert boss_streak.defeat_tier_for_battle(ch, st) == 1  # type: ignore[arg-type]
    boss_streak.bump_defeat_streak(ch, st)  # type: ignore[arg-type]
    assert boss_streak.defeat_tier_for_battle(ch, st) == 2
    boss_streak.clear_defeat_streak(ch, st)  # type: ignore[arg-type]
    assert boss_streak.defeat_tier_for_battle(ch, st) == 0


def test_defeat_tier_capped_at_10() -> None:
    ch = _FakeCharacter()
    k = boss_streak.battle_key_from_combat_state(_boss_state(5, "goblin"))
    ch.meta_progress = {boss_streak.META_BOSS_DEFEAT_STREAK: {k: 99}}
    assert boss_streak.defeat_tier_for_battle(ch, _boss_state(5, "goblin")) == 10  # type: ignore[arg-type]


def test_bump_skips_non_boss() -> None:
    ch = _FakeCharacter()
    st = {
        "floor": 3,
        "monster": {"template_key": "wolf", "is_major_boss": False, "is_mini_boss": False},
    }
    boss_streak.bump_defeat_streak(ch, st)  # type: ignore[arg-type]
    raw = ch.meta_progress.get(boss_streak.META_BOSS_DEFEAT_STREAK)
    assert raw in (None, {})


def test_tavern_offers_regional_lengths() -> None:
    base_n = len(tavern_loc.TAVERN_MENU)
    assert len(tavern_loc.tavern_offers_for_floor(31)) == base_n
    assert len(tavern_loc.tavern_offers_for_floor(61)) == base_n + 2
    assert len(tavern_loc.tavern_offers_for_floor(91)) == base_n + 1


def test_tavern_offer_by_key_requires_floor_for_regional() -> None:
    assert tavern_loc.offer_by_key("mulled") is None
    assert tavern_loc.offer_by_key("mulled", floor_number=61) is not None
    assert tavern_loc.offer_by_key("star_soup", floor_number=91) is not None


def test_forge_star_merge_unlock_floor() -> None:
    assert forge_service.star_merge_unlocked_on_floor(31) is False
    assert forge_service.star_merge_unlocked_on_floor(61) is True
    assert forge_service.star_merge_unlocked_on_floor(91) is True


def test_forge_star_merge_gold_cost_monotonic() -> None:
    costs = [forge_service.star_merge_gold_cost(i) for i in range(0, 6)]
    assert costs == sorted(costs)
    assert costs[0] < costs[-1]


def test_star_merge_bucket_parametrized() -> None:
    cases = [
        ("weapon", "weapon"),
        ("ring", "jewelry"),
        ("amulet", "jewelry"),
        ("armor", "armor_line"),
        ("shield", "armor_line"),
        ("consumable", None),
    ]
    for kind, expected in cases:
        assert forge_service._star_merge_bucket({"kind": kind}) == expected  # noqa: SLF001


def test_apply_dot_damage_player_log_prefix() -> None:
    st = {
        "player_hp": 100,
        "player_hp_max": 100,
        "player_effects": [{"key": "burn", "potency_percent": 10, "turns": 2}],
    }
    logs = combat_engine.apply_dot_damage_player(st)
    assert any(l.startswith("→ 👤") and "Поджог" in l for l in logs)


def test_apply_dot_damage_monster_log_prefix() -> None:
    st = {
        "monster": {"hp": 50, "max_hp": 100},
        "monster_effects": [{"key": "burn", "potency_percent": 10, "turns": 2}],
    }
    logs = combat_engine.apply_dot_damage_monster(st)
    assert any(l.startswith("→ 👹") for l in logs)


def test_enchant_success_via_apply_matches_star_merge_assumption() -> None:
    data = {"enchant": 2, "kind": "weapon", "name": "X"}
    new_data, delta = enchant_rules.apply_enchant_change(dict(data), "success")
    assert delta == 1
    assert enchant_rules.current_enchant_level(new_data) == 3
