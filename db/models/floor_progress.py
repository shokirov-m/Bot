"""
Дополнительный прогресс по этажам (посещения, боссы, тайные комнаты).
Текущий этаж персонажа хранится в characters.floor_number.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from db.models.character import Character


class FloorProgress(Base):
    __tablename__ = "floor_progress"
    __table_args__ = (
        UniqueConstraint("character_id", "floor_number", name="uq_floor_progress_char_floor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    floor_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    visits: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    mini_boss_defeated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    boss_defeated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    secret_rooms_found: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    character: Mapped["Character"] = relationship(back_populates="floor_progress_rows")
