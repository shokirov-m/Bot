"""
Поручения стражи в городах-хабах (3, 31, 61, 91): победы в боях башни.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from game.tower.progression import floor_data
from game.locations.cities import guard_npc_title_for_floor


@dataclass(frozen=True, slots=True)
class CityQuestTemplate:
    quest_key: str
    title: str
    intro_html: str
    kills_needed: int
    reward_gold: int
    reward_xp: int
    reward_gear: dict[str, Any] | None = None


def _city_floor(floor_number: int) -> int | None:
    city = floor_data.get_city_for_floor(floor_number)
    if city is None:
        return None
    return int(city.floor)


def city_quest_template(floor_number: int) -> CityQuestTemplate | None:
    cf = _city_floor(floor_number)
    if cf is None:
        return None
    city = floor_data.get_city_for_floor(floor_number)
    assert city is not None
    name_esc = html.escape(city.name)
    role_esc = html.escape(guard_npc_title_for_floor(floor_number).capitalize())
    reward_gear: dict[str, Any] | None = None
    if cf == 1:
        # Стартовый хаб (Тихий Ручей): раньше попадал в ветку else (как этаж 91) — неверный баланс и ощущение «сломанного» квеста.
        need, rg, rx = 1, 15, 12
        intro = (
            f"{role_esc} у ворот <b>{name_esc}</b>: "
            "«Шебуршат тени у башни — докажи, что не беспомощен. "
            f"Одолей <b>{need}</b> врага где угодно на ярусах — скромная плата, но честная.»"
        )
    elif cf == 3:
        need, rg, rx = 2, 28, 18
        intro = (
            f"{role_esc} <b>{name_esc}</b> беспокоится: "
            "«У окраины башни шебуршат твари — небольшая угроза деревне. "
            f"Одолей <b>{need}</b> врагов где угодно в башне — и прими нашу благодарность.»"
        )
    elif cf == 31:
        need, rg, rx = 3, 85, 48
        intro = (
            f"{role_esc} <b>{name_esc}</b> хмурится: "
            "«Твари с нижних колец лезут к воротам. "
            f"Уложи <b>{need}</b> врагов башни — дам награду и благодарность гильдии.»"
        )
    elif cf == 61:
        need, rg, rx = 4, 160, 88
        intro = (
            f"{role_esc} в <b>{name_esc}</b>: "
            "«Нужны доказательства силы. "
            f"<b>{need}</b> поверженных тварей — и положено жалование.»"
        )
    else:
        need, rg, rx = 5, 320, 165
        intro = (
            f"{role_esc} <b>{name_esc}</b>: "
            "«Бездна шевелится. "
            f"Низвергни <b>{need}</b> тварей башни — награда достойная.»"
        )
    qtitle = (
        f"Поручение старосты — {city.name}"
        if cf in (1, 3)
        else f"Поручение стражи — {city.name}"
    )
    return CityQuestTemplate(
        quest_key=f"city_task_{cf}",
        title=qtitle,
        intro_html=intro,
        kills_needed=need,
        reward_gold=rg,
        reward_xp=rx,
        reward_gear=reward_gear,
    )
