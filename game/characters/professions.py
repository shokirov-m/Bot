"""
Система профессий 1.0 удалена. 
Ожидается внедрение Архетипов 2.0.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

StatKey = Literal["str", "dex", "int", "vit", "luck"]

STAT_COLUMN: dict[StatKey, str] = {
    "str": "stat_strength",
    "dex": "stat_dexterity",
    "int": "stat_intelligence",
    "vit": "stat_vitality",
    "luck": "stat_luck",
}

@dataclass(frozen=True, slots=True)
class StatGeUnlock:
    stat: StatKey
    value: int

@dataclass(frozen=True, slots=True)
class EnchantAttemptsGeUnlock:
    value: int

UnlockCondition = StatGeUnlock | EnchantAttemptsGeUnlock

@dataclass(frozen=True, slots=True)
class ProfessionDef:
    key: str
    name_ru: str
    name_en: str
    skill_class_key: str
    unlock: tuple[UnlockCondition, ...]
    stat_bonus: dict[str, int]
    enchant_success_bonus: float = 0.0

PROFESSIONS: tuple[ProfessionDef, ...] = ()
PROFESSION_BY_KEY: dict[str, ProfessionDef] = {}
SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR = 999
