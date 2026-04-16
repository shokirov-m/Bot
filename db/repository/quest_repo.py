"""Прогресс квестов."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.quest import QuestProgress


async def get_by_key(
    session: AsyncSession,
    character_id: int,
    quest_key: str,
) -> QuestProgress | None:
    result = await session.execute(
        select(QuestProgress).where(
            QuestProgress.character_id == character_id,
            QuestProgress.quest_key == quest_key,
        ),
    )
    return result.scalar_one_or_none()


async def create_active(
    session: AsyncSession,
    character_id: int,
    quest_key: str,
    progress: dict[str, Any],
) -> QuestProgress:
    row = QuestProgress(
        character_id=character_id,
        quest_key=quest_key,
        status="active",
        progress=progress,
    )
    session.add(row)
    await session.flush()
    return row


async def list_active_city_quests(session: AsyncSession, character_id: int) -> list[QuestProgress]:
    result = await session.execute(
        select(QuestProgress).where(
            QuestProgress.character_id == character_id,
            QuestProgress.status == "active",
            QuestProgress.quest_key.like("city_task_%"),
        ),
    )
    return list(result.scalars().all())


async def list_active_npc_extended_quests(
    session: AsyncSession,
    character_id: int,
) -> list[QuestProgress]:
    """Активные квесты npcq_* (расширенные NPC, не странник)."""
    result = await session.execute(
        select(QuestProgress).where(
            QuestProgress.character_id == character_id,
            QuestProgress.status == "active",
            QuestProgress.quest_key.like("npcq_%"),
        ),
    )
    return list(result.scalars().all())


async def list_active_slain_quests(session: AsyncSession, character_id: int) -> list[QuestProgress]:
    result = await session.execute(
        select(QuestProgress).where(
            QuestProgress.character_id == character_id,
            QuestProgress.status == "active",
            QuestProgress.quest_key.like("tower_slain_%"),
        ),
    )
    return list(result.scalars().all())


async def mark_completed(session: AsyncSession, row: QuestProgress) -> None:
    row.status = "completed"
    row.completed_at = datetime.now(UTC)
    await session.flush()
