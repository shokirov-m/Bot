"""Создание предметов по рецептам (материалы в сумке)."""

from __future__ import annotations

import copy
import html
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
from game.crafting.recipes_data import get_recipe_by_id, is_forge_instant
from game.items import craft_resources as cr_sys
from game.items import materials as mat_sys
from services.forge_service import _consume_materials  # noqa: SLF001
from services.workshop_service import apply_workshop_craft_premium


def _can_afford(cost: dict[str, int], bag_items: list[Any]) -> bool:
    for r, n in cost.items():
        if mat_sys.total_materials_in_bag(bag_items, r) < int(n):
            return False
    return True


def _can_afford_craft(bag_items: list[Any], craft_cost: dict[str, int]) -> bool:
    for rid, n in craft_cost.items():
        if cr_sys.total_craft_resource_in_bag(bag_items, str(rid)) < int(n):
            return False
    return True


async def try_craft(
    session: AsyncSession,
    character: Character,
    recipe_id: str,
) -> tuple[bool, list[str]]:
    r = get_recipe_by_id(recipe_id)
    if r is None:
        return False, ["Нет такого рецепта."]
    if not is_forge_instant(r):
        return False, [
            "Этот рецепт ведёт в <b>Мастерскую</b> (меню → Мастерская) — очередь и таймер.",
        ]
    cost = dict(r.get("cost") or {})
    craft_cost = {str(k): int(v) for k, v in (r.get("craft_cost") or {}).items()}
    bag_items = await inventory_repo.list_bag_items(session, character.id)
    if cost and not _can_afford(cost, bag_items):
        return False, ["Недостаточно материалов заточки в сумке."]
    if craft_cost and not _can_afford_craft(bag_items, craft_cost):
        return False, ["Недостаточно ремесленных материалов (гача / именованные ресурсы)."]
    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, ["Нет свободной ячейки в сумке."]

    for rare, n in cost.items():
        await _consume_materials(session, int(character.id), str(rare), int(n))
    if craft_cost:
        await cr_sys.consume_craft_resources(session, int(character.id), craft_cost)

    pl = apply_workshop_craft_premium(copy.deepcopy(r["result"]))
    await inventory_repo.add_bag_item(session, character.id, pl, bag_slot=free)
    await session.flush()
    nm = html.escape(str(pl.get("name", "Предмет")))
    lines = [
        f"⚒️ <b>{html.escape(str(r.get('name_ru', recipe_id)))}</b> готово.",
        f"📦 {nm} — в сумку (ячейка {free}).",
    ]
    return True, lines
