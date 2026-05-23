"""Balance tests for necromancer."""

from __future__ import annotations

from game.combat import engine as combat_engine
from game.necromancer import service as necro_svc


class _FakeCharacter:
    __slots__ = ("class_key", "level", "stat_intelligence", "meta_progress", "hp_max")

    def __init__(self) -> None:
        self.class_key = "necromancer"
        self.level = 70
        self.stat_intelligence = 90
        self.hp_max = 8000
        self.meta_progress = {
            "necromancer_v1": {
                "skeleton_unlocks": ["skel_tank", "skel_blade", "skel_mage"],
                "skeleton_party": ["skel_tank", "skel_blade", "skel_mage"],
            },
        }


def test_defensive_barrier_hp_scaled() -> None:
    hp = necro_svc.defensive_barrier_hp(None, hp_max=8000, intelligence=90, level=70)
    assert hp >= 5000


def test_skeleton_atk_combat_mult() -> None:
    ch = _FakeCharacter()
    comps = necro_svc.build_skeleton_companions(ch)  # type: ignore[arg-type]
    blade = next(c for c in comps if c.get("role") == "skel_blade")
    assert int(blade["atk"]) >= 150


def test_nec_mend_heals_companions() -> None:
    from game.archetypes.data import SKILLS

    state = {
        "player_hp": 100,
        "player_hp_max": 1000,
        "player_mp": 500,
        "player_level": 70,
        "player_mp_cost_mult": 1.0,
        "skill_cd": {},
        "stats": {"int": 90, "level": 70, "luck": 10},
        "combat_skills": (SKILLS["nec_bolt"], SKILLS["nec_barrier"], SKILLS["nec_mend"]),
        "monster": {"hp": 1000},
        "companions": [{"name": "Guard", "hp": 50, "hp_max": 500, "dead": False}],
    }
    logs, outcome, _ = combat_engine.player_skill(state, 2)
    assert outcome == "continue"
    assert int(state["player_hp"]) > 100
    assert int(state["companions"][0]["hp"]) > 50
    assert logs


def test_unlock_skeleton_keys() -> None:
    ch = _FakeCharacter()
    unlocks = necro_svc.unlocked_skeleton_keys(ch)  # type: ignore[arg-type]
    assert "skel_tank" in unlocks
    assert "skel_colossus" not in unlocks