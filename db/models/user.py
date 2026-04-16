"""
Пользователь Telegram: бан, заглушка уведомлений, связь с персонажем.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from db.models.character import Character


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Рефералка: кто пригласил (users.id); после выплаты пригласившему за L2 приглашённого — True
    referred_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referral_l2_payout_done: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
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

    character: Mapped["Character | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
