"""Наёмник персонажа (чёрный рынок «Тени Башни»)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from db.models.character import Character


class Mercenary(Base):
    __tablename__ = "mercenaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    race_key: Mapped[str] = mapped_column(String(32), nullable=False, server_default="human")
    class_role: Mapped[str] = mapped_column(String(24), nullable=False)
    rarity: Mapped[str] = mapped_column(String(24), nullable=False, server_default="common")
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    loyalty: Mapped[int] = mapped_column(Integer, nullable=False, server_default="40")
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    atk: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    character: Mapped["Character"] = relationship(back_populates="mercenaries")
