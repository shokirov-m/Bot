"""
25 званий (отдельно от титулов): учебный бой на 1 этаже.
Пассив звания: meta.path_passive_key, суммируется с классом и глобальными пассивами.
"""

from __future__ import annotations

from dataclasses import dataclass

from db.models.character import Character

# (key, name_ru, sort, str, dex, int, vit, luck, passive_key, skill_ru, _, _) — последние два поля не используются
PATH_RANK_SPECS: tuple[
    tuple[str, str, int, int, int, int, int, int, str, str, int, int],
    ...,
] = (
    (
        "path_ideal",
        "Идеал наставника",
        200,
        1,
        1,
        0,
        0,
        0,
        "pp_balanced",
        "Равновесие: +1 к защите в бою и +1% к шансу крита.",
        1,
        1,
    ),
    (
        "path_whirl",
        "Вихрь клинка",
        201,
        2,
        0,
        0,
        0,
        0,
        "pp_crit3",
        "Жар стали: +3% к шансу критического удара.",
        0,
        2,
    ),
    (
        "path_swift",
        "Стремительный след",
        202,
        0,
        2,
        0,
        0,
        0,
        "pp_dodge3",
        "Лёгкие ступени: +3% к уклонению.",
        0,
        1,
    ),
    (
        "path_hail",
        "Град ударов",
        203,
        1,
        0,
        1,
        0,
        0,
        "pp_mag5",
        "Искра магии: +5% к силе магических навыков.",
        1,
        0,
    ),
    (
        "path_lightning",
        "Молниеносный выбор",
        204,
        1,
        1,
        0,
        0,
        0,
        "pp_mp2",
        "Второе дыхание: +2 MP каждый твой ход (пассивно).",
        0,
        2,
    ),
    (
        "path_steel",
        "Стальное равновесие",
        205,
        0,
        0,
        0,
        2,
        0,
        "pp_def4",
        "Каменная стойкость: +4 к защите в бою.",
        2,
        0,
    ),
    (
        "path_cold",
        "Холодный расчёт",
        206,
        0,
        0,
        2,
        0,
        0,
        "pp_mag8",
        "Ясный ум: +8% к силе магических навыков.",
        0,
        1,
    ),
    (
        "path_focus",
        "Сосредоточенный удар",
        207,
        2,
        0,
        0,
        0,
        0,
        "pp_crit2_def1",
        "Прицел: +2% крита и +1 к защите.",
        1,
        1,
    ),
    (
        "path_tactician",
        "Тактик поля",
        208,
        0,
        1,
        1,
        0,
        0,
        "pp_dodge2_mag4",
        "Гибкий разум: +2% уклонения, +4% к магии.",
        1,
        0,
    ),
    (
        "path_saver",
        "Эконом силы",
        209,
        0,
        0,
        1,
        1,
        0,
        "pp_mp3",
        "Запас энергии: +3 MP за ход.",
        0,
        2,
    ),
    (
        "path_tenacious",
        "Живучий натиск",
        210,
        1,
        0,
        0,
        1,
        0,
        "pp_def3_hp",
        "Тяжёлая поступь: +3 к защите.",
        2,
        0,
    ),
    (
        "path_grip",
        "Крепкая хватка",
        211,
        0,
        0,
        0,
        1,
        1,
        "pp_def2_luck",
        "Упорство: +2 к защите и +1% к криту.",
        0,
        1,
    ),
    (
        "path_steadfast",
        "Стойкий боец",
        212,
        0,
        1,
        0,
        1,
        0,
        "pp_dodge2_def2",
        "Перекат и щит: +2% уклонения и +2 к защите.",
        1,
        1,
    ),
    (
        "path_unshaken",
        "Непоколебимый",
        213,
        0,
        0,
        0,
        2,
        0,
        "pp_def3_mag3",
        "Стечение: +3 к защите и +3% к магии.",
        1,
        0,
    ),
    (
        "path_bone",
        "Кость башни",
        214,
        1,
        0,
        0,
        1,
        0,
        "pp_crit2_mp1",
        "Ритм боя: +2% крита и +1 MP за ход.",
        0,
        1,
    ),
    (
        "path_danger",
        "Опасный танец",
        215,
        0,
        2,
        0,
        0,
        0,
        "pp_dodge4",
        "Тень шагов: +4% к уклонению.",
        0,
        2,
    ),
    (
        "path_edge",
        "Грань выживания",
        216,
        0,
        0,
        0,
        1,
        1,
        "pp_def2_dodge2",
        "Инстинкт: +2 к защите и +2% уклонения.",
        2,
        0,
    ),
    (
        "path_bloodsteel",
        "Кровь и сталь",
        217,
        2,
        0,
        0,
        0,
        0,
        "pp_crit4",
        "Ярость клинка: +4% к шансу крита.",
        1,
        1,
    ),
    (
        "path_fury",
        "Упорство ярости",
        218,
        1,
        1,
        0,
        0,
        0,
        "pp_mix_phys",
        "Натиск: +2 к защите и +2% крита.",
        0,
        1,
    ),
    (
        "path_last",
        "Последний рубеж",
        219,
        0,
        0,
        0,
        0,
        2,
        "pp_luck_crit",
        "Удача башни: +2% крита и +2% уклонения.",
        1,
        1,
    ),
    (
        "path_spark",
        "Звёздная искра",
        220,
        0,
        0,
        2,
        0,
        0,
        "pp_mag6_mp1",
        "Поток: +6% к магии и +1 MP за ход.",
        0,
        2,
    ),
    (
        "path_ether",
        "Эфирный жест",
        221,
        0,
        1,
        1,
        0,
        0,
        "pp_mag5_dodge2",
        "Лёгкая магия: +5% к магии и +2% уклонения.",
        1,
        0,
    ),
    (
        "path_foresight",
        "Дух предвидения",
        222,
        0,
        0,
        1,
        0,
        1,
        "pp_mag4_crit2",
        "Прозрение: +4% к магии и +2% крита.",
        0,
        1,
    ),
    (
        "path_shadow",
        "Тень первого шага",
        223,
        0,
        1,
        0,
        0,
        1,
        "pp_dodge3_crit1",
        "Скрытность: +3% уклонения и +1% крита.",
        1,
        1,
    ),
    (
        "path_wanderer",
        "Судьба странника",
        224,
        1,
        0,
        0,
        0,
        1,
        "pp_allround",
        "Универсал: +1 ко всем пассивным модификаторам боя (защита, крит, уклонение, магия).",
        2,
        1,
    ),
)

PATH_PASSIVE_DELTAS: dict[str, dict[str, float | int]] = {
    "pp_balanced": {"def_bonus": 1.0, "crit_bonus": 0.01},
    "pp_crit3": {"crit_bonus": 0.03},
    "pp_dodge3": {"dodge_bonus": 0.03},
    "pp_mag5": {"mag_bonus_percent": 5},
    "pp_mp2": {"mp_regen_turn": 2},
    "pp_def4": {"def_bonus": 4.0},
    "pp_mag8": {"mag_bonus_percent": 8},
    "pp_crit2_def1": {"crit_bonus": 0.02, "def_bonus": 1.0},
    "pp_dodge2_mag4": {"dodge_bonus": 0.02, "mag_bonus_percent": 4},
    "pp_mp3": {"mp_regen_turn": 3},
    "pp_def3_hp": {"def_bonus": 3.0},
    "pp_def2_luck": {"def_bonus": 2.0, "crit_bonus": 0.01},
    "pp_dodge2_def2": {"dodge_bonus": 0.02, "def_bonus": 2.0},
    "pp_def3_mag3": {"def_bonus": 3.0, "mag_bonus_percent": 3},
    "pp_crit2_mp1": {"crit_bonus": 0.02, "mp_regen_turn": 1},
    "pp_dodge4": {"dodge_bonus": 0.04},
    "pp_def2_dodge2": {"def_bonus": 2.0, "dodge_bonus": 0.02},
    "pp_crit4": {"crit_bonus": 0.04},
    "pp_mix_phys": {"def_bonus": 2.0, "crit_bonus": 0.02},
    "pp_luck_crit": {"crit_bonus": 0.02, "dodge_bonus": 0.02},
    "pp_mag6_mp1": {"mag_bonus_percent": 6, "mp_regen_turn": 1},
    "pp_mag5_dodge2": {"mag_bonus_percent": 5, "dodge_bonus": 0.02},
    "pp_mag4_crit2": {"mag_bonus_percent": 4, "crit_bonus": 0.02},
    "pp_dodge3_crit1": {"dodge_bonus": 0.03, "crit_bonus": 0.01},
    "pp_allround": {"def_bonus": 1.0, "crit_bonus": 0.01, "dodge_bonus": 0.01, "mag_bonus_percent": 1},
}

PATH_RANK_KEYS: tuple[str, ...] = tuple(s[0] for s in PATH_RANK_SPECS)


@dataclass(frozen=True, slots=True)
class PathRankDef:
    key: str
    name_ru: str
    sort: int
    stat_str: int
    stat_dex: int
    stat_int: int
    stat_vit: int
    stat_luck: int
    passive_key: str
    skill_ru: str


PATH_RANK_BY_KEY: dict[str, PathRankDef] = {
    s[0]: PathRankDef(
        s[0],
        s[1],
        s[2],
        s[3],
        s[4],
        s[5],
        s[6],
        s[7],
        s[8],
        s[9],
    )
    for s in PATH_RANK_SPECS
}


def path_rank_key_from_meta(meta: dict | None) -> str:
    if not meta:
        return ""
    return str(meta.get("path_rank_key") or meta.get("tutorial_path_title") or "")


def path_rank_name_ru(character: Character) -> str | None:
    """Текущее звание или None."""
    k = path_rank_key_from_meta(character.meta_progress)
    if not k:
        return None
    r = PATH_RANK_BY_KEY.get(k)
    return r.name_ru if r else None


PATH_RANK_LORE: dict[str, str] = {
    "path_ideal": "твоя манера учебного боя — выверенная, без лишних движений",
    "path_whirl": "твоя манера учебного боя — стремительная и решительная",
    "path_swift": "твоя манера учебного боя — лёгкая и подвижная",
    "path_hail": "твоя манера учебного боя — давить шквалом ударов",
    "path_lightning": "твоя манера учебного боя — реагировать раньше, чем враг замахнётся",
    "path_steel": "твоя манера учебного боя — стоять как стена и принимать удары",
    "path_cold": "твоя манера учебного боя — продумывать каждый ход",
    "path_focus": "твоя манера учебного боя — точечный, прицельный удар",
    "path_tactician": "твоя манера учебного боя — гибкий план и быстрая реакция",
    "path_saver": "твоя манера учебного боя — экономить силы и беречь дыхание",
    "path_tenacious": "твоя манера учебного боя — упрямый натиск без шага назад",
    "path_grip": "твоя манера учебного боя — держаться до последнего",
    "path_steadfast": "твоя манера учебного боя — спокойная стойкость в обороне",
    "path_unshaken": "твоя манера учебного боя — несдвигаемая сила",
    "path_bone": "твоя манера учебного боя — ритмичная и выносливая",
    "path_danger": "твоя манера учебного боя — рисковать на грани уклонения",
    "path_edge": "твоя манера учебного боя — выживать в шаге от поражения",
    "path_bloodsteel": "твоя манера учебного боя — давить силой и яростью",
    "path_fury": "твоя манера учебного боя — прямой и упрямый натиск",
    "path_last": "твоя манера учебного боя — переломить бой удачей",
    "path_spark": "твоя манера учебного боя — бить вспышками магии",
    "path_ether": "твоя манера учебного боя — лёгкое касание силы",
    "path_foresight": "твоя манера учебного боя — предугадывать ход врага",
    "path_shadow": "твоя манера учебного боя — заходить с тени",
    "path_wanderer": "твоя манера учебного боя — пробовать всё понемногу",
}


def path_rank_lore(character: Character) -> str | None:
    """Лоровое описание звания (без эффектов)."""
    k = path_rank_key_from_meta(character.meta_progress)
    if not k:
        return None
    return PATH_RANK_LORE.get(k)


def _speed_bin(player_rounds: int) -> int:
    t = max(1, int(player_rounds))
    if t <= 3:
        return 0
    if t <= 6:
        return 1
    if t <= 10:
        return 2
    if t <= 15:
        return 3
    return 4


def _survival_bin(hp: int, hp_max: int) -> int:
    mx = max(1, int(hp_max))
    pct = 100.0 * float(hp) / float(mx)
    if pct >= 90:
        return 0
    if pct >= 70:
        return 1
    if pct >= 50:
        return 2
    if pct >= 30:
        return 3
    return 4


def path_rank_key_from_battle(player_rounds: int, hp: int, hp_max: int, used_skill: bool) -> str:
    """Один из 25 ключей звания по исходу учебного боя."""
    base = _speed_bin(player_rounds) * 5 + _survival_bin(hp, hp_max)
    idx = (base + (7 if used_skill else 0)) % 25
    return PATH_RANK_KEYS[idx]


def path_passive_delta(meta: dict | None) -> dict[str, float | int]:
    """Дельта пассивов из meta.path_passive_key (после обучения)."""
    if not meta:
        return {}
    pk = meta.get("path_passive_key")
    if not pk or not isinstance(pk, str):
        return {}
    return dict(PATH_PASSIVE_DELTAS.get(pk, {}))


def merge_passive_row(
    base: dict[str, float | int],
    extra: dict[str, float | int],
) -> dict[str, float | int]:
    out = dict(base)
    for k, v in extra.items():
        if k == "mp_regen_turn":
            out[k] = int(out.get(k, 0)) + int(v)
        elif k == "mag_bonus_percent":
            out[k] = int(out.get(k, 0)) + int(v)
        else:
            out[k] = float(out.get(k, 0)) + float(v)
    return out
