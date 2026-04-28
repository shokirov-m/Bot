"""
Справочник башни: 135 этажей, 13 зон, города 31/61/91, флаги NPC и боссов.
Тайная комната (15%) обрабатывается при входе на этаж на поздних шагах.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.data import floors as tower_data


@dataclass(frozen=True, slots=True)
class ZoneInfo:
    """Игровая зона башни."""

    key: str
    name: str
    emoji: str
    floor_from: int
    floor_to: int
    description: str
    floor_type: str = "normal"


@dataclass(frozen=True, slots=True)
class CityInfo:
    """Особый город-хаб."""

    floor: int
    name: str
    emoji: str
    theme_ru: str


_ZONE_INFO_FIELDS = {"key", "name", "emoji", "floor_from", "floor_to", "description", "floor_type"}


def _zone_info_from_raw(z: dict) -> ZoneInfo:
    """Создаёт ZoneInfo, игнорируя лишние поля (debuff, factions и т.п.)."""
    return ZoneInfo(**{k: v for k, v in z.items() if k in _ZONE_INFO_FIELDS})


# Десять зон + финал (этаж 100 отдельно в логике).
ZONES: tuple[ZoneInfo, ...] = tuple(_zone_info_from_raw(z) for z in tower_data.ZONES_RAW)

ZONE_FINAL_KEY: str = str(tower_data.ZONE_FINAL_RAW["key"])

ZONE_FINAL: ZoneInfo = _zone_info_from_raw(tower_data.ZONE_FINAL_RAW)

CITIES: dict[int, CityInfo] = {
    floor: CityInfo(**row) for floor, row in tower_data.CITIES_RAW.items()
}

# Быстрый переход через меню «Портал»
# Города-хабы (3/31/61/91/121), сюжетные этажи (8/10) и кратные 5 (5..135).
PORTAL_DESTINATION_FLOORS: tuple[int, ...] = tuple(
    sorted({3, 8, 10, 31, 61, 91, 121} | {f for f in range(5, 136, 5)}),
)

# Уникальные «комнаты» внутри зоны — циклически по этажу
EPITHETS: dict[str, tuple[str, ...]] = {
    "forest_beginnings": (
        "Тропа первых шагов",
        "Поляна затерянных факелов",
        "Роща шепчущих корней",
        "Брод у старого капища",
        "Тенистый перекрёсток",
        "Логово стаи",
        "Моховой каньон",
        "Склон ветров",
        "Заросший идол",
        "Кольцо древних камней",
    ),
    "rotten_swamps": (
        "Трясина шепота",
        "Озеро пузырящейся жижи",
        "Корни над водой",
        "Заброшенный тракт",
        "Туманная заводь",
        "Холм черепов",
        "Разрушенный мост",
        "Топь забвения",
        "Сгнивший курган",
        "Тропа гниющих фонарей",
    ),
    "shadow_caves": (
        "Зал отражений",
        "Ниша без эха",
        "Расщелина холодного ветра",
        "Колодец тьмы",
        "Галерея костяных шипов",
        "Площадка ритуала",
        "Коридор слепых летучих",
        "Пещера застывшего времени",
        "Провал шёпота",
        "Каменный зев",
    ),
    "icy_peaks": (
        "Ледяной карниз",
        "Ветреный перевал",
        "Расщелина синего льда",
        "Площадка вьюг",
        "Снежный мост",
        "Пещера вечной стужи",
        "Склон обмороженных статуй",
        "Ущелье колокольного льда",
        "Тропа кристаллов",
        "Высота без солнца",
    ),
    "desert_oblivion": (
        "Дюны зыбучие",
        "Оазис-призрак",
        "Руины часовни",
        "Рассохшийся акведук",
        "Площадь песков времени",
        "Каньон жара",
        "Колодец яда",
        "След скорпионов",
        "Каменная арка",
        "Бездна зеркального песка",
    ),
    "volcanic_ruins": (
        "Мост расплавленного камня",
        "Тропа искр",
        "Зал застывшей лавы",
        "Щель драконьего дыхания",
        "Площадка шлаков",
        "Кузница руин",
        "Склон обсидиана",
        "Кратер шипов",
        "Тоннель жара",
        "Алтарь пепла",
    ),
    "sky_citadel": (
        "Парящий двор",
        "Мост без опор",
        "Балкон гроз",
        "Зал перьев",
        "Кольцо ветров",
        "Арена облаков",
        "Свод из молний",
        "Терраса грифонов",
        "Коридор эха крыльев",
        "Шпиль без тени",
    ),
    "chaos_abyss": (
        "Вихрь искажений",
        "Платформа без гравитации",
        "Зал ломаных зеркал",
        "Провал в шёпот",
        "Кольцо демонов",
        "Мост из костей",
        "Площадка криков",
        "Щель между мирами",
        "Алтарь безликих",
        "Ступень бездны",
    ),
    "eternity_hall": (
        "Зал вечного света",
        "Коридор застывших молний",
        "Площадка часов",
        "Арка стражей",
        "Свод звёздного пепла",
        "Тронный периметр",
        "Кольцо печатей",
        "Мост к вершине",
        "Зал последних клятв",
        "Порог вечности",
    ),
    "jade_labyrinth": (
        "Зал нефритовых врат",
        "Коридор слепых стражей",
        "Ловушка трёх зеркал",
        "Тронный чертог мудрецов",
        "Переход сквозь туман",
        "Комната без теней",
        "Алтарь нефритового дракона",
        "Лабиринт без выхода",
        "Тайная библиотека",
        "Зал вечного нефрита",
    ),
    "frozen_wastes": (
        "Ледяная равнина без конца",
        "Поле обмороженных статуй",
        "Вьюжный перевал",
        "Пустошь скованных душ",
        "Кладбище экспедиций",
        "Провал в вечный лёд",
        "Тропа замёрзших слёз",
        "Алтарь стужи",
        "Снежный лабиринт",
        "Вершина смерти",
    ),
    "faction_war_plains": (
        "Поле первой битвы",
        "Лагерь эльфов",
        "Лагерь орков",
        "Линия фронта",
        "Руины нейтрального города",
        "Мост раздора",
        "Переправа крови",
        "Поляна переговоров",
        "Алтарь верности",
        "Трон победителя",
    ),
    ZONE_FINAL_KEY: (
        "Сердце башни",
        "Зал третьей фазы",
        "Трон ока",
        "Кольцо испытаний",
        "Площадка последнего выбора",
        "Свод без неба",
        "Мост к желанию",
        "Алтарь стража",
        "Периметр печати",
        "Врата ста",
    ),
}


def get_zone_for_floor(floor_number: int) -> ZoneInfo:
    """Возвращает зону по номеру этажа (1–135)."""
    if floor_number >= 135:
        return ZONE_FINAL
    if floor_number < 1:
        floor_number = 1
    for zone in ZONES:
        if zone.floor_from <= floor_number <= zone.floor_to:
            return zone
    return ZONES[-1]


def get_city_for_floor(floor_number: int) -> CityInfo | None:
    """Город-хаб или None."""
    return CITIES.get(floor_number)


def epithet_for_floor(zone: ZoneInfo, floor_number: int) -> str:
    """Название «комнаты» на этаже."""
    pool = EPITHETS.get(zone.key) or EPITHETS[ZONE_FINAL_KEY]
    idx = max(0, floor_number - 1) % len(pool)
    return pool[idx]


def has_quest_npc(floor_number: int) -> bool:
    """NPC с квестами на каждом 3-м этаже."""
    return floor_number > 0 and floor_number % 3 == 0


def has_trader(floor_number: int) -> bool:
    """Торговец на 3 этаже (лавка снаряжения) и на каждом 5-м."""
    if floor_number == 3:
        return True
    return floor_number > 0 and floor_number % 5 == 0


def is_major_boss_floor(floor_number: int) -> bool:
    """Сильный босс каждые 10 этажей (включая 100)."""
    return floor_number > 0 and floor_number % 10 == 0


def is_tower_milestone_boss_floor(floor_number: int) -> bool:
    """Вехи ×20: фаза «Ярость» у сильного босса (20/40/60/80/100/120/135)."""
    return floor_number in (20, 40, 60, 80, 100, 120, 135)


def is_mini_boss_floor(floor_number: int) -> bool:
    """Мини-босс на каждом 5-м, кроме этажей сильного босса."""
    return (
        floor_number > 0
        and floor_number % 5 == 0
        and not is_major_boss_floor(floor_number)
    )


SECRET_ROOM_CHANCE: float = 0.15


def get_zone_floor_type(floor_number: int) -> str:
    """Возвращает тип этажа: 'normal', 'survival', 'faction_war'."""
    zone = get_zone_for_floor(floor_number)
    raw: list[dict] = list(tower_data.ZONES_RAW)
    raw.append(tower_data.ZONE_FINAL_RAW)
    for z in raw:
        if z["key"] == zone.key:
            return str(z.get("floor_type", "normal"))
    return "normal"


def get_zone_raw(floor_number: int) -> dict:
    """Возвращает raw-словарь зоны для заданного этажа."""
    zone = get_zone_for_floor(floor_number)
    raw: list[dict] = list(tower_data.ZONES_RAW)
    raw.append(tower_data.ZONE_FINAL_RAW)
    for z in raw:
        if z["key"] == zone.key:
            return z
    return {}
