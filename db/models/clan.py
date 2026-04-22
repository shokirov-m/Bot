"""
Кланы: группа игроков, постройки, войны, захват этажей.
payload — гибкое JSON-хранилище (казна, постройки, реликвии, захват, война, лог).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Clan(Base):
    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tag: Mapped[str | None] = mapped_column(String(5), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    leader_character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    chat_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    clan_xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    clan_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    # Гибкое хранилище: казна, постройки, реликвии, захваченные этажи, война, лог событий
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ClanMembership(Base):
    __tablename__ = "clan_memberships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="member")
    contribution_points: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
