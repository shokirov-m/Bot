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
        price=1200,
        blurb="+3 стамины (не выше максимума). Макс. 5 раз в сутки.",
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


# ---- Ежедневные товары (детерминированный пул на день/этаж) ----

import hashlib
from typing import Any

# (recipe_id, name_ru, price_gold). Привязка чертежей к game/crafting/recipes.py:RECIPES.
TAVERN_DAILY_BLUEPRINTS: tuple[tuple[str, str, int], ...] = (
    ("salve_basic", "📜 Чертёж: Настой (HP)", 220),
    ("ring_siphon", "📜 Чертёж: Перстень поглощения", 480),
    # Запасные «псевдо-чертежи» как заглушки, если выпадет на день один и тот же.
    ("salve_basic", "📜 Чертёж: Настой (HP)", 220),
)

# (key, item_data, price_gold). Снаряжение, стыкуется с инвентарём.
TAVERN_DAILY_GEAR: tuple[tuple[str, dict[str, Any], int], ...] = (
    (
        "tdg_iron_blade",
        {
            "name": "🗡 Железный клинок",
            "kind": "weapon",
            "weapon_type": "blade",
            "rarity": "uncommon",
            "attack": 14,
            "summary": "Кузнец таверны: ровный клинок без излишеств.",
        },
        320,
    ),
    (
        "tdg_oak_buckler",
        {
            "name": "🛡 Дубовый щит",
            "kind": "shield",
            "rarity": "uncommon",
            "defense": 7,
            "summary": "Купец таверны: лёгкий щит, удобно носить.",
        },
        280,
    ),
    (
        "tdg_swift_bow",
        {
            "name": "🏹 Быстрый лук",
            "kind": "weapon",
            "weapon_type": "bow",
            "rarity": "uncommon",
            "attack": 13,
            "summary": "Ровная тетива и крепкое плечо.",
        },
        330,
    ),
    (
        "tdg_padded_vest",
        {
            "name": "🧥 Мягкий жилет",
            "kind": "armor",
            "rarity": "uncommon",
            "defense": 8,
            "summary": "Добротная подкладка, лёгкий вес.",
        },
        290,
    ),
)


def daily_tavern_offers(
    floor_number: int,
    date_iso: str,
) -> dict[str, list[tuple[str, str, int] | tuple[str, dict[str, Any], int]]]:
    """3 чертежа + 2 снаряжения, детерминированно по (этаж, дата)."""
    seed_str = f"tvr|{int(floor_number)}|{str(date_iso)}".encode("utf-8")
    seed = int(hashlib.sha256(seed_str).hexdigest(), 16)
    bps_list = list(TAVERN_DAILY_BLUEPRINTS)
    grs_list = list(TAVERN_DAILY_GEAR)
    bps_pick: list[tuple[str, str, int]] = []
    seen_bp: set[str] = set()
    for k in range(len(bps_list)):
        idx = (seed + k * 7) % len(bps_list)
        item = bps_list[idx]
        if item[0] in seen_bp:
            continue
        seen_bp.add(item[0])
        bps_pick.append(item)
        if len(bps_pick) >= 3:
            break
    grs_pick: list[tuple[str, dict[str, Any], int]] = []
    seen_gr: set[str] = set()
    for k in range(len(grs_list)):
        idx = (seed + k * 13 + 5) % len(grs_list)
        item = grs_list[idx]
        if item[0] in seen_gr:
            continue
        seen_gr.add(item[0])
        grs_pick.append(item)
        if len(grs_pick) >= 2:
            break
    return {"blueprints": bps_pick, "gears": grs_pick}
