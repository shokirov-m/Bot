"""
Статические промокоды (ключ — ВЕРХНИЙ РЕГИСТР).
Игрок может активировать каждый код один раз.

Если в БД есть строка с тем же code_key (/admin promo add …), при активации
используется запись из БД (лимиты и срок — там).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from game.items.equipment import hunter_set_uncommon_payloads, promo_starter_armor_amulet_payloads


@dataclass(frozen=True, slots=True)
class PromoReward:
    gold: int = 0
    xp: int = 0
    rune_stones: int = 0


# Публичные коды для игроков; при необходимости добавляй новые.
PROMO_REWARDS: dict[str, PromoReward] = {
    "GIFT10K": PromoReward(gold=10000, xp=10000),
    "TOWER2026": PromoReward(gold=15000, xp=2000),
    "TOWER1000": PromoReward(gold=15000, xp=2000),
    "START": PromoReward(gold=150, xp=80),
    "WELCOME": PromoReward(gold=80, xp=40, rune_stones=1),
    # Одно использование на аккаунт + броня и амулет в сумку (нужны 2 свободные ячейки).
    "BASEKIT26": PromoReward(gold=30, xp=40, rune_stones=0),
    # Одно использование: редкий питомец «Осколок пустоты» + немного золота и опыта.
    "VOIDPROMO26": PromoReward(gold=80, xp=120, rune_stones=1),
    # Набор Охотника (9 необычных предметов): нужны 9 свободных ячеек в сумке.
    "HUNTERSET": PromoReward(gold=120, xp=80, rune_stones=0),
}


def reward_for_code(normalized: str) -> PromoReward | None:
    return PROMO_REWARDS.get(normalized)


def bag_payloads_for_code(normalized: str) -> tuple[dict[str, Any], ...] | None:
    """Доп. предметы в сумку по статическому коду (копии для каждой выдачи)."""
    if normalized == "BASEKIT26":
        return promo_starter_armor_amulet_payloads()
    if normalized == "HUNTERSET":
        return hunter_set_uncommon_payloads()
    return None


def promo_pet_key_for_code(normalized: str) -> str | None:
    """Ключ питомца из PET_* по статическому промокоду (не inventory)."""
    if normalized == "VOIDPROMO26":
        return "pet_void_wisp"
    return None
