"""
Промокоды из админки: награды, лимит активаций, срок действия.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PromoOffer(Base):
    __tablename__ = "promo_offers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code_key: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)

    gold: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rune_stones: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # NULL = без лимита по количеству активаций
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # NULL = бессрочно после valid_from
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
