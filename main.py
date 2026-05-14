"""
Точка входа бота «Башня Испытаний».
Запуск из каталога `tower_bot/`: python main.py
Или из родителя: python tower_bot/main.py (sys.path пополняется автоматически).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC
from pathlib import Path

# При запуске `python tower_bot/main.py` из родительской папки — добавляем корень проекта в путь
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from scheduler.tasks import bootstrap_golden_goblin_if_needed, setup_scheduler

from bot.handlers.admin import router as admin_router
from bot.handlers.auction import router as auction_router
from bot.handlers.arena import router as arena_router
from bot.handlers.city_quests import router as city_quests_router
from bot.handlers.class_arc import router as class_arc_router
from bot.handlers.daily import router as daily_router
from bot.handlers.economy_sinks import router as economy_sinks_router
from bot.handlers.leaderboard import router as leaderboard_router
from bot.handlers.gacha_broadcast_groups import router as gacha_broadcast_groups_router
from bot.handlers.black_market import router as black_market_router
from bot.handlers.home import router as home_router
from bot.handlers.menu import router as menu_router
from bot.handlers.sticker_duel import router as sticker_duel_router
from bot.handlers.settings import router as settings_router
from bot.handlers.combat import router as combat_router
from bot.handlers.forge import router as forge_router
from bot.handlers.workshop import router as workshop_router
from bot.handlers.coliseum import router as coliseum_router
from bot.handlers.city import router as city_router
from bot.handlers.floor import router as floor_router
from bot.handlers.forest_beginnings import router as forest_beginnings_router
from bot.handlers.quests import router as quests_router
from bot.handlers.tavern import router as tavern_router
from bot.handlers.inventory import router as inventory_router
from bot.handlers.clans import router as clans_router
from bot.handlers.profile import router as profile_router
from bot.handlers.titles import router as titles_router
from bot.handlers.shop import router as shop_router
from bot.handlers.start import router as start_router
from bot.handlers.stats_alloc import router as stats_alloc_router
from bot.handlers.tutorial import router as tutorial_router
from bot.handlers.floor_zero import router as floor_zero_router
from bot.middlewares.activity import ActivityMiddleware
from bot.middlewares.auth import RegistrationAuthMiddleware
from bot.middlewares.database import DbSessionMiddleware
from bot.middlewares.throttle import UserThrottleMiddleware
from config import settings
from db.database import ensure_sqlite_schema_or_migrate


def setup_logging() -> None:
    """Настройка loguru: уровень из конфига, вывод в stderr."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )


def _telegram_proxy_url() -> str | None:
    return (
        settings.TELEGRAM_PROXY_URL
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("ALL_PROXY")
        or os.environ.get("all_proxy")
        or None
    )


def _make_bot() -> Bot:
    proxy = _telegram_proxy_url()
    if proxy:
        logger.info("Запросы к Telegram идут через прокси (HTTPS_PROXY / TELEGRAM_PROXY_URL).")
        session = AiohttpSession(proxy=proxy)
        return Bot(
            token=settings.BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def _make_storage():
    redis_client = None
    if settings.REDIS_URL:
        from redis.asyncio import Redis
        from aiogram.fsm.storage.redis import RedisStorage

        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=False)
        storage = RedisStorage(redis=redis_client)
        logger.info("FSM хранится в Redis.")
    else:
        storage = MemoryStorage()
        logger.info(
            "FSM в памяти процесса (после перезапуска активные бои в Telegram не восстанавливаются; "
            "игрок видит старое сообщение — пусть откроет /floor).",
        )
    return redis_client, storage


def _register_update_middlewares(dp: Dispatcher) -> None:
    """Порядок: throttle → сессия БД → регистрация → учёт активности."""
    dp.update.middleware(UserThrottleMiddleware())
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(RegistrationAuthMiddleware())
    dp.update.middleware(ActivityMiddleware())


def _register_routers(dp: Dispatcher) -> None:
    # clans_router — /clan; forest_beginnings_router — flf:*; floor_router — fl:* и scr:* (скупщик).
    dp.include_router(start_router)
    dp.include_router(gacha_broadcast_groups_router)
    dp.include_router(floor_zero_router)
    dp.include_router(tutorial_router)
    dp.include_router(admin_router)
    dp.include_router(profile_router)
    dp.include_router(clans_router)
    dp.include_router(stats_alloc_router)
    dp.include_router(menu_router)
    dp.include_router(sticker_duel_router)
    dp.include_router(home_router)
    dp.include_router(black_market_router)
    dp.include_router(auction_router)
    dp.include_router(settings_router)
    dp.include_router(leaderboard_router)
    dp.include_router(titles_router)
    dp.include_router(inventory_router)
    dp.include_router(combat_router)
    dp.include_router(arena_router)
    dp.include_router(coliseum_router)
    dp.include_router(forge_router)
    dp.include_router(workshop_router)
    dp.include_router(economy_sinks_router)
    dp.include_router(tavern_router)
    dp.include_router(shop_router)
    dp.include_router(quests_router)
    dp.include_router(city_router)
    dp.include_router(city_quests_router)
    dp.include_router(class_arc_router)
    dp.include_router(forest_beginnings_router)
    dp.include_router(floor_router)
    dp.include_router(daily_router)


async def _polling_main() -> None:
    logger.info("Запуск «Башня Испытаний»…")
    logger.debug("БД: {}", settings.DB_PATH)

    redis_client, storage = _make_storage()
    bot = _make_bot()
    dp = Dispatcher(storage=storage)
    _register_update_middlewares(dp)
    _register_routers(dp)

    scheduler = AsyncIOScheduler(timezone=UTC)
    setup_scheduler(scheduler, bot)
    scheduler.start()
    asyncio.create_task(bootstrap_golden_goblin_if_needed(bot))

    from services.tier2_migration_service import run_tier2_reset
    asyncio.create_task(run_tier2_reset(bot))

    async def _purge_stamina_rations_startup() -> None:
        from services.inventory_purge_service import purge_stamina_rations_if_needed

        await purge_stamina_rations_if_needed()

    asyncio.create_task(_purge_stamina_rations_startup())

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        if redis_client is not None:
            await redis_client.aclose()


def _webhook_main() -> None:
    if not settings.WEBHOOK_BASE_URL.strip():
        raise SystemExit("WEBHOOK_ENABLED=true, но WEBHOOK_BASE_URL пустой.")

    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    logger.info("Режим webhook, база URL: {}", settings.WEBHOOK_BASE_URL)

    redis_client, storage = _make_storage()
    bot = _make_bot()
    dp = Dispatcher(storage=storage)
    _register_update_middlewares(dp)
    _register_routers(dp)

    scheduler = AsyncIOScheduler(timezone=UTC)
    setup_scheduler(scheduler, bot)

    webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
    secret = (settings.WEBHOOK_SECRET or "").strip() or None

    async def _start_jobs(b: Bot) -> None:
        await b.set_webhook(
            url=webhook_url,
            secret_token=secret,
            drop_pending_updates=True,
        )
        scheduler.start()
        logger.info("Webhook зарегистрирован у Telegram: {}", webhook_url)
        from scheduler.tasks import bootstrap_golden_goblin_if_needed
        from services.tier2_migration_service import run_tier2_reset

        asyncio.create_task(bootstrap_golden_goblin_if_needed(b))
        asyncio.create_task(run_tier2_reset(b))
        from services.inventory_purge_service import purge_stamina_rations_if_needed

        asyncio.create_task(purge_stamina_rations_if_needed())

    async def _stop_jobs(b: Bot) -> None:
        scheduler.shutdown(wait=False)
        await b.delete_webhook(drop_pending_updates=False)
        if redis_client is not None:
            await redis_client.aclose()

    dp.startup.register(_start_jobs)
    dp.shutdown.register(_stop_jobs)

    app = web.Application()
    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret,
        handle_in_background=True,
    )
    handler.register(app, path=settings.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(
        app,
        host=settings.WEBAPP_HOST,
        port=settings.WEBAPP_PORT,
    )


if __name__ == "__main__":
    try:
        setup_logging()
        ensure_sqlite_schema_or_migrate()
        if settings.WEBHOOK_ENABLED:
            _webhook_main()
        else:
            asyncio.run(_polling_main())
    except KeyboardInterrupt:
        logger.info("Остановка по Ctrl+C")
    except Exception:
        logger.exception("Критическая ошибка при работе бота")
