"""Лоты игрокового аукциона."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AuctionLot(Base):
    __tablename__ = "auction_lots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    seller_char_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )
    start_price: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    current_bid: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    buyer_char_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # active | sold | expired | cancelled
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
