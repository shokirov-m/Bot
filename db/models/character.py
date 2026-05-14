"""
Персонаж игрока: класс, статы, этаж, опыт, золото, титул, элемент.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from db.models.floor_progress import FloorProgress
    from db.models.inventory import InventoryItem
    from db.models.mercenary import Mercenary
    from db.models.quest import QuestProgress
    from db.models.user import User


class Character(Base):
    __tablename__ = "characters"
    # floor_number индексируется отдельно (ТЗ: ускорение выборок по этажу)
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Публичный номер игрока (1, 2, 3… по порядку регистрации героев) — для арены и отображения.
    game_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True, index=True)

    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    class_key: Mapped[str] = mapped_column(String(32), nullable=False)

    # Базовые статы (СИЛ/ЛОВ/ИНТ/ВЫН/УДА) — имена полей без ключевых слов Python
    stat_strength: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stat_dexterity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stat_intelligence: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stat_vitality: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stat_luck: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    hp_current: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    mp_current: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    mp_max: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    stamina: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    last_stamina_regen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    floor_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", index=True)
    highest_floor_reached: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )

    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    unspent_stat_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    experience: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")

    gold: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    rune_stones: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    active_title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    element: Mapped[str | None] = mapped_column(String(24), nullable=True)

    # Счётчики для титулов и античита
    total_kills: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    death_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tavern_visits: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    enchant_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    runes_socketed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Стикер-дуэли: рейтинг и статистика (дублирует часть логики из meta для ТОПа)
    sticker_duel_rating: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1000")
    sticker_duel_wins: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sticker_duel_losses: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Ключи к 100 этажу и прочий прогресс — JSON для гибкости эндгейма
    meta_progress: Mapped[dict[str, Any]] = mapped_column(
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

    user: Mapped[User] = relationship(back_populates="character")
    inventory_items: Mapped[list[InventoryItem]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
    )
    floor_progress_rows: Mapped[list[FloorProgress]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
    )
    mercenaries: Mapped[list["Mercenary"]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
    )
    quests: Mapped[list[QuestProgress]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
    )
    enchant_logs: Mapped[list["EnchantLog"]] = relationship(
        "EnchantLog",
        back_populates="character",
        cascade="all, delete-orphan",
    )
