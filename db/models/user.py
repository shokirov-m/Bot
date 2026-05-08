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

    # Уведомления в чат: появление / победа / побег золотого гоблина (мировой босс не зависит от этого).
    notify_golden_goblin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="1",
    )

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
    # Пригласившему уже выдано эпическое ожерелье за 5 приглашённых с уровнем ≥ 3.
    referral_five_l3_necklace_done: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
    )

    # 18+ контент: однократный выбор при первом вопросе.
    # adult_age_declared:
    #   - True  -> игрок подтвердил 18+
    #   - False -> игрок заявил, что ему нет 18 (навсегда запрещает 18+ контент)
    #   - None  -> ещё не отвечал (для старых пользователей / до внедрения)
    adult_age_declared: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # adult_content_enabled имеет смысл только при adult_age_declared=True
    adult_content_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    adult_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    adult_consent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
