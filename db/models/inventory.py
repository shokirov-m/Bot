"""
Предметы в сумке и в слотах экипировки; данные предмета в JSON.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from db.models.character import Character


class InventoryItem(Base):
    """
    Один экземпляр предмета.
    Слот сумки: bag_slot 0..19; экипировка: is_equipped + equip_slot.
    """

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_equipped: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    # weapon, armor, helmet, gloves, ring, amulet — если надето
    equip_slot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Индекс ячейки сумки (0–19); NULL если предмет только в экипировке
    bag_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Полное состояние: имя, редкость, статы, заточка, прочность, руны и т.д.
    item_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    character: Mapped["Character"] = relationship(back_populates="inventory_items")
