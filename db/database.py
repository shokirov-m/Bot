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


def patch_sqlite_character_game_id() -> None:
    """Публичный game_id у персонажей: порядковый номер для арены и UI."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='characters'",
            ).fetchone()
            if row is None:
                return
            cols = {r[1] for r in con.execute("PRAGMA table_info(characters)").fetchall()}
            if "game_id" not in cols:
                con.execute("ALTER TABLE characters ADD COLUMN game_id INTEGER")
                con.commit()
                logger.info("Патч SQLite: добавлена колонка characters.game_id")
            needs_fill = con.execute(
                "SELECT 1 FROM characters WHERE game_id IS NULL LIMIT 1",
            ).fetchone()
            if needs_fill:
                rows = con.execute("SELECT id FROM characters ORDER BY id").fetchall()
                for i, (cid,) in enumerate(rows, start=1):
                    con.execute("UPDATE characters SET game_id = ? WHERE id = ?", (i, cid))
                con.commit()
                logger.info("Патч SQLite: заполнен game_id для {} персонажей", len(rows))
            try:
                con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_characters_game_id ON characters (game_id)")
                con.commit()
            except sqlite3.Error:
                logger.debug("Индекс game_id: пропуск ({})", p)
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (character game_id) не удался: {}", p)


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
            cols = {row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()}
            if "referral_five_l3_necklace_done" not in cols:
                con.execute(
                    "ALTER TABLE users ADD COLUMN referral_five_l3_necklace_done BOOLEAN NOT NULL DEFAULT 0",
                )
                con.commit()
                logger.info("Патч SQLite: добавлена колонка users.referral_five_l3_necklace_done")
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_users_referred_by_user_id ON users (referred_by_user_id)",
            )
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (users referral) не удался: {}", p)


def patch_sqlite_users_notify_golden_goblin() -> None:
    """Колонка users.notify_golden_goblin (оповещения о золотом гоблине)."""
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
            if "notify_golden_goblin" not in cols:
                con.execute(
                    "ALTER TABLE users ADD COLUMN notify_golden_goblin BOOLEAN NOT NULL DEFAULT 1",
                )
                con.commit()
                logger.info("Патч SQLite: добавлена колонка users.notify_golden_goblin")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (users notify_golden_goblin) не удался: {}", p)


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


def patch_sqlite_auction_lots_target_char_id() -> None:
    """Колонка target_char_id — личные предложения на аукционе."""
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
            if row is None:
                return
            cols = {r[1] for r in con.execute("PRAGMA table_info(auction_lots)").fetchall()}
            if "target_char_id" in cols:
                return
            con.execute(
                "ALTER TABLE auction_lots ADD COLUMN target_char_id INTEGER "
                "REFERENCES characters(id) ON DELETE SET NULL",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_auction_lots_target_char_id ON auction_lots (target_char_id)",
            )
            con.commit()
            logger.info("Патч SQLite: auction_lots.target_char_id")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (auction_lots.target_char_id) не удался: {}", p)


def patch_sqlite_clans_tables() -> None:
    """Таблицы кланов (базовый уровень: создание, участники, XP)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clans'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE clans (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL UNIQUE,
                    leader_character_id INTEGER NOT NULL,
                    chat_url VARCHAR(256),
                    clan_xp INTEGER NOT NULL DEFAULT 0,
                    clan_level INTEGER NOT NULL DEFAULT 1
                )
                """,
            )
            con.execute(
                """
                CREATE TABLE clan_memberships (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    clan_id INTEGER NOT NULL,
                    character_id INTEGER NOT NULL UNIQUE,
                    role VARCHAR(16) NOT NULL DEFAULT 'member'
                )
                """,
            )
            con.execute("CREATE INDEX IF NOT EXISTS ix_clan_memberships_clan_id ON clan_memberships (clan_id)")
            con.commit()
            logger.info("Патч SQLite: созданы таблицы clans и clan_memberships")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (clans) не удался: {}", p)


def patch_sqlite_clans_extended_columns() -> None:
    """Расширенные колонки кланов: tag, description, payload, contribution_points, joined_at, last_active_at."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            # --- clans ---
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clans'"
            ).fetchone()
            if row is None:
                return  # таблица ещё не создана — patch_sqlite_clans_tables сделает это
            cols = {r[1] for r in con.execute("PRAGMA table_info(clans)").fetchall()}
            if "tag" not in cols:
                con.execute("ALTER TABLE clans ADD COLUMN tag VARCHAR(5)")
                con.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_clans_tag ON clans (tag)"
                )
                con.commit()
                logger.info("Патч SQLite: clans.tag")
            if "description" not in cols:
                con.execute("ALTER TABLE clans ADD COLUMN description TEXT")
                con.commit()
                logger.info("Патч SQLite: clans.description")
            if "payload" not in cols:
                con.execute("ALTER TABLE clans ADD COLUMN payload JSON NOT NULL DEFAULT '{}'")
                con.commit()
                logger.info("Патч SQLite: clans.payload")
            if "created_at" not in cols:
                con.execute("ALTER TABLE clans ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
                con.commit()
                logger.info("Патч SQLite: clans.created_at")

            # --- clan_memberships ---
            row2 = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clan_memberships'"
            ).fetchone()
            if row2 is None:
                return
            mcols = {r[1] for r in con.execute("PRAGMA table_info(clan_memberships)").fetchall()}
            if "contribution_points" not in mcols:
                con.execute(
                    "ALTER TABLE clan_memberships ADD COLUMN contribution_points BIGINT NOT NULL DEFAULT 0"
                )
                con.commit()
                logger.info("Патч SQLite: clan_memberships.contribution_points")
            if "joined_at" not in mcols:
                con.execute("ALTER TABLE clan_memberships ADD COLUMN joined_at DATETIME")
                con.commit()
                logger.info("Патч SQLite: clan_memberships.joined_at")
            if "last_active_at" not in mcols:
                con.execute("ALTER TABLE clan_memberships ADD COLUMN last_active_at DATETIME")
                con.commit()
                logger.info("Патч SQLite: clan_memberships.last_active_at")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (clans extended) не удался: {}", p)


def patch_sqlite_stored_gear_boost_v3() -> None:
    """
    Одноразово усилить defense и статы в JSON экипировки в сумке/слотах и на лотах аукциона.
    Флаг в app_global.payload.gear_stats_boost_v3 — не повторять.
    """
    import json
    import sqlite3

    from loguru import logger

    from game.items.rarity_scaling import apply_stored_gear_balance_boost_v3

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        with sqlite3.connect(str(p)) as con:
            row_tbl = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_global'",
            ).fetchone()
            if row_tbl is None:
                return
            con.execute("INSERT OR IGNORE INTO app_global (id, payload) VALUES (1, '{}')")
            row = con.execute("SELECT payload FROM app_global WHERE id = 1").fetchone()
            raw_payload = row[0] if row else "{}"
            try:
                payload = json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload or {})
            except json.JSONDecodeError:
                payload = {}
            if payload.get("gear_stats_boost_v3"):
                return

            def _loads_item_data(raw: object) -> dict[str, object]:
                if raw is None:
                    return {}
                if isinstance(raw, dict):
                    return dict(raw)
                if isinstance(raw, str):
                    try:
                        return dict(json.loads(raw))
                    except json.JSONDecodeError:
                        return {}
                return {}

            n_inv = 0
            if con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='inventory_items'",
            ).fetchone():
                for iid, raw in con.execute("SELECT id, item_data FROM inventory_items"):
                    d = _loads_item_data(raw)
                    new_d, changed = apply_stored_gear_balance_boost_v3(d)
                    if changed:
                        con.execute(
                            "UPDATE inventory_items SET item_data = ? WHERE id = ?",
                            (json.dumps(new_d, ensure_ascii=False), int(iid)),
                        )
                        n_inv += 1

            n_lot = 0
            if con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='auction_lots'",
            ).fetchone():
                for lid, raw in con.execute("SELECT id, item_data FROM auction_lots"):
                    d = _loads_item_data(raw)
                    new_d, changed = apply_stored_gear_balance_boost_v3(d)
                    if changed:
                        con.execute(
                            "UPDATE auction_lots SET item_data = ? WHERE id = ?",
                            (json.dumps(new_d, ensure_ascii=False), int(lid)),
                        )
                        n_lot += 1

            payload["gear_stats_boost_v3"] = True
            con.execute(
                "UPDATE app_global SET payload = ? WHERE id = 1",
                (json.dumps(payload, ensure_ascii=False),),
            )
            if n_inv or n_lot:
                logger.info(
                    "Патч SQLite gear_stats_boost_v3: inventory_items={}, auction_lots={}",
                    n_inv,
                    n_lot,
                )
    except sqlite3.Error:
        logger.exception("Патч SQLite (gear_stats_boost_v3) не удался: {}", p)


def patch_sqlite_unequip_boots_cloak() -> None:
    """Снять сапоги/плащ с экипировки (слоты удалены из игры) — предметы в сумку."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row_tbl = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='inventory_items'",
            ).fetchone()
            if row_tbl is None:
                return
            rows = con.execute(
                "SELECT id, character_id FROM inventory_items "
                "WHERE is_equipped = 1 AND equip_slot IN ('boots', 'cloak')",
            ).fetchall()
            for iid, cid in rows:
                r = con.execute(
                    "SELECT COALESCE(MAX(bag_slot), -1) FROM inventory_items "
                    "WHERE character_id = ? AND bag_slot IS NOT NULL",
                    (int(cid),),
                ).fetchone()
                next_slot = int(r[0]) + 1
                con.execute(
                    "UPDATE inventory_items SET is_equipped = 0, equip_slot = NULL, bag_slot = ? "
                    "WHERE id = ?",
                    (next_slot, int(iid)),
                )
            con.commit()
            if rows:
                logger.info("Патч SQLite: сапоги/плащ сняты с экипировки ({} шт.)", len(rows))
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (unequip boots/cloak) не удался: {}", p)


def patch_sqlite_workshop_orders_table() -> None:
    """Таблица заказов городской кузницы (эскроу, мастер-плательщик)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workshop_orders'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE workshop_orders (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    order_type VARCHAR(16) NOT NULL DEFAULT 'open',
                    customer_char_id INTEGER NOT NULL,
                    crafter_char_id INTEGER,
                    recipe_id VARCHAR(64) NOT NULL,
                    qty INTEGER NOT NULL DEFAULT 1,
                    escrow_gold INTEGER NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'posted',
                    deadline_at VARCHAR(40),
                    created_at VARCHAR(40) NOT NULL,
                    updated_at VARCHAR(40) NOT NULL
                )
                """,
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_workshop_orders_status ON workshop_orders (status)",
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_workshop_orders_customer "
                "ON workshop_orders (customer_char_id)",
            )
            con.commit()
            logger.info("Патч SQLite: создана таблица workshop_orders")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (workshop_orders) не удался: {}", p)


def patch_sqlite_mercenaries_table() -> None:
    """Таблица наёмников (чёрный рынок)."""
    import sqlite3

    from loguru import logger

    p = resolve_db_path()
    if not p.exists():
        return
    try:
        con = sqlite3.connect(str(p))
        try:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mercenaries'",
            ).fetchone()
            if row is not None:
                return
            con.execute(
                """
                CREATE TABLE mercenaries (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    display_name VARCHAR(64) NOT NULL,
                    race_key VARCHAR(32) NOT NULL DEFAULT 'human',
                    class_role VARCHAR(24) NOT NULL,
                    rarity VARCHAR(24) NOT NULL DEFAULT 'common',
                    level INTEGER NOT NULL DEFAULT 1,
                    loyalty INTEGER NOT NULL DEFAULT 40,
                    hp_max INTEGER NOT NULL DEFAULT 100,
                    atk INTEGER NOT NULL DEFAULT 10,
                    extra JSON NOT NULL DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(character_id) REFERENCES characters (id) ON DELETE CASCADE
                )
                """,
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS ix_mercenaries_character_id ON mercenaries (character_id)",
            )
            con.commit()
            logger.info("Патч SQLite: создана таблица mercenaries")
        finally:
            con.close()
    except sqlite3.Error:
        logger.exception("Патч SQLite (mercenaries) не удался: {}", p)


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
    patch_sqlite_character_game_id()
    patch_sqlite_users_referral_columns()
    patch_sqlite_users_notify_golden_goblin()
    patch_sqlite_app_global_table()
    patch_sqlite_game_events_table()
    patch_sqlite_auction_lots_table()
    patch_sqlite_auction_lots_target_char_id()
    patch_sqlite_promo_redemptions_table()
    patch_sqlite_promo_offers_table()
    patch_sqlite_clans_tables()
    patch_sqlite_clans_extended_columns()
    patch_sqlite_stored_gear_boost_v3()
    patch_sqlite_unequip_boots_cloak()
    patch_sqlite_workshop_orders_table()
    patch_sqlite_mercenaries_table()
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
