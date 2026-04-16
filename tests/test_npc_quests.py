"""Пул квестов NPC на этажах ×3."""

from __future__ import annotations

from game.quests.npc_quests import generate_quest_pool, template_by_key, templates_for_floor


def test_quest_pool_covers_multiples_of_three() -> None:
    pool = generate_quest_pool()
    assert 3 in pool and 99 in pool
    assert 4 not in pool
    assert len(pool[3]) == 2
    assert len(pool[30]) == 2


def test_template_by_key() -> None:
    t = template_by_key("npcq_6_hunt")
    assert t is not None
    assert t.floor == 6
    assert t.quest_type == "kill"


def test_floor_three_not_hundred() -> None:
    assert templates_for_floor(100) == []
