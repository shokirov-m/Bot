"""
Зачарование алхимика: расходник из сумки переносит бонус на предмет экипировки в сумке.
Поддержка нескольких стихий (см. ice_resist_pct в бою) и плоских статов/защиты.
"""

from __future__ import annotations

import html
import copy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from db.models.inventory import InventoryItem
from db.repository import inventory_repo

USE_TAG_ALCHEMY_ENCHANT = "workshop_alchemy_enchant"

# Броня / бижутерия под «защитные» свитки; оружие — под усиливающие.
_ARMOR_KINDS = frozenset({"armor", "pants", "helmet", "gloves", "ring", "amulet", "shield"})
_WEAPON_KINDS = frozenset({"weapon"})
_CAP_PCT = 40


def _kind_of(data: dict[str, Any]) -> str:
    return str(data.get("kind") or "").strip().lower()


def scroll_targets_armor(scroll: dict[str, Any]) -> bool:
    return bool(scroll.get("alchemy_enchant_armor"))


def scroll_targets_weapon(scroll: dict[str, Any]) -> bool:
    return bool(scroll.get("alchemy_enchant_weapon"))


def can_apply_scroll_to_target(scroll_data: dict[str, Any], target_data: dict[str, Any]) -> bool:
    sd = dict(scroll_data or {})
    tk = _kind_of(target_data)
    if scroll_targets_weapon(sd):
        return tk in _WEAPON_KINDS
    if scroll_targets_armor(sd):
        return tk in _ARMOR_KINDS
    return False


_RESIST_SCROLL_KEYS: tuple[tuple[str, str], ...] = (
    ("add_fire_resist_pct", "fire_resist_pct"),
    ("add_ice_resist_pct", "ice_resist_pct"),
    ("add_lightning_resist_pct", "lightning_resist_pct"),
    ("add_poison_resist_pct", "poison_resist_pct"),
    ("add_dark_resist_pct", "dark_resist_pct"),
)

_STAT_SCROLL_KEYS: tuple[tuple[str, str], ...] = (
    ("add_str_flat", "str"),
    ("add_dex_flat", "dex"),
    ("add_int_flat", "int"),
    ("add_vit_flat", "vit"),
)


def _merge_enchant_onto_target(scroll: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(target)

    # Сопротивления стихиям (кап как раньше — общий на строку)
    for sk, ik in _RESIST_SCROLL_KEYS:
        add = int(scroll.get(sk) or 0)
        if add > 0:
            cur = int(out.get(ik) or 0)
            out[ik] = min(_CAP_PCT, cur + add)

    # Урон через стихию (в данных предмета ключ legacy fire_damage_bonus_pct — в бою суммируется в elemental %)
    add_fire_dmg = int(scroll.get("add_fire_damage_bonus_pct") or 0)
    if add_fire_dmg > 0:
        cur = int(out.get("fire_damage_bonus_pct") or 0)
        out["fire_damage_bonus_pct"] = min(_CAP_PCT, cur + add_fire_dmg)

    add_def = int(scroll.get("add_defense_flat") or 0)
    if add_def > 0:
        cur = int(out.get("defense", out.get("armor", 0)) or 0)
        out["defense"] = cur + add_def

    for sk, dk in _STAT_SCROLL_KEYS:
        add = int(scroll.get(sk) or 0)
        if add > 0:
            cur = int(out.get(dk) or 0)
            out[dk] = cur + add

    note = str(scroll.get("enchant_label_ru") or "").strip()
    if note:
        prev = str(out.get("alchemy_enchant_summary_ru") or "").strip()
        out["alchemy_enchant_summary_ru"] = f"{prev}; {note}".strip("; ").strip() if prev else note
    return out


async def try_apply_alchemy_enchant(
    session: AsyncSession,
    character: Character,
    scroll_item_id: int,
    target_item_id: int,
) -> tuple[bool, str]:
    from game.crafting.recipes_data import PROF_ALCHEMIST
    from game.crafting.workshop_meta import prof_level

    if scroll_item_id == target_item_id:
        return False, "Нужны два разных предмета."

    scroll_it = await inventory_repo.get_item_for_character(session, character.id, scroll_item_id)
    target_it = await inventory_repo.get_item_for_character(session, character.id, target_item_id)
    if scroll_it is None or target_it is None:
        return False, "Предмет не найден."
    if scroll_it.is_equipped or target_it.is_equipped:
        return False, "Сначала сними предметы в сумку."
    if scroll_it.bag_slot is None or target_it.bag_slot is None:
        return False, "Оба предмета должны быть в сумке."

    sd = dict(scroll_it.item_data or {})
    if str(sd.get("use_tag") or "") != USE_TAG_ALCHEMY_ENCHANT:
        return False, "Это не алхимическое зачарование."

    need = int(sd.get("min_alchemist_level_to_use") or 0)
    if need > 0 and prof_level(character, PROF_ALCHEMIST) < need:
        return False, f"Нужен алхимик {need}+ уровня, чтобы применить этот свиток."

    td = dict(target_it.item_data or {})
    if not can_apply_scroll_to_target(sd, td):
        return False, "Этот свиток не подходит к этому типу предмета."

    new_payload = _merge_enchant_onto_target(sd, td)
    target_it.item_data = new_payload
    flag_modified(target_it, "item_data")

    await inventory_repo.consume_one_from_stack(session, scroll_it)
    await session.flush()

    nm = html.escape(str(new_payload.get("name", "Предмет")))
    return True, f"✅ Зачарование наложено на <b>{nm}</b>."


def summarize_scroll(scroll_data: dict[str, Any]) -> str:
    sd = dict(scroll_data or {})
    parts: list[str] = []
    for sk, label in (
        ("add_fire_resist_pct", "огонь"),
        ("add_ice_resist_pct", "лёд"),
        ("add_lightning_resist_pct", "молния"),
        ("add_poison_resist_pct", "яд"),
        ("add_dark_resist_pct", "тьма"),
    ):
        v = int(sd.get(sk) or 0)
        if v > 0:
            parts.append(f"+{v}% сопр. ({label})")
    if int(sd.get("add_fire_damage_bonus_pct") or 0) > 0:
        parts.append(f"+{int(sd['add_fire_damage_bonus_pct'])}% стих. урона (оружие)")
    if int(sd.get("add_defense_flat") or 0) > 0:
        parts.append(f"+{int(sd['add_defense_flat'])} защиты")
    for sk, lab in (("add_str_flat", "СИЛ"), ("add_dex_flat", "ЛОВ"), ("add_int_flat", "ИНТ"), ("add_vit_flat", "ВЫН")):
        v = int(sd.get(sk) or 0)
        if v > 0:
            parts.append(f"+{v} {lab}")
    need = int(sd.get("min_alchemist_level_to_use") or 0)
    if need > 0:
        parts.append(f"нужен алх. {need}+")
    return ", ".join(parts) if parts else "Зачарование"


async def list_compatible_targets(
    session: AsyncSession,
    character_id: int,
    scroll_data: dict[str, Any],
) -> list[InventoryItem]:
    sd = dict(scroll_data or {})
    bag = await inventory_repo.list_bag_items(session, character_id)
    out: list[InventoryItem] = []
    for it in bag:
        if bool(it.is_equipped):
            continue
        d = dict(it.item_data or {})
        if can_apply_scroll_to_target(sd, d):
            out.append(it)
    return out
