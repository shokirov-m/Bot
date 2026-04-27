"""
Справочник башни: 100 этажей, 10 зон, города 31/61/91, флаги NPC и боссов.
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


@dataclass(frozen=True, slots=True)
class CityInfo:
    """Особый город-хаб."""

    floor: int
    name: str
    emoji: str
    theme_ru: str


# Десять зон + финал (этаж 100 отдельно в логике).
ZONES: tuple[ZoneInfo, ...] = tuple(ZoneInfo(**z) for z in tower_data.ZONES_RAW)

ZONE_FINAL_KEY: str = str(tower_data.ZONE_FINAL_RAW["key"])

ZONE_FINAL: ZoneInfo = ZoneInfo(**tower_data.ZONE_FINAL_RAW)

CITIES: dict[int, CityInfo] = {
    floor: CityInfo(**row) for floor, row in tower_data.CITIES_RAW.items()
}

# Быстрый переход через меню «Портал»
# Города-хабы (3/31/61/91), сюжетные этажи (8/10) и кратные 5 (5..100).
PORTAL_DESTINATION_FLOORS: tuple[int, ...] = tuple(
    sorted({3, 8, 10, 31, 61, 91} | {f for f in range(5, 101, 5)}),
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
    """Возвращает зону по номеру этажа (1–100)."""
    if floor_number >= 100:
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
    """Вехи ×20: фаза «Ярость» у сильного босса (20 / 40 / 60 / 80 / 100)."""
    return floor_number in (20, 40, 60, 80, 100)


def is_mini_boss_floor(floor_number: int) -> bool:
    """Мини-босс на каждом 5-м, кроме этажей сильного босса."""
    return (
        floor_number > 0
        and floor_number % 5 == 0
        and not is_major_boss_floor(floor_number)
    )


SECRET_ROOM_CHANCE: float = 0.15
