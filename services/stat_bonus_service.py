"""
Бонусы к основным характеристикам с экипировки и активного титула.
Разбор полей предмета — в game.items.stat_bonuses.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.models.inventory import InventoryItem
from db.repository import inventory_repo
from game.characters.titles import TITLE_BY_KEY
from game.items import enchant as enchant_rules
from game.items.rarity_scaling import scaled_armor_defense_value
from game.archetypes import manager as arch_manager
from game.items.stat_bonuses import STAT_KEYS, empty_stat_bonus_map, stat_bonuses_from_item_data
from services import profession_service, title_service


def _messenger_set_bonus_from_equipped(items: list[InventoryItem]) -> dict[str, int]:
    """Набор «Посланник башни»: два предмета с set_key messenger на персонаже."""
    n = 0
    for it in items:
        d = dict(it.item_data or {})
        if str(d.get("set_key") or "").lower() == "messenger":
            n += 1
    if n >= 2:
        b = empty_stat_bonus_map()
        b["int"] = 5
        b["luck"] = 5
        return b
    return empty_stat_bonus_map()


def armor_hp_bonus_from_item_data(data: dict[str, Any] | None) -> int:
    """Плоский бонус к макс. HP с экипировки (поле hp_bonus; не расходники/руны)."""
    if not data:
        return 0
    k = str(data.get("kind") or "").lower()
    if k in ("consumable", "rune"):
        return 0
    return max(0, int(data.get("hp_bonus", 0) or 0))


async def equipped_armor_hp_bonus_flat(session: AsyncSession, character_id: int) -> int:
    """Сумма hp_bonus с надетой экипировки (броня, кольца и т.д.)."""
    total = 0
    items = await inventory_repo.list_equipped_items(session, character_id)
    for it in items:
        total += armor_hp_bonus_from_item_data(dict(it.item_data or {}))
    return total


async def equipped_gear_stat_bonuses(session: AsyncSession, character_id: int) -> dict[str, int]:
    """
    Сумма плоских/вложенных статов со всех надетых предметов (любой ``equip_slot`` из
    ``EQUIP_ORDER``: weapon, offhand, armor, pants, helmet, gloves, ring, ring2, amulet).
    Репозиторий не отфильтровывает второе кольцо и вторую руку.
    """
    total = empty_stat_bonus_map()
    items = await inventory_repo.list_equipped_items(session, character_id)
    for it in items:
        part = stat_bonuses_from_item_data(dict(it.item_data or {}))
        for k in STAT_KEYS:
            total[k] += part[k]
    set_b = _messenger_set_bonus_from_equipped(items)
    for k in STAT_KEYS:
        total[k] += set_b[k]
    return total


def _title_stat_row(key: str | None) -> dict[str, int]:
    if not key:
        return empty_stat_bonus_map()
    td = TITLE_BY_KEY.get(key)
    if td is None:
        return empty_stat_bonus_map()
    return {
        "str": int(getattr(td, "stat_str", 0)),
        "dex": int(getattr(td, "stat_dex", 0)),
        "int": int(getattr(td, "stat_int", 0)),
        "vit": int(getattr(td, "stat_vit", 0)),
        "luck": int(getattr(td, "stat_luck", 0)),
    }


def active_title_stat_bonuses(character: Character) -> dict[str, int]:
    """Сумма статов с двух слотов титулов (если оба заданы и разные)."""
    keys: list[str] = []
    k1 = title_service.active_title_key(character)
    if k1:
        keys.append(k1)
    k2 = title_service.active_secondary_title_key(character)
    if k2 and k2 not in keys:
        keys.append(k2)
    out = empty_stat_bonus_map()
    for k in keys:
        row = _title_stat_row(k)
        for sk in STAT_KEYS:
            out[sk] += row[sk]
    return out


async def extra_stat_bonuses(session: AsyncSession, character: Character) -> tuple[dict[str, int], dict[str, int]]:
    """(сумма с экипировки, сумма с активного титула + основная профессия + древо навыков)."""
    gear = await equipped_gear_stat_bonuses(session, character.id)
    title_b = active_title_stat_bonuses(character)
    prof_b = profession_service.profession_primary_stat_bonuses(character)
    tree_b_raw = arch_manager.get_tree_bonuses(character)
    
    # Filter only base stats (str, dex, int, vit, luck) and cast to int
    tree_b = {k: int(v) for k, v in tree_b_raw.items() if k in STAT_KEYS}
    
    title_b = merge_stat_maps(title_b, prof_b)
    title_b = merge_stat_maps(title_b, tree_b)
    return gear, title_b


def merge_stat_maps(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    return {k: int(a.get(k, 0)) + int(b.get(k, 0)) for k in STAT_KEYS}


async def equipped_gear_defense_total(session: AsyncSession, character_id: int) -> int:
    """Суммарная защита (defense) со всей надетой экипировки, с учётом заточки (+5%/ур.)."""
    items = await inventory_repo.list_equipped_items(session, character_id)
    total = 0
    for it in items:
        data = it.item_data or {}
        base_def = int(data.get("defense", data.get("armor", 0)) or 0)
        def_val = scaled_armor_defense_value(base_def, data)
        ench = enchant_rules.current_enchant_level(data)
        mult = enchant_rules.enchant_stat_multiplier(ench)
        total += max(0, int(round(def_val * mult)))
    return total


async def effective_primary_stats(session: AsyncSession, character: Character) -> dict[str, int]:
    """Статы в бою/профиле: база из БД + экип + титул(ы) + бонус основной профессии."""
    gear, title_b = await extra_stat_bonuses(session, character)
    extra = merge_stat_maps(gear, title_b)
    return {
        "str": int(character.stat_strength) + extra["str"],
        "dex": int(character.stat_dexterity) + extra["dex"],
        "int": int(character.stat_intelligence) + extra["int"],
        "vit": int(character.stat_vitality) + extra["vit"],
        "luck": int(character.stat_luck) + extra["luck"],
    }
