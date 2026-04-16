"""
Таверна в городах-хабах (этажи 3, 31, 61, 91): меню, цены (золото). Баффы «пьяного бойца» — позже.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.floors import floor_data


@dataclass(frozen=True, slots=True)
class TavernOffer:
    key: str
    name: str
    emoji: str
    price: int
    blurb: str


TAVERN_MENU: tuple[TavernOffer, ...] = (
    TavernOffer(
        key="ale",
        name="Кружка эля",
        emoji="🍺",
        price=18,
        blurb="Лёгкий отдых: +12% HP и +8% MP.",
    ),
    TavernOffer(
        key="stew",
        name="Горшок рагу",
        emoji="🍲",
        price=42,
        blurb="Сытно: +32% HP и +25% MP.",
    ),
    TavernOffer(
        key="feast",
        name="Пир героя",
        emoji="🍖",
        price=98,
        blurb="Полное восстановление HP и MP.",
    ),
    TavernOffer(
        key="lodging",
        name="Ночлег",
        emoji="🛏️",
        price=55,
        blurb="+3 стамины (не выше максимума).",
    ),
)


def offer_by_key(key: str) -> TavernOffer | None:
    k = key.strip().lower()
    for o in TAVERN_MENU:
        if o.key == k:
            return o
    return None


def tavern_available_on_floor(floor_number: int) -> bool:
    return floor_data.get_city_for_floor(floor_number) is not None
