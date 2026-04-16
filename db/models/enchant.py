"""
Журнал попыток заточки (аналитика, античит, откаты).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from db.models.character import Character


class EnchantLog(Base):
    __tablename__ = "enchant_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("inventory_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    old_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    new_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    destroyed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    cost_gold: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    character: Mapped["Character"] = relationship(back_populates="enchant_logs")
