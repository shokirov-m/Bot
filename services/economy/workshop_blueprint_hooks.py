"""Минимальные хуки выдачи редких чертежей (босс, квест — точки расширения)."""

from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from game.enemies.floors.spawns import FloorMonsterSpawn
from game.crafting.workshop_meta import add_known_blueprint


async def roll_blueprint_after_boss(
    session: AsyncSession,
    character: Character,
    spawn: FloorMonsterSpawn,
) -> str:
    """Шанс чертежа bp_tower_flame_blade после крупного босса."""
    _ = session
    if not spawn.is_major_boss:
        return ""
    if random.random() >= 0.06:
        return ""
    if add_known_blueprint(character, "bp_tower_flame_blade"):
        return "📜 В башне найден <b>редкий чертёж</b> — загляни в Мастерскую!"
    return ""
