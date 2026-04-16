"""
Бонусы к основным характеристикам с экипировки и активного титула.
Разбор полей предмета — в game.items.stat_bonuses.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
from game.characters.titles import TITLE_BY_KEY
from game.items.stat_bonuses import STAT_KEYS, empty_stat_bonus_map, stat_bonuses_from_item_data
from services import title_service


async def equipped_gear_stat_bonuses(session: AsyncSession, character_id: int) -> dict[str, int]:
    total = empty_stat_bonus_map()
    items = await inventory_repo.list_equipped_items(session, character_id)
    for it in items:
        part = stat_bonuses_from_item_data(dict(it.item_data or {}))
        for k in STAT_KEYS:
            total[k] += part[k]
    return total


def active_title_stat_bonuses(character: Character) -> dict[str, int]:
    k = title_service.active_title_key(character)
    if not k:
        return empty_stat_bonus_map()
    t = TITLE_BY_KEY.get(k)
    if t is None:
        return empty_stat_bonus_map()
    return {
        "str": int(getattr(t, "stat_str", 0)),
        "dex": int(getattr(t, "stat_dex", 0)),
        "int": int(getattr(t, "stat_int", 0)),
        "vit": int(getattr(t, "stat_vit", 0)),
        "luck": int(getattr(t, "stat_luck", 0)),
    }


async def extra_stat_bonuses(session: AsyncSession, character: Character) -> tuple[dict[str, int], dict[str, int]]:
    """(сумма с экипировки, сумма с активного титула)."""
    gear = await equipped_gear_stat_bonuses(session, character.id)
    title_b = active_title_stat_bonuses(character)
    return gear, title_b


def merge_stat_maps(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    return {k: int(a.get(k, 0)) + int(b.get(k, 0)) for k in STAT_KEYS}


async def effective_primary_stats(session: AsyncSession, character: Character) -> dict[str, int]:
    """Статы персонажа в бою/профиле: база из БД + экипировка + титул."""
    gear, title_b = await extra_stat_bonuses(session, character)
    extra = merge_stat_maps(gear, title_b)
    return {
        "str": int(character.stat_strength) + extra["str"],
        "dex": int(character.stat_dexterity) + extra["dex"],
        "int": int(character.stat_intelligence) + extra["int"],
        "vit": int(character.stat_vitality) + extra["vit"],
        "luck": int(character.stat_luck) + extra["luck"],
    }
