from game.characters.skills import SkillDef
from game.combat.engine import player_skill


def _state(mp: int = 20) -> dict:
    return {
        "monster": {"name": "Манекен", "hp": 50, "max_hp": 50, "defense": 0, "element": "earth"},
        "stats": {"str": 10, "dex": 10, "int": 10, "vit": 10, "luck": 0},
        "player_hp": 100,
        "player_hp_max": 100,
        "player_mp": mp,
        "player_mp_max": 20,
        "skill_cd": {"0": 0, "1": 0, "2": 0},
        "combat_skills": (
            SkillDef("test_hit", "Проверочный удар", 5, 2, 1.0, "phys"),
            SkillDef("_empty", "", 0, 0, 0.0, "phys"),
            SkillDef("_empty", "", 0, 0, 0.0, "phys"),
        ),
        "weapon_attack": 3,
        "passive_mods": {},
    }


def test_player_skill_spends_mp_and_sets_cooldown() -> None:
    state = _state(mp=20)

    logs, outcome, damage = player_skill(state, 0)

    assert logs
    assert outcome in ("continue", "win")
    assert damage > 0
    assert state["player_mp"] == 15
    assert state["skill_cd"]["0"] == 2


def test_player_skill_without_enough_mp_does_not_crash() -> None:
    state = _state(mp=2)

    logs, outcome, damage = player_skill(state, 0)

    assert "Недостаточно MP" in logs[0]
    assert outcome is None
    assert damage == 0
    assert state["player_mp"] == 2
