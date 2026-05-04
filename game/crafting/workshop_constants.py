"""Константы мастерской: этаж хаба для заказов, потолок уровней профессий."""

from __future__ import annotations

# Город игроков / хаб заказов мастерской
WORKSHOP_ORDERS_HUB_FLOOR: int = 21

# Кузнец качается до 30; остальные — до 20
MAX_PROF_BY_KEY: dict[str, int] = {
    "blacksmith": 30,
    "alchemist": 20,
    "jeweler": 20,
}


def max_profession_level(profession: str) -> int:
    return int(MAX_PROF_BY_KEY.get(str(profession).lower().strip(), 20))
