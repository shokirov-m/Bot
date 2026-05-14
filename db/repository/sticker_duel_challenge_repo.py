"""Временные вызовы на стикер-дуэль (код для /duel_accept)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def insert_challenge(
    session: AsyncSession,
    *,
    code: str,
    attacker_character_id: int,
    defender_character_id: int,
    attacker_sticker_id: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO sticker_duel_challenges
            (code, attacker_character_id, defender_character_id, attacker_sticker_id, created_at)
            VALUES (:code, :aid, :did, :sid, :ts)
            """,
        ),
        {
            "code": code[:16],
            "aid": int(attacker_character_id),
            "did": int(defender_character_id),
            "sid": str(attacker_sticker_id)[:48],
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        },
    )


async def fetch_challenge(session: AsyncSession, code: str) -> dict | None:
    c = str(code).strip().upper()[:16]
    r = await session.execute(
        text(
            """
            SELECT code, attacker_character_id, defender_character_id, attacker_sticker_id, created_at
            FROM sticker_duel_challenges WHERE code = :c
            """,
        ),
        {"c": c},
    )
    row = r.mappings().first()
    return dict(row) if row else None


async def delete_challenge(session: AsyncSession, code: str) -> None:
    c = str(code).strip().upper()[:16]
    await session.execute(text("DELETE FROM sticker_duel_challenges WHERE code = :c"), {"c": c})
