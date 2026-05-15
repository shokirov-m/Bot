"""
Города-хабы башни: лор, ключи для квестов/меты, привязка к floor_data.

Источник правды по этажу и имени — `game.floors.floor_data` (CITIES, CityInfo).
Здесь — расширенные тексты и стабильные ключи для цепочек «город → NPC → квесты».
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from game.floors import floor_data
from game.floors.floor_data import CityInfo


@dataclass(frozen=True, slots=True)
class CityHubDef:
    """Расширенное описание хаба (удержание, атмосфера, сервисы)."""

    key: str
    """Стабильный ключ: quiet_brook, ironfall, emberhall, eternis."""

    tagline: str
    """Одна строка под названием города."""

    welcome_html: str
    """2–4 абзаца HTML (без внешних <p>, используем <b>/<i>)."""

    retention_note: str
    """Зачем игроку возвращаться (крючок удержания)."""

    npc_guard_title: str
    """Кто выдаёт городское поручение (для текстов квестов)."""

    economy_blurb: str
    """Кратко про лотерею / ростовщика / сейф в этом городе."""


# Ключ хаба по этажу (для meta_progress, аналитики, будущих NPC).
HUB_KEY_BY_FLOOR: dict[int, str] = {
    3: "quiet_brook",
    31: "ironfall",
    61: "emberhall",
    91: "eternis",
}

def _build_city_hubs() -> dict[int, CityHubDef]:
    try:
        from game.data.catalogs.cities_catalog import catalog_city_hubs

        cat = catalog_city_hubs()
        if cat:
            return cat
    except Exception:
        pass
    return _default_city_hubs()


def _default_city_hubs() -> dict[int, CityHubDef]:
    return {
    3: CityHubDef(
        key="quiet_brook",
        tagline="Первый очаг у подножия — здесь учатся не сдаваться.",
        welcome_html=(
            "Тихий Ручей — не город, а <b>деревня ополчения</b>: низкие дома, дым из очагов, "
            "на стене — карта заросших троп к башне. Староста держит связь с нижними кольцами "
            "и не пускает новичков вверх без хотя бы базовой снаряги.\n"
            "<i>Здесь впервые открываются кузница, таверна и лавка — шаблон всей дальнейшей дороги.</i>"
        ),
        retention_note="Возвращайся за поручением старосты и первыми заточками, пока кольца ещё «мягкие».",
        npc_guard_title="староста",
        economy_blurb="Местная лотерея скромная; в гильдии банкиров принимают золото в сейф.",
    ),
    31: CityHubDef(
        key="ironfall",
        tagline="Ледяной форпост средних колец — отсюда видно, кто дойдёт до верхних ярусов.",
        welcome_html=(
            "<b>Айронфолл</b> стоит на пороге <i>Ледяных Пиков</i>: бастион викингов и наёмников, "
            "где клинки заряжают морозом, а в таверне спорят только те, кто пережил хотя бы одного элитного стража. "
            "Кузнецы города куют под башню — без их заточки средние этажи начинают «кусаться».\n"
            "<i>Стража Айронфолла ведёт учёт охотников на тварей: поручения здесь щедрее, чем у ручья.</i>"
        ),
        retention_note="Середина башни без хаба выгорает: Айронфолл — точка, где ты пополняешь руны, зелья и решимость.",
        npc_guard_title="капитан стражи",
        economy_blurb="Ростовщики легиона дают короткие займы под процент; лотерея — городская, с крупным фондом.",
    ),
    61: CityHubDef(
        key="emberhall",
        tagline="Гномьи мастерские и жар плавилен — сердце вулканического кольца.",
        welcome_html=(
            "<b>Эмберхолл</b> — промышленный гигант у разломов лавы: шипы мостов, капли шлака на брусчатке, "
            "воздух пахнет углем и магией сдерживания. Здесь перекуёшь легендарные чертежи и услышишь слухи "
            "о том, что творится в Небесной Крепости выше.\n"
            "<i>Инспекторы казармы не терпят слабаков: их поручения — экзамен перед верхними зонами.</i>"
        ),
        retention_note="Перед 70+ этажами без захода в Эмберхолл нечем погасить инфляцию лута — трать золото в sinks и кузнице.",
        npc_guard_title="инспектор казармы",
        economy_blurb="Банк гильдии кузнецов держит сейфы; аукцион лотов пока вестится объявлениями у таверны.",
    ),
    91: CityHubDef(
        key="eternis",
        tagline="Последний шик перед Залом Вечности — здесь решается, кто увидит 100-й этаж.",
        welcome_html=(
            "<b>Этернис</b> парит на краю небесного кольца: мосты из светящегося камня, стражи с перьями вместо плюмажей, "
            "и тишина, которую режет только гул башни вверху. Это эндгейм-хаб: лучшие руны, рискованные займы "
            "и последняя передышка перед бездной и вечностью.\n"
            "<i>Командор гарнизона выдаёт поручения с наивысшими наградами — цена ошибки тоже высока.</i>"
        ),
        retention_note="Игроки, застрявшие на 80–99, цепляются за Этернис: фарм, sinks и финальная экипировка.",
        npc_guard_title="командор гарнизона",
        economy_blurb="Крупнейшая лотерея кольца, ростовщики небесных домов и надёжные сейфы для золота.",
    ),
    }


_CITY_HUBS: dict[int, CityHubDef] = _build_city_hubs()

_HUB_KEYS_LOADED = False


def _ensure_hub_keys() -> None:
    global HUB_KEY_BY_FLOOR, _HUB_KEYS_LOADED
    if _HUB_KEYS_LOADED:
        return
    try:
        from game.data.catalogs.cities_catalog import catalog_hub_key_by_floor

        cat = catalog_hub_key_by_floor()
        if cat:
            HUB_KEY_BY_FLOOR = cat
    except Exception:
        pass
    _HUB_KEYS_LOADED = True


def hub_key_for_floor(floor_number: int) -> str | None:
    """Стабильный ключ хаба или None."""
    _ensure_hub_keys()
    return HUB_KEY_BY_FLOOR.get(int(floor_number))


def get_city_hub_def(floor_number: int) -> CityHubDef | None:
    """Расширенное описание, если этаж — город-хаб."""
    return _CITY_HUBS.get(int(floor_number))


def resolve_city(floor_number: int) -> CityInfo | None:
    """Тонкая обёртка над floor_data (единая точка импорта для квестов)."""
    return floor_data.get_city_for_floor(floor_number)


def format_city_hub_rich_html(city: CityInfo) -> str:
    """
    Полный текст входа в город: тема из floor_data + лор из этого модуля.
    """
    ext = get_city_hub_def(int(city.floor))
    base_theme = html.escape(city.theme_ru)
    head = f"{city.emoji} <b>{html.escape(city.name)}</b>\n<i>{base_theme}</i>"
    if ext is None:
        return head
    ret = html.escape(ext.retention_note)
    econ = html.escape(ext.economy_blurb)
    return (
        f"{head}\n"
        f"<b>{html.escape(ext.tagline)}</b>\n"
        f"{ext.welcome_html}\n"
        f"📌 <i>{ret}</i>\n"
        f"💸 <i>{econ}</i>"
    )


def guard_npc_title_for_floor(floor_number: int) -> str:
    """Как называть NPC поручения в UI (fallback — стражник)."""
    ext = get_city_hub_def(int(floor_number))
    if ext is None:
        return "стражник"
    return ext.npc_guard_title
