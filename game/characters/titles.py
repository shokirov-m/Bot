"""
Титулы: разблокировка по достижениям, бонусы к золоту/опыту за победу (активный титул в профиле).
Звания с учебного боя — отдельно, см. path_ranks.py.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from db.models.character import Character


def _meta(c: Character) -> dict:
    return dict(c.meta_progress or {})


@dataclass(frozen=True, slots=True)
class TitleDef:
    key: str
    name_ru: str
    sort: int
    check: Callable[[Character], bool]
    unlock_ru: str
    gold_bonus_pct: int = 0
    xp_bonus_pct: int = 0
    stat_str: int = 0
    stat_dex: int = 0
    stat_int: int = 0
    stat_vit: int = 0
    stat_luck: int = 0


def _stranger_done(c: Character) -> bool:
    return int(_meta(c).get("stranger_quests_done", 0)) >= 3


def _city_quests_done(c: Character) -> bool:
    return int(_meta(c).get("city_quests_done", 0)) >= 3


def format_title_bonus_brief(t: TitleDef) -> str:
    """Очень кратко для карточки полных характеристик (слот ① / ②)."""
    parts: list[str] = []
    if t.gold_bonus_pct:
        parts.append(f"+{t.gold_bonus_pct}% золота")
    if t.xp_bonus_pct:
        parts.append(f"+{t.xp_bonus_pct}% опыта")
    for lab, v in (("СИЛ", t.stat_str), ("ЛОВ", t.stat_dex), ("ИНТ", t.stat_int), ("ВЫН", t.stat_vit), ("УДА", t.stat_luck)):
        if v:
            parts.append(f"+{v} {lab}")
    return " ".join(parts) if parts else "—"


def format_title_bonus_line(t: TitleDef) -> str:
    """Краткое описание бонуса активного титула (для профиля и справочника)."""
    parts: list[str] = []
    if t.gold_bonus_pct:
        parts.append(f"+{t.gold_bonus_pct}% золота за победу")
    if t.xp_bonus_pct:
        parts.append(f"+{t.xp_bonus_pct}% опыта за победу")
    st_labels = (
        ("СИЛ", t.stat_str),
        ("ЛОВ", t.stat_dex),
        ("ИНТ", t.stat_int),
        ("ВЫН", t.stat_vit),
        ("УДА", t.stat_luck),
    )
    for lab, v in st_labels:
        if v:
            parts.append(f"+{v} {lab}")
    if not parts:
        return "без числовых бонусов (только строка в профиле)"
    return ", ".join(parts) + " (пока титул активен в профиле)"


ALL_TITLES: tuple[TitleDef, ...] = (
    TitleDef(
        "first_blood",
        "Первая кровь",
        10,
        lambda c: int(c.total_kills) >= 1,
        "1 победа в бою",
        gold_bonus_pct=2,
    ),
    TitleDef(
        "tower_butcher",
        "Мясник башни",
        20,
        lambda c: int(c.total_kills) >= 15,
        "15 побед всего",
        gold_bonus_pct=3,
    ),
    TitleDef(
        "grim_reaper",
        "Жнец",
        30,
        lambda c: int(c.total_kills) >= 50,
        "50 побед всего",
        gold_bonus_pct=4,
        xp_bonus_pct=1,
    ),
    TitleDef(
        "apex_legend",
        "Легенда вершины",
        40,
        lambda c: int(c.total_kills) >= 200,
        "200 побед всего",
        gold_bonus_pct=6,
        xp_bonus_pct=2,
    ),
    TitleDef(
        "climber",
        "Поднимающийся",
        50,
        lambda c: int(c.floor_number) >= 10,
        "достичь 10 этажа",
        xp_bonus_pct=2,
    ),
    TitleDef(
        "citizen_mid",
        "Гражданин средних высот",
        60,
        lambda c: int(c.floor_number) >= 31,
        "достичь 31 этажа",
        gold_bonus_pct=1,
        xp_bonus_pct=3,
    ),
    TitleDef(
        "highborn_climber",
        "Высокий странник",
        70,
        lambda c: int(c.floor_number) >= 61,
        "достичь 61 этажа",
        gold_bonus_pct=2,
        xp_bonus_pct=4,
    ),
    TitleDef(
        "sky_walker",
        "Ходок небес",
        80,
        lambda c: int(c.floor_number) >= 91,
        "достичь 91 этажа",
        gold_bonus_pct=3,
        xp_bonus_pct=5,
    ),
    TitleDef(
        "veteran",
        "Ветеран полей",
        90,
        lambda c: int(c.level) >= 15,
        "15 уровень героя",
        gold_bonus_pct=1,
        xp_bonus_pct=2,
    ),
    TitleDef(
        "master",
        "Мастер пути",
        100,
        lambda c: int(c.level) >= 30,
        "30 уровень героя",
        gold_bonus_pct=2,
        xp_bonus_pct=4,
    ),
    TitleDef(
        "phoenix",
        "Феникс",
        110,
        lambda c: int(c.death_count) >= 3,
        "3 поражения (смерти) всего",
        xp_bonus_pct=3,
    ),
    TitleDef(
        "tavern_regular",
        "Завсегдатай",
        120,
        lambda c: int(c.tavern_visits) >= 5,
        "5 визитов в таверну",
        gold_bonus_pct=2,
    ),
    TitleDef(
        "forge_touched",
        "Касание кузницы",
        130,
        lambda c: int(c.enchant_attempts) >= 5,
        "5 попыток заточки в кузнице",
        gold_bonus_pct=2,
    ),
    TitleDef(
        "stranger_friend",
        "Друг странников",
        140,
        _stranger_done,
        "3 поручения странника",
        gold_bonus_pct=2,
        xp_bonus_pct=2,
    ),
    TitleDef(
        "warden_trusted",
        "Доверие стражи",
        141,
        _city_quests_done,
        "3 городских поручения стражи",
        gold_bonus_pct=2,
        xp_bonus_pct=2,
        stat_vit=1,
    ),
)

TITLE_BY_KEY: dict[str, TitleDef] = {t.key: t for t in ALL_TITLES}
