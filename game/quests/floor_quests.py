"""
Простые квесты странника (NPC на каждом 3-м этаже): убить N врагов башни.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.floors import floor_data


@dataclass(frozen=True, slots=True)
class FloorQuestTemplate:
    quest_key: str
    title: str
    kills_needed: int


def npc_quest_template(floor_number: int) -> FloorQuestTemplate | None:
    if not floor_data.has_quest_npc(floor_number):
        return None
    zone = floor_data.get_zone_for_floor(floor_number)
    need = 2 if floor_number < 30 else 3
    return FloorQuestTemplate(
        quest_key=f"tower_slain_{floor_number}",
        title=f"Долг странника — этаж {floor_number}",
        kills_needed=need,
    )


def reward_for_quest(floor_number: int, kills_needed: int) -> tuple[int, int]:
    """Золото и опыт за выполнение (снимок при принятии)."""
    gold = 35 + floor_number * 3 + kills_needed * 10
    xp = 20 + floor_number * 2 + kills_needed * 8
    return gold, xp
