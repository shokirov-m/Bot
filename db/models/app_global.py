"""
Глобальное состояние приложения (одна строка id=1): мировой босс и т.п.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AppGlobal(Base):
    __tablename__ = "app_global"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )
