"""
Async-движок SQLite (aiosqlite), фабрика сессий и разрешение пути к БД.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

_TOWER_BOT_ROOT = Path(__file__).resolve().parent.parent


def patch_sqlite_characters_columns() -> None:
    """
    Добавить недостающие колонки в SQLite без полного alembic upgrade
    (для старых файлов БД после обновления кода).
    """
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            cols = {row[1] for row in con.execute("PRAGMA table_info(characters)").fetchall()}
            if not cols:
                return
            if "unspent_stat_points" not in cols:
                con.execute(
                    "ALTER TABLE characters ADD COLUMN unspent_stat_points INTEGER NOT NULL DEFAULT 0",
                )
                con.commit()
                logger.info("Патч SQLite: добавлена колонка characters.unspent_stat_points")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (characters) не удался: {}", p)


def patch_sqlite_users_referral_columns() -> None:
    """Колонки рефералки в users (старые БД без alembic upgrade)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            cols = {row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()}
            if not cols:
                return
            if "referred_by_user_id" not in cols:
                con.execute("ALTER TABLE users ADD COLUMN referred_by_user_id INTEGER")
                con.commit()
                logger.info("Патч SQLite: добавлена колонка users.referred_by_user_id")
            cols = {row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()}
            if "referral_l2_payout_done" not in cols:
                con.execute(
                    "ALTER TABLE users ADD COLUMN referral_l2_payout_done BOOLEAN NOT NULL DEFAULT 0",
                )
                con.commit()
                logger.info("Патч SQLite: добавлена колонка users.referral_l2_payout_done")
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_users_referred_by_user_id ON users (referred_by_user_id)",
            )
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (users referral) не удался: {}", p)


def patch_sqlite_promo_offers_table() -> None:
    """Таблица promo_offers (промокоды из админки)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='promo_offers'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE promo_offers (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    code_key VARCHAR(48) NOT NULL,
                    gold INTEGER NOT NULL DEFAULT 0,
                    xp INTEGER NOT NULL DEFAULT 0,
                    rune_stones INTEGER NOT NULL DEFAULT 0,
                    max_uses INTEGER,
                    uses_count INTEGER NOT NULL DEFAULT 0,
                    valid_from DATETIME NOT NULL,
                    valid_until DATETIME,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    note TEXT,
                    created_by_telegram_id BIGINT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (code_key)
                )
                """,
            )
            con.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_promo_offers_code_key ON promo_offers (code_key)",
            )
            con.commit()
            logger.info("Патч SQLite: создана таблица promo_offers")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (promo_offers) не удался: {}", p)


def patch_sqlite_promo_redemptions_table() -> None:
    """Создать promo_redemptions при отсутствии (старые БД без alembic upgrade)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='promo_redemptions'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE promo_redemptions (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code_key VARCHAR(48) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                    CONSTRAINT uq_promo_user_code UNIQUE (user_id, code_key)
                )
                """,
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_promo_redemptions_user_id ON promo_redemptions (user_id)",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_promo_redemptions_code_key ON promo_redemptions (code_key)",
            )
            con.commit()
            logger.info("Патч SQLite: создана таблица promo_redemptions")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (promo_redemptions) не удался: {}", p)


def patch_sqlite_app_global_table() -> None:
    """Создать app_global при отсутствии (миграция могла быть не применена вручную)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_global'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE app_global (
                    id INTEGER NOT NULL,
                    payload JSON NOT NULL DEFAULT '{}',
                    PRIMARY KEY (id)
                )
                """,
            )
            con.execute("INSERT OR IGNORE INTO app_global (id, payload) VALUES (1, '{}')")
            con.commit()
            logger.info("Патч SQLite: создана таблица app_global")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (app_global) не удался: {}", p)


def patch_sqlite_game_events_table() -> None:
    """Таблица game_events для метрик баланса (старые БД без alembic upgrade)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='game_events'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE game_events (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(32) NOT NULL,
                    floor INTEGER NOT NULL DEFAULT 0,
                    class_key VARCHAR(32) NOT NULL DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_game_events_event_type ON game_events (event_type)",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_game_events_created_at ON game_events (created_at)",
            )
            con.commit()
            logger.info("Патч SQLite: создана таблица game_events")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (game_events) не удался: {}", p)


def patch_sqlite_auction_lots_table() -> None:
    """Таблица auction_lots (старые БД без alembic upgrade)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='auction_lots'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE auction_lots (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    seller_char_id INTEGER NOT NULL,
                    item_data TEXT NOT NULL DEFAULT '{}',
                    start_price BIGINT NOT NULL DEFAULT 0,
                    current_bid BIGINT NOT NULL DEFAULT 0,
                    buyer_char_id INTEGER,
                    expires_at DATETIME NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(seller_char_id) REFERENCES characters (id) ON DELETE CASCADE,
                    FOREIGN KEY(buyer_char_id) REFERENCES characters (id) ON DELETE SET NULL
                )
                """,
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_auction_lots_seller_char_id ON auction_lots (seller_char_id)",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_auction_lots_buyer_char_id ON auction_lots (buyer_char_id)",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_auction_lots_status ON auction_lots (status)",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_auction_lots_expires_at ON auction_lots (expires_at)",
            )
            con.commit()
            logger.info("Патч SQLite: создана таблица auction_lots")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (auction_lots) не удался: {}", p)


def resolve_db_path() -> Path:
    """
    Абсолютный путь к файлу SQLite.
    Относительный DB_PATH резолвится от корня пакета tower_bot (рядом с main.py),
    чтобы совпадать с Alembic при запуске `python tower_bot/main.py` из родителя.
    """
    raw = Path(settings.DB_PATH).expanduser()
    path = raw if raw.is_absolute() else (_TOWER_BOT_ROOT / raw).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_async_database_url() -> str:
    """URL для create_async_engine (aiosqlite)."""
    path = resolve_db_path()
    # as_posix() даёт корректный путь в URL на Windows/Linux
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def get_sync_database_url() -> str:
    """Синхронный URL для Alembic (через run_sync поверх async-подключения не нужен отдельный файл)."""
    path = resolve_db_path()
    return f"sqlite:///{path.as_posix()}"


def ensure_sqlite_schema_or_migrate() -> None:
    """
    Если в файле БД нет таблицы users — применяет миграции Alembic
    через command.upgrade (тот же интерпретатор, cwd = tower_bot).
    Вызывать только из синхронного кода до asyncio.run(main()).
    """
    import os
    import sqlite3

    from alembic import command
    from alembic.config import Config
    from loguru import logger

    p = resolve_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    patch_sqlite_characters_columns()
    patch_sqlite_users_referral_columns()
    patch_sqlite_app_global_table()
    patch_sqlite_game_events_table()
    patch_sqlite_auction_lots_table()
    patch_sqlite_promo_redemptions_table()
    patch_sqlite_promo_offers_table()
    had_users = False
    if p.exists():
        try:
            con = sqlite3.connect(str(p))
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'",
            ).fetchone()
            con.close()
            had_users = row is not None
        except sqlite3.Error:
            logger.exception("Ошибка проверки SQLite: {}", p)
            raise

    if had_users:
        logger.debug("SQLite готова: {}", p)
        return

    ini = _TOWER_BOT_ROOT / "alembic.ini"
    if not ini.is_file():
        raise RuntimeError(f"Не найден {ini} — миграции недоступны.")

    logger.info("В {} нет таблицы users — Alembic upgrade head", p)
    old_cwd = os.getcwd()
    try:
        os.chdir(str(_TOWER_BOT_ROOT))
        cfg = Config(str(ini))
        command.upgrade(cfg, "head")
    except Exception as e:
        logger.exception("Alembic upgrade не удался")
        raise RuntimeError(
            "Не удалось создать таблицы БД. Из каталога tower_bot: python -m alembic upgrade head",
        ) from e
    finally:
        os.chdir(old_cwd)

    if not p.exists():
        raise RuntimeError(f"После миграций файл БД не найден: {p}")

    con = sqlite3.connect(str(p))
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'",
    ).fetchone()
    con.close()
    if row is None:
        raise RuntimeError(
            "После alembic таблица users отсутствует. Проверь DB_PATH и права на файл.",
        )
    logger.info("Миграции применены, схема БД готова ({}).", p)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Ленивая инициализация async-движка."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_async_database_url(),
            echo=False,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Фабрика async-сессий (для хендлеров и сервисов)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для выдачи сессии в рамках одного запроса.
    Использование: async for session in get_async_session(): ...
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
