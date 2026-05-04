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


def _coliseum_defeated_ids(c: Character) -> set[int]:
    raw = _meta(c).get("coliseum_v1")
    if not isinstance(raw, dict):
        return set()
    d = raw.get("defeated")
    if not isinstance(d, list):
        return set()
    out: set[int] = set()
    for x in d:
        try:
            out.add(int(x))
        except (TypeError, ValueError):
            continue
    return out


def _workshop_tal(c: Character, key: str) -> bool:
    ws = _meta(c).get("workshop_v1")
    if not isinstance(ws, dict):
        return False
    t = ws.get("talismans") or {}
    return bool(t.get(key))


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
    TitleDef(
        "icy_conqueror",
        "Покоритель льдов",
        150,
        lambda c: int(c.floor_number) >= 40,
        "достичь 40 этажа",
        stat_str=5,
    ),
    TitleDef(
        "alchemist_apprentice",
        "Ученик алхимика",
        160,
        lambda c: int(_meta(c).get("elixirs_brewed", 0)) >= 10,
        "сварить 10 эликсиров",
        stat_int=5,
    ),
    TitleDef(
        "monster_scholar",
        "Исследователь монстров",
        170,
        lambda c: int(c.total_kills) >= 500, # Using total kills as proxy or just more kills
        "совершить 500 убийств монстров",
        stat_luck=3,
    ),
    TitleDef(
        "wealthy_adventurer",
        "Богатый странник",
        180,
        lambda c: int(c.gold) >= 100000,
        "накопить 100 000 золота",
        gold_bonus_pct=5,
    ),
    TitleDef(
        "gladiator",
        "Гладиатор",
        190,
        lambda c: int((c.meta_progress or {}).get("arena_wins", 0)) >= 20,
        "победить в 20 боях на арене",
        stat_dex=5,
        gold_bonus_pct=3,
    ),
    TitleDef(
        "enchanter",
        "Заклинатель вещей",
        200,
        lambda c: int((c.meta_progress or {}).get("successful_enchants", 0)) >= 10,
        "10 успешных заточек",
        stat_int=5,
        xp_bonus_pct=2,
    ),
    TitleDef(
        "grand_explorer",
        "Великий исследователь",
        210,
        lambda c: int(c.highest_floor_reached or c.floor_number) >= 50,
        "достичь 50 этажа",
        stat_vit=5,
        xp_bonus_pct=3,
    ),
    TitleDef(
        "berserker",
        "Берсерк",
        220,
        lambda c: int(c.total_kills) >= 1000,
        "совершить 1000 убийств",
        stat_str=10,
        gold_bonus_pct=5,
    ),
    TitleDef(
        "shadow_dancer",
        "Танцующий в тени",
        230,
        lambda c: int((c.meta_progress or {}).get("dodged_attacks", 0)) >= 100,
        "уклониться от 100 атак",
        stat_dex=8,
        xp_bonus_pct=5,
    ),
    TitleDef(
        "merchant_prince",
        "Принц торговли",
        240,
        lambda c: int((c.meta_progress or {}).get("total_gold_from_sales", 0)) >= 250000,
        "продать предметов на 250 000 золота",
        gold_bonus_pct=10,
    ),
    TitleDef(
        "lucky_soul",
        "Удачливая душа",
        250,
        lambda c: int(c.stat_luck) >= 50,
        "базовая удача 50+",
        stat_luck=10,
    ),
    TitleDef(
        "workshop_forge_legend",
        "Король наковальни",
        252,
        lambda c: _workshop_tal(c, "top_blacksmith"),
        "топ-10 кузнецов (мастерская)",
        stat_str=2,
    ),
    TitleDef(
        "workshop_alchemy_legend",
        "Владыка эликсиров",
        253,
        lambda c: _workshop_tal(c, "top_alchemist"),
        "топ-10 алхимиков (мастерская)",
        stat_int=2,
    ),
    TitleDef(
        "workshop_jewel_legend",
        "Светильник оправ",
        254,
        lambda c: _workshop_tal(c, "top_jeweler"),
        "топ-10 ювелиров (мастерская)",
        stat_luck=2,
    ),
    TitleDef(
        "coliseum_champion_10",
        "Десятник Колизея",
        255,
        lambda c: 10 in _coliseum_defeated_ids(c),
        "победа над чемпионом Колизея (10-й боец)",
        xp_bonus_pct=3,
        stat_str=1,
    ),
    TitleDef(
        "coliseum_champion_20",
        "Властитель двадцатки",
        256,
        lambda c: 20 in _coliseum_defeated_ids(c),
        "победа над чемпионом Колизея (20-й боец)",
        xp_bonus_pct=3,
        gold_bonus_pct=2,
        stat_dex=1,
    ),
    TitleDef(
        "coliseum_champion_30",
        "Триумфатор тридцати",
        257,
        lambda c: 30 in _coliseum_defeated_ids(c),
        "победа над чемпионом Колизея (30-й боец)",
        xp_bonus_pct=4,
        stat_vit=2,
    ),
    TitleDef(
        "coliseum_champion_40",
        "Сокрушитель сорока",
        258,
        lambda c: 40 in _coliseum_defeated_ids(c),
        "победа над чемпионом Колизея (40-й боец)",
        xp_bonus_pct=4,
        gold_bonus_pct=3,
        stat_int=2,
    ),
    TitleDef(
        "coliseum_godslayer",
        "Богоубийца",
        259,
        lambda c: 50 in _coliseum_defeated_ids(c),
        "победа над финальным бойцом Колизея",
        gold_bonus_pct=5,
        xp_bonus_pct=5,
        stat_str=3,
    ),
    TitleDef(
        "coliseum_overlord",
        "Властелин Колизея",
        260,
        lambda c: len(_coliseum_defeated_ids(c)) >= 50,
        "победить всех 50 бойцов Колизея",
        gold_bonus_pct=8,
        xp_bonus_pct=8,
        stat_luck=5,
    ),
)

TITLE_BY_KEY: dict[str, TitleDef] = {t.key: t for t in ALL_TITLES}
