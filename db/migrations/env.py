"""
Окружение Alembic: async SQLite (aiosqlite) через run_sync.
Путь импорта — корень `tower_bot/` (prepend_sys_path в alembic.ini).
"""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# tower_bot/ — два уровня вверх от db/migrations/env.py
_TOWER_BOT_ROOT = Path(__file__).resolve().parents[2]
if str(_TOWER_BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOWER_BOT_ROOT))

from db.base import Base  # noqa: E402
import db.models  # noqa: F401, E402 — регистрация таблиц в metadata
from db.database import get_async_database_url, get_sync_database_url  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерация SQL без подключения (синхронный URL SQLite)."""
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        get_async_database_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Онлайн-миграции через async-движок."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
