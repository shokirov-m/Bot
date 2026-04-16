"""Кланы: группа игроков, ссылка на чат, уровень по clan_xp."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Clan(Base):
    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    leader_character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    chat_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    clan_xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    clan_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


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
