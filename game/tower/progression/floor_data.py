"""
Справочник башни: зоны 1–99, города между этажами (0/30/60/90). Высота башни неизвестна.
Контент зон-испытаний: content/data/packs/zones/
"""

from __future__ import annotations

from dataclasses import dataclass

from db.models.character import Character
from game.crafting.workshop_constants import WORKSHOP_ORDERS_HUB_FLOOR as _WSP_HUB_FLOOR
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
    """Город-хаб в зазоре между боевыми ярусами (не занимает номер этажа)."""

    key: str
    after_floor: int
    name: str
    emoji: str
    theme_ru: str

    @property
    def floor(self) -> int:
        """Якорь для callback кузницы/таверны (legacy-имя поля)."""
        return self.after_floor


_ZONE_INFO_FIELDS = {"key", "name", "emoji", "floor_from", "floor_to", "description", "floor_type"}


def _zone_info_from_raw(z: dict) -> ZoneInfo:
    """Создаёт ZoneInfo, игнорируя лишние поля (debuff, factions и т.п.)."""
    return ZoneInfo(**{k: v for k, v in z.items() if k in _ZONE_INFO_FIELDS})


def _city_info_from_raw(row: dict) -> CityInfo:
    anchor = int(row.get("after_floor", row.get("floor", 0)))
    return CityInfo(
        key=str(row.get("key") or f"city_{anchor}"),
        after_floor=anchor,
        name=str(row["name"]),
        emoji=str(row["emoji"]),
        theme_ru=str(row.get("theme_ru") or ""),
    )


ZONES: tuple[ZoneInfo, ...] = tuple(_zone_info_from_raw(z) for z in tower_data.ZONES_RAW)

_raw_final = tower_data.ZONE_FINAL_RAW
if _raw_final:
    ZONE_FINAL_KEY: str = str(_raw_final["key"])
    ZONE_FINAL: ZoneInfo = _zone_info_from_raw(_raw_final)
else:
    ZONE_FINAL_KEY = "eternity_hall"
    ZONE_FINAL = ZONES[-1]

# Потолок известной карты (этажи 101+ сняты)
KNOWN_MAX_FLOOR = 99

CITIES: dict[int, CityInfo] = {
    int(k): _city_info_from_raw(row) for k, row in tower_data.CITIES_RAW.items()
}
# Город игроков (хаб ремесленных заказов) — отдельный боевой этаж мастерской
if _WSP_HUB_FLOOR not in CITIES:
    CITIES[_WSP_HUB_FLOOR] = CityInfo(
        key="workshop_union",
        after_floor=_WSP_HUB_FLOOR,
        name="Свод союза",
        emoji="🏙",
        theme_ru="Город игроков: общий хаб, ремесло и заказы мастерских.",
    )

# Быстрый переход через меню «Портал»
PORTAL_DESTINATION_FLOORS: tuple[int, ...] = tuple(
    sorted({1, 8, 10, 31, 60, 61, 91} | {f for f in range(5, KNOWN_MAX_FLOOR + 1, 5)}),
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
        "Площадка песков времени",
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
    "blood_spire": (
        "Внешние стены Шпиля",
        "Кладбище первого колокола",
        "Двор с залитой луной",
        "Балконы без света",
        "Склеп баронов",
        "Галерея клыков",
        "Тронный коридор",
        "Алтарь сгустившейся крови",
        "Тюремный ярус",
        "Врата Князя",
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
}


def get_zone_for_floor(floor_number: int) -> ZoneInfo:
    """Возвращает зону по номеру этажа (1–KNOWN_MAX_FLOOR)."""
    if floor_number < 1:
        floor_number = 1
    if floor_number > KNOWN_MAX_FLOOR:
        floor_number = KNOWN_MAX_FLOOR
    for zone in ZONES:
        if zone.floor_from <= floor_number <= zone.floor_to:
            return zone
    return ZONES[-1]


def _city_unlocked(highest_reached: int, city: CityInfo) -> bool:
    return int(highest_reached) > int(city.after_floor)


def get_city_for_floor(
    floor_number: int,
    *,
    highest_reached: int | None = None,
) -> CityInfo | None:
    """
    Ближайший доступный город-хаб с боевого яруса.
    Город стоит между after_floor и after_floor+1 (не на боевом номере).
    """
    hi = int(highest_reached if highest_reached is not None else floor_number)
    best: CityInfo | None = None
    for city in sorted(CITIES.values(), key=lambda c: c.after_floor):
        if _city_unlocked(hi, city):
            best = city
    return best


def city_service_anchor_for_character(character: Character) -> int | None:
    """Якорь города для callback кузницы/таверны/экономики."""
    from game.locations import hub_floors as hf

    n = int(character.floor_number)
    if hf.is_city_hub_floor(n):
        return hf.city_anchor_from_hub_floor(n)
    city = get_city_for_floor(
        n,
        highest_reached=int(character.highest_floor_reached),
    )
    return city.after_floor if city else None


def city_service_floor_ok(character: Character, floor_key: int) -> bool:
    """Проверка floor_key в callback города (якорь, не боевой этаж)."""
    anchor = city_service_anchor_for_character(character)
    return anchor is not None and int(floor_key) == int(anchor)


def city_button_label(floor_number: int, *, highest_reached: int | None = None) -> str | None:
    city = get_city_for_floor(floor_number, highest_reached=highest_reached)
    if city is None:
        return None
    gap = f"{city.after_floor}→{city.after_floor + 1}"
    return f"{city.emoji} {city.name} ({gap})"


def epithet_for_floor(zone: ZoneInfo, floor_number: int) -> str:
    """Название «комнаты» на этаже."""
    pool = EPITHETS.get(zone.key) or EPITHETS[ZONE_FINAL_KEY]
    idx = max(0, floor_number - 1) % len(pool)
    return pool[idx]


def has_quest_npc(floor_number: int) -> bool:
    """NPC с квестами на каждом 3-м этаже."""
    return floor_number > 0 and floor_number % 3 == 0


def has_trader(floor_number: int) -> bool:
    """Торговец на 1 этаже (лавка снаряжения) и на каждом 5-м."""
    if floor_number == 1:
        return True
    return floor_number > 0 and floor_number % 5 == 0


def is_major_boss_floor(floor_number: int) -> bool:
    """Сильный босс каждые 10 этажей (включая 100)."""
    return floor_number > 0 and floor_number % 10 == 0


def is_tower_milestone_boss_floor(floor_number: int) -> bool:
    """Вехи ×20: фаза «Ярость» у сильного босса."""
    return floor_number in (20, 40, 60, 80)


def is_mini_boss_floor(floor_number: int) -> bool:
    """Мини-босс на каждом 5-м, кроме этажей сильного босса."""
    return (
        floor_number > 0
        and floor_number % 5 == 0
        and not is_major_boss_floor(floor_number)
    )


SECRET_ROOM_CHANCE: float = 0.15


def format_floor_label(floor_number: int) -> str:
    """Подпись этажа без раскрытия высоты башни."""
    return f"🗼 <b>ЭТАЖ {int(floor_number)}</b>"


def get_zone_floor_type(floor_number: int) -> str:
    """Возвращает тип этажа: 'normal', 'survival', 'faction_war'."""
    zone = get_zone_for_floor(floor_number)
    raw: list[dict] = list(tower_data.ZONES_RAW)
    if tower_data.ZONE_FINAL_RAW:
        raw.append(tower_data.ZONE_FINAL_RAW)
    for z in raw:
        if z["key"] == zone.key:
            return str(z.get("floor_type", "normal"))
    return "normal"


def get_zone_raw(floor_number: int) -> dict:
    """Возвращает raw-словарь зоны для заданного этажа."""
    zone = get_zone_for_floor(floor_number)
    raw: list[dict] = list(tower_data.ZONES_RAW)
    if tower_data.ZONE_FINAL_RAW:
        raw.append(tower_data.ZONE_FINAL_RAW)
    for z in raw:
        if z["key"] == zone.key:
            return z
    return {}
