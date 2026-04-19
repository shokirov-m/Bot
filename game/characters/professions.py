"""
Профессии (замена классовой ветки наставника / подкласса на 57).
Разблокировка по базовым статам БД и счётчикам; бонусы при активной основной профессии;
вторая профессия с 51 этажа — только к пассивным модификаторам боя (см. skills.passive_combat_modifiers_merged).
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
    """Ключ набора навыков из CLASS_SKILLS (skills.py)."""
    skill_class_key: str
    unlock: tuple[UnlockCondition, ...]
    """Плоские статы к effective_primary_stats (только основная профессия)."""
    stat_bonus: dict[str, int]
    """Добавка к базовому шансу успеха заточки (0..1), только для кузнеца при активной профессии."""
    enchant_success_bonus: float = 0.0


PROFESSIONS: tuple[ProfessionDef, ...] = (
    ProfessionDef(
        key="warrior",
        name_ru="Воин",
        name_en="Warrior",
        skill_class_key="warrior",
        unlock=(StatGeUnlock("str", 80),),
        stat_bonus={"str": 10},
    ),
    ProfessionDef(
        key="mage",
        name_ru="Маг",
        name_en="Mage",
        skill_class_key="mage",
        unlock=(StatGeUnlock("int", 80),),
        stat_bonus={"int": 10},
    ),
    ProfessionDef(
        key="archer",
        name_ru="Стрелок",
        name_en="Archer",
        skill_class_key="archer",
        unlock=(StatGeUnlock("dex", 80),),
        stat_bonus={"dex": 10},
    ),
    ProfessionDef(
        key="warden",
        name_ru="Страж",
        name_en="Warden",
        skill_class_key="warden",
        unlock=(StatGeUnlock("vit", 80),),
        stat_bonus={"vit": 10},
    ),
    ProfessionDef(
        key="smith",
        name_ru="Кузнец",
        name_en="Smith",
        skill_class_key="wanderer",
        unlock=(EnchantAttemptsGeUnlock(80),),
        stat_bonus={"vit": 5, "luck": 3},
        enchant_success_bonus=0.06,
    ),
)

PROFESSION_BY_KEY: dict[str, ProfessionDef] = {p.key: p for p in PROFESSIONS}

SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR = 51
