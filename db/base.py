"""
Базовый класс моделей SQLAlchemy 2.0 (DeclarativeBase).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """База для всех ORM-моделей проекта."""

    pass
