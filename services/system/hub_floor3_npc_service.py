"""
Лёгкие поручения NPC на 3 этаже (город): награды предметом + опыт/золото.
meta_progress['hub_f3_v1'] = { 'scribe': bool, 'herbalist': bool }
"""

from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
import services.progression.character_service as character_service

META = "hub_f3_v1"

_SCRIBE_GOLD = 25
_SCRIBE_XP = 12
_HERB_XP = 8
_HERB_GOLD = 15


def _st(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META)
    if not isinstance(raw, dict):
        raw = {}
    return mp, raw


def _save(character: Character, mp: dict[str, Any], st: dict[str, Any]) -> None:
    mp[META] = st
    character.meta_progress = mp


def scribe_done(character: Character) -> bool:
    _, st = _st(character)
    return bool(st.get("scribe"))


def herbalist_done(character: Character) -> bool:
    _, st = _st(character)
    return bool(st.get("herbalist"))


async def try_scribe_quest(session: AsyncSession, character: Character) -> tuple[bool, str]:
    if scribe_done(character):
        return False, "Писарь уже записал твою подпись в книгу."
    if int(character.gold) < _SCRIBE_GOLD:
        return False, f"Нужно {_SCRIBE_GOLD} золота на пергамент и пошлину."
    mp, st = _st(character)
    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, "Освободи хотя бы одну ячейку сумки за награду."
    character.gold = int(character.gold) - _SCRIBE_GOLD
    await character_service.add_experience_async(session, character, _SCRIBE_XP, bot=None)
    payload = {
        "name": "Смоляной бальзам",
        "kind": "consumable",
        "rarity": "common",
        "summary": "В бою: мелкий запас (+5 HP один раз).",
        "use_tag": "heal_hp_flat",
        "use_value": 5,
    }
    await inventory_repo.add_bag_item(session, character.id, copy.deepcopy(payload), bag_slot=free)
    st = dict(st)
    st["scribe"] = True
    _save(character, dict(mp), st)
    return (
        True,
        f"−{_SCRIBE_GOLD} 💰 · +{_SCRIBE_XP} опыта. <b>Смоляной бальзам</b> — в сумку (ячейка {free}).",
    )


async def try_herbalist_quest(session: AsyncSession, character: Character) -> tuple[bool, str]:
    if herbalist_done(character):
        return False, "Мара уже улыбнулась тебе."
    mp, st = _st(character)
    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, "Освободи ячейку сумки за травяной свёрток."
    await character_service.add_experience_async(session, character, _HERB_XP, bot=None)
    character_service.add_gold(character, _HERB_GOLD)
    payload = {
        "name": "Травяной свёрток",
        "kind": "consumable",
        "rarity": "common",
        "summary": "Вне боя: +2 ⚡ (как походный паёк).",
        "use_tag": "stamina_flat",
        "use_value": 2,
    }
    await inventory_repo.add_bag_item(session, character.id, copy.deepcopy(payload), bag_slot=free)
    st = dict(st)
    st["herbalist"] = True
    _save(character, dict(mp), st)
    return (
        True,
        f"+{_HERB_GOLD} 💰 · +{_HERB_XP} опыта. <b>Травяной свёрток</b> — ячейка {free}.",
    )
