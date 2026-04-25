from __future__ import annotations

from db.models.character import Character
from game.archetypes import manager as arch_manager


def _char(**kwargs: object) -> Character:
    data = dict(
        user_id=1,
        display_name="T",
        class_key="warrior",
        level=30,
        stat_strength=40,
        stat_dexterity=10,
        stat_intelligence=10,
        stat_vitality=30,
        stat_luck=10,
        floor_number=1,
        highest_floor_reached=1,
        meta_progress={},
    )
    data.update(kwargs)
    return Character(**data)


def test_tier2_requires_parent_path() -> None:
    c = _char(class_key="mage", stat_intelligence=40)
    ok, msg = arch_manager.can_unlock_archetype(c, "guardian")
    assert ok is False
    assert "Воин" in msg


def test_tier2_stat_requirement_uses_real_character_columns() -> None:
    c = _char(class_key="warrior", stat_strength=40, stat_vitality=30)
    ok, _ = arch_manager.can_unlock_archetype(c, "guardian")
    assert ok is True


def test_tier2_base_skills_survive_old_unlocked_nodes() -> None:
    c = _char(class_key="guardian", meta_progress={"unlocked_nodes": ["war_g3"]})
    skills = [s.key for s in arch_manager.get_unlocked_skills(c)]
    assert "grd_wall" in skills
    assert "grd_crush" in skills
