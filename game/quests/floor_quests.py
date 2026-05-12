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
    """Золото и опыт за выполнение (снимок при принятии). Усиление с этажом."""
    f = max(1, int(floor_number))
    k = max(1, int(kills_needed))
    mult = 1.0 + (f - 1) * 0.015
    gold = int((45 + f * 5 + k * 14) * mult)
    xp = int((28 + f * 3 + k * 10) * mult)
    return gold, xp
