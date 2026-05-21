"""
Каталог вариантов испытаний: разный лор и параметры, без одинакового цикла.

~60% ярусов получают вариант из пула зоны (детерминированный «рандом» по номеру этажа).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TrialVariant:
    id: str
    trial_type: str
    title_ru: str
    blurb_ru: str
    defense_mode: str = ""
    grounds_delta: int = 0
    wins_delta: int = 0
    waves_delta: int = 0
    perim_delta: int = 0
    required_pct_delta: int = 0
    death_reset: str = ""
    hardcore: bool | None = None
    ground_prefix: str = ""
    targets: dict[str, int] = field(default_factory=dict)


def _v(
    vid: str,
    ttype: str,
    title: str,
    blurb: str,
    **kw: Any,
) -> TrialVariant:
    targets = dict(kw.pop("targets", {}) or {})
    return TrialVariant(
        id=vid,
        trial_type=ttype,
        title_ru=title,
        blurb_ru=blurb,
        defense_mode=str(kw.pop("defense_mode", "") or ""),
        grounds_delta=int(kw.pop("grounds_delta", 0) or 0),
        wins_delta=int(kw.pop("wins_delta", 0) or 0),
        waves_delta=int(kw.pop("waves_delta", 0) or 0),
        perim_delta=int(kw.pop("perim_delta", 0) or 0),
        required_pct_delta=int(kw.pop("required_pct_delta", 0) or 0),
        death_reset=str(kw.pop("death_reset", "") or ""),
        hardcore=kw.pop("hardcore", None),
        ground_prefix=str(kw.pop("ground_prefix", "") or ""),
        targets=targets,
    )


# --- Лес начал ---
_FOREST: tuple[TrialVariant, ...] = (
    _v(
        "hunt_wolf_alpha",
        "hunt",
        "Охота на вожака стаи",
        "Стая устроила засаду у старого моста. Выслеживай альфу по угодьям.",
        ground_prefix="🐺",
        targets={"contracts": 2, "trophies": 6},
    ),
    _v(
        "search_lost_convoy",
        "search",
        "Поиск пропавшего обоза",
        "Следы ведут в чащу — собери улики в секторах, пока не стёр их дождь.",
        ground_prefix="🔍",
        targets={"clues": 8},
    ),
    _v(
        "rescue_woodcutters",
        "rescue",
        "Спасение лесорубов",
        "Бригаду затянуло в чащу теневых корней. Освободи лагеря пленных.",
        ground_prefix="⛓️",
        targets={"prisoners": 3, "camps": 5},
    ),
    _v(
        "capture_goblin_nets",
        "capture",
        "Захват сетей гоблинов",
        "Гоблины натянули сети на тропы — отбей узлы по периметру чащи.",
        ground_prefix="📍",
        targets={"nodes": 4},
    ),
    _v(
        "defense_mill",
        "defense",
        "Оборона мельницы",
        "Мельница — последний оплот деревни. Удержи рубежи, не пусти тварей к жерновам.",
        ground_prefix="🌾",
        grounds_delta=-1,
    ),
    _v(
        "defense_hub_forest_camp",
        "defense",
        "Оборона лагеря ополчения",
        "Лагерь новобранцев осаждают. Волны штурма, затем зачисти периметр леса.",
        defense_mode="hub",
        ground_prefix="🛡️",
        waves_delta=-2,
        perim_delta=0,
    ),
    _v(
        "rescue_unknown_voice",
        "rescue",
        "Голос из тумана",
        "Кто-то зовёт из чащи — пленники неизвестны даже старосте. Спаси, пока не замолкли.",
        ground_prefix="❓",
        death_reset="phase",
        targets={"prisoners": 2, "camps": 4},
    ),
)

# --- Болота ---
_SWAMP: tuple[TrialVariant, ...] = (
    _v(
        "hunt_leech_queen",
        "hunt",
        "Охота на матку пиявок",
        "Токсичные пиявки размножились у кургана. Охота на элитных особей.",
        ground_prefix="🪱",
        targets={"contracts": 3, "trophies": 10},
    ),
    _v(
        "search_sunken_relic",
        "search",
        "Поиск реликвии в трясине",
        "В болоте утонил обоз с реликвией — улики на островках сгнивают.",
        ground_prefix="🔍",
        targets={"clues": 10},
    ),
    _v(
        "capture_bog_beacons",
        "capture",
        "Захват маяков топи",
        "Зажги контроль узлов — пока не погасли факелы сами.",
        ground_prefix="📍",
        targets={"nodes": 5},
    ),
    _v(
        "rescue_prisoner_barge",
        "rescue",
        "Спасение с баржи-тюрьмы",
        "Полузатонувшая баржа: пленники в трюмах, стража мутировала.",
        ground_prefix="⛓️",
        targets={"prisoners": 4, "camps": 6},
    ),
    _v(
        "defense_hub_swamp_dam",
        "defense",
        "Оборона плотины",
        "Держи плотину: волны тварей идут с трёх сторон топи.",
        defense_mode="hub",
        ground_prefix="🛡️",
    ),
    _v(
        "defense_herb_garden",
        "defense",
        "Оборона сада травника",
        "Сад единственный источник противоядия — не отдай его жиже.",
        ground_prefix="🌿",
    ),
)

# --- Пещеры ---
_CAVES: tuple[TrialVariant, ...] = (
    _v(
        "search_echo_map",
        "search",
        "Поиск карты эха",
        "Каменные стены повторяют шаги врага — найди узлы резонанса.",
        ground_prefix="🔍",
        targets={"clues": 9},
    ),
    _v(
        "hunt_bat_matron",
        "hunt",
        "Охота на матрону летучих",
        "Рой сменил матку — без неё стая рассыплется.",
        ground_prefix="🦇",
        targets={"contracts": 2, "trophies": 8},
    ),
    _v(
        "rescue_cage_miners",
        "rescue",
        "Спасение из клеток шахты",
        "Шахтёров заперли в клетках на глубине — ключи у элит.",
        ground_prefix="⛓️",
        targets={"prisoners": 5, "camps": 7},
    ),
    _v(
        "capture_crystal_nodes",
        "capture",
        "Захват кристальных узлов",
        "Узлы питают портал — удержи их от теневых культистов.",
        ground_prefix="📍",
        targets={"nodes": 4},
    ),
    _v(
        "defense_hub_lamp_crypt",
        "defense",
        "Оборона лампадария",
        "Лампы гаснут — волны тьмы. Периметр святилища, затем босс.",
        defense_mode="hub",
        ground_prefix="🛡️",
    ),
    _v(
        "rescue_unknown_depths",
        "rescue",
        "Неведомые из глубины",
        "Из расщелины тянут руки — кто пленники, неясно. Спаси или запечатай.",
        ground_prefix="❓",
        targets={"prisoners": 3, "camps": 5},
    ),
)

# --- Ледяные пики ---
_ICE: tuple[TrialVariant, ...] = (
    _v(
        "hunt_yeti_trace",
        "hunt",
        "Охота на след йети",
        "След ведёт через перевалы — контракты викингов ждут трофея.",
        ground_prefix="❄️",
        targets={"contracts": 3, "trophies": 12},
    ),
    _v(
        "search_frozen_banner",
        "search",
        "Поиск знамени легиона",
        "Знамя замёрзло в леднике — улики в заснеженных нишах.",
        ground_prefix="🔍",
        targets={"clues": 11},
    ),
    _v(
        "defense_hub_frost_gate",
        "defense",
        "Оборона морозных ворот",
        "Ворота Айронфолла — волны штурма с перевала.",
        defense_mode="hub",
        ground_prefix="🛡️",
    ),
    _v(
        "defense_bridge_chain",
        "defense",
        "Оборона цепного моста",
        "Мост рвут ледяные элементали — держи сектора до ремонта.",
        ground_prefix="🌉",
    ),
    _v(
        "capture_hot_springs",
        "capture",
        "Захват горячих источников",
        "Источники — единственное тепло. Отбей узлы у купальщиков-мутантов.",
        ground_prefix="📍",
        targets={"nodes": 4},
    ),
    _v(
        "rescue_avalanche_camp",
        "rescue",
        "Спасение после лавины",
        "Лагерь занесло — выкопай пленных до следующего схода.",
        ground_prefix="⛓️",
        targets={"prisoners": 4, "camps": 8},
    ),
)

# --- Пустыня ---
_DESERT: tuple[TrialVariant, ...] = (
    _v(
        "search_mirage_clues",
        "search",
        "Поиск улик миража",
        "Оазисы-призраки оставляют ложные следы — отличай истинные улики.",
        ground_prefix="🏜️",
        targets={"clues": 12},
    ),
    _v(
        "hunt_scorpion_khan",
        "hunt",
        "Охота на хан скорпионов",
        "Хан ядовит — без трофея караваны не пойдут.",
        ground_prefix="🦂",
        targets={"contracts": 3, "trophies": 14},
    ),
    _v(
        "capture_well_nodes",
        "capture",
        "Захват колодцев",
        "Колодцы отравлены — верни узлы под контроль каравана.",
        ground_prefix="📍",
        targets={"nodes": 5},
    ),
    _v(
        "rescue_sand_prison",
        "rescue",
        "Спасение из песчаной тюрьмы",
        "Пленники в яме под руинами — копай лагеря до заката.",
        ground_prefix="⛓️",
        targets={"prisoners": 5, "camps": 9},
    ),
    _v(
        "defense_hub_caravan_ring",
        "defense",
        "Оборона караванного кольца",
        "Караван в кольце барханов — волны рейдеров с дюн.",
        defense_mode="hub",
        ground_prefix="🛡️",
    ),
    _v(
        "rescue_lost_in_storm",
        "rescue",
        "Заблудшие в буре",
        "Имена стёрты песком — спаси кого ещё можно найти.",
        ground_prefix="❓",
        death_reset="phase",
        targets={"prisoners": 3, "camps": 6},
    ),
)

# --- Вулканы ---
_VOLCANO: tuple[TrialVariant, ...] = (
    _v(
        "defense_hub_slag_fort",
        "defense",
        "Оборона шлакового форта",
        "Форт у лавы — волны элементалей, периметр плавилен.",
        defense_mode="hub",
        ground_prefix="🛡️",
    ),
    _v(
        "defense_ember_convoy",
        "defense",
        "Оборона обоза угля",
        "Обоз горит без огня — защити сектора погрузки.",
        ground_prefix="🔥",
    ),
    _v(
        "hunt_slag_beast",
        "hunt",
        "Охота на зверя шлака",
        "Зверь пожирает руду — контракты кузнецов Эмберхолла.",
        ground_prefix="🌋",
        targets={"contracts": 4, "trophies": 15},
    ),
    _v(
        "capture_magma_valves",
        "capture",
        "Захват клапанов магмы",
        "Клапаны сходят с ума — удержи узлы до остывания.",
        ground_prefix="📍",
        targets={"nodes": 5},
    ),
    _v(
        "search_ash_ledger",
        "search",
        "Поиск книги пепла",
        "Книга записей утонула в пепле — улики в залах руин.",
        ground_prefix="🔍",
        targets={"clues": 10},
    ),
    _v(
        "rescue_chain_gangs",
        "rescue",
        "Спасение из цепей бандитов",
        "Бандиты держат пленников у раскалённых клетей.",
        ground_prefix="⛓️",
        targets={"prisoners": 4, "camps": 7},
    ),
)

# --- Бездна ---
_CHAOS: tuple[TrialVariant, ...] = (
    _v(
        "hunt_demon_herald",
        "hunt",
        "Охота на вестника демонов",
        "Вестник зовёт вихри — охота по искажённым угодьям.",
        ground_prefix="👹",
        hardcore=True,
        targets={"contracts": 4, "trophies": 18},
    ),
    _v(
        "search_void_runes",
        "search",
        "Поиск рун бездны",
        "Руны плывут в воздухе — собери улики, пока не исчезли.",
        ground_prefix="🔍",
        targets={"clues": 14},
    ),
    _v(
        "rescue_mind_prison",
        "rescue",
        "Спасение из тюрьмы разума",
        "Пленники в клетках иллюзий — лагеря не на карте.",
        ground_prefix="⛓️",
        death_reset="full_trial",
        targets={"prisoners": 5, "camps": 10},
    ),
    _v(
        "rescue_unknown_rift",
        "rescue",
        "Никого не знают",
        "Из разлома выходят фигуры без имён — спаси или изгони.",
        ground_prefix="❓",
        death_reset="full_trial",
        targets={"prisoners": 3, "camps": 6},
    ),
    _v(
        "defense_hub_anchor_spire",
        "defense",
        "Оборона якоря реальности",
        "Якорь держит этаж — волны демонов бьют в лагерь магов.",
        defense_mode="hub",
        ground_prefix="🛡️",
        waves_delta=2,
    ),
    _v(
        "capture_rift_nodes",
        "capture",
        "Захват узлов разлома",
        "Узлы скачут между измерениями — закрепи их победами.",
        ground_prefix="📍",
        targets={"nodes": 6},
    ),
)

# --- Зал вечности ---
_ETERNITY: tuple[TrialVariant, ...] = (
    _v(
        "defense_hub_star_gate",
        "defense",
        "Оборона звёздных врат",
        "Врата Этерниса — финальные волны, периметр зала.",
        defense_mode="hub",
        ground_prefix="🛡️",
        waves_delta=4,
        perim_delta=1,
        required_pct_delta=2,
    ),
    _v(
        "search_oath_tablets",
        "search",
        "Поиск скрижалей клятв",
        "Скрижали рассыпаны по залу — улики ведут к стражу.",
        ground_prefix="🔍",
        targets={"clues": 16},
        hardcore=True,
    ),
    _v(
        "hunt_archon_hunt",
        "hunt",
        "Охота на архонта",
        "Архонт судит смертных — контракты гарнизона.",
        ground_prefix="⚡",
        hardcore=True,
        targets={"contracts": 5, "trophies": 20},
    ),
    _v(
        "rescue_time_cells",
        "rescue",
        "Спасение из клеток времени",
        "Пленники застыли в ячейках — разбуди лагеря до вечности.",
        ground_prefix="⛓️",
        death_reset="full_trial",
        targets={"prisoners": 6, "camps": 12},
    ),
    _v(
        "capture_seal_pillars",
        "capture",
        "Захват столпов печати",
        "Печати трещат — удержи узлы столпов.",
        ground_prefix="📍",
        targets={"nodes": 6},
    ),
    _v(
        "defense_throne_approach",
        "defense",
        "Оборона подступов к трону",
        "Подступы к трону — сектора света, не отступай.",
        ground_prefix="👑",
        hardcore=True,
    ),
)

_UNIVERSAL: tuple[TrialVariant, ...] = (
    _v(
        "hunt_wandering_elite",
        "hunt",
        "Охота на бродячую элиту",
        "Элита без логова — выслеживай по угодьям башни.",
        ground_prefix="🎯",
        targets={"contracts": 2, "trophies": 8},
    ),
    _v(
        "search_tower_whisper",
        "search",
        "Шёпот башни",
        "Башня шепчет подсказки — найди, что она скрывает на этом ярусе.",
        ground_prefix="🔮",
        targets={"clues": 7},
    ),
    _v(
        "rescue_nameless",
        "rescue",
        "Безымянные пленники",
        "Никто не помнит, кто они. Спаси лагеря, пока память не стёрлась.",
        ground_prefix="❓",
        targets={"prisoners": 3, "camps": 5},
    ),
    _v(
        "capture_stray_nodes",
        "capture",
        "Блуждающие узлы",
        "Узлы силы сместились — верни контроль победами.",
        ground_prefix="📍",
        targets={"nodes": 4},
    ),
    _v(
        "defense_last_light",
        "defense",
        "Последний свет",
        "Факелы гаснут — оборона рубежей, иначе ярус поглотит тьма.",
        ground_prefix="🕯️",
    ),
)

VARIANTS_BY_ZONE: dict[str, tuple[TrialVariant, ...]] = {
    "forest_beginnings": _FOREST,
    "rotten_swamps": _SWAMP,
    "shadow_caves": _CAVES,
    "icy_peaks": _ICE,
    "desert_oblivion": _DESERT,
    "volcanic_ruins": _VOLCANO,
    "chaos_abyss": _CHAOS,
    "eternity_hall": _ETERNITY,
}

ALL_VARIANTS: tuple[TrialVariant, ...] = (
    _FOREST + _SWAMP + _CAVES + _ICE + _DESERT + _VOLCANO + _CHAOS + _ETERNITY + _UNIVERSAL
)

VARIANT_BY_ID: dict[str, TrialVariant] = {v.id: v for v in ALL_VARIANTS}
