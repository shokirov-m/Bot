"""
Цепочка особых миссий «Странник» за славу 150+.
Прогресс в character.meta_progress['wanderer_fame_chain_v1'].
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WandererFameStep:
    key: str
    title: str
    description: str
    quest_type: str  # kills_any | kills_elite | daily_claim | arena_win | seal_claim
    target: int
    reward_gold: int
    reward_xp: int
    reward_runes: int = 0


META_WANDERER_FAME_CHAIN = "wanderer_fame_chain_v1"

# Пять шагов: четыре с прогрессом + финальная печать (кнопка «забрать»).
WANDERER_FAME_STEPS: tuple[WandererFameStep, ...] = (
    WandererFameStep(
        "wf_s1",
        "Тени у подножия",
        "Победи 12 врагов в башне (любых).",
        "kills_any",
        12,
        90,
        55,
    ),
    WandererFameStep(
        "wf_s2",
        "Долг дня",
        "Забери награду за любое ежедневное задание.",
        "daily_claim",
        1,
        70,
        45,
    ),
    WandererFameStep(
        "wf_s3",
        "Метка элиты",
        "Победи 3 элитных врагов.",
        "kills_elite",
        3,
        130,
        85,
        1,
    ),
    WandererFameStep(
        "wf_s4",
        "Проверка арены",
        "Одолей соперника на арене (победа).",
        "arena_win",
        1,
        160,
        110,
    ),
    WandererFameStep(
        "wf_s5",
        "Печать странника",
        "Получи завет — награда за весь путь.",
        "seal_claim",
        1,
        220,
        160,
        3,
    ),
)
