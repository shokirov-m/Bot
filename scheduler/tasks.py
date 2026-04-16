"""
Задачи APScheduler: стамина, ежедневный сброс мета-полей, рейтинг, мировой босс.
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Регистрация всех фоновых задач (UTC)."""
    regen_secs = max(60, int(settings.STAMINA_REGEN_INTERVAL))

    async def job_world_boss() -> None:
        try:
            await task_world_boss_spawn(bot)
        except Exception:
            logger.exception("[WORLD_BOSS] Ошибка задачи")

    scheduler.add_job(
        task_stamina_regen,
        IntervalTrigger(seconds=regen_secs),
        id="tower_stamina_regen",
        replace_existing=True,
    )
    scheduler.add_job(
        task_daily_reset,
        CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="tower_daily_reset_utc",
        replace_existing=True,
    )
    scheduler.add_job(
        task_leaderboard_update,
        IntervalTrigger(hours=6),
        id="tower_leaderboard_tick",
        replace_existing=True,
    )
    scheduler.add_job(
        job_world_boss,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone="UTC"),
        id="tower_world_boss_spawn",
        replace_existing=True,
    )


async def task_stamina_regen() -> None:
    """Периодическое +1 стамины всем, кто ниже лимита."""
    from db.database import get_session_factory
    from game.economy import stamina as stamina_mod

    try:
        factory = get_session_factory()
        async with factory() as session:
            count = await stamina_mod.regen_stamina_all(session)
            await session.commit()
        logger.info("[STAMINA] Восстановлено у {} игроков", count)
    except Exception:
        logger.exception("[STAMINA] Ошибка задачи восстановления")


async def task_daily_reset() -> None:
    """
    Сброс ежедневных флагов в meta_progress одним UPDATE (SQLite json_set).
    Плюс финализация просроченных лотов аукциона.
    """
    from db.database import get_session_factory
    from services import economy_service

    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE characters
                    SET meta_progress = json_set(
                        json_set(
                            json_set(
                                COALESCE(meta_progress, '{}'),
                                '$.daily_battles_done',
                                0
                            ),
                            '$.daily_quest_taken',
                            0
                        ),
                        '$.tavern_used_today',
                        0
                    )
                    """,
                ),
            )
            auc_n = await economy_service.auction_finalize_lots(session)
            await session.commit()
        logger.info("[DAILY] Ежедневный сброс выполнен, аукцион закрыто лотов: {}", auc_n)
    except Exception:
        logger.exception("[DAILY] Ошибка ежедневного сброса")


async def task_leaderboard_update() -> None:
    """Рейтинг считается по запросу; здесь только метка в логах (кэш при появлении — сюда)."""
    try:
        logger.info("[LEADERBOARD] Рейтинг обновлён")
    except Exception:
        logger.exception("[LEADERBOARD] Ошибка задачи")


async def task_world_boss_spawn(bot: Bot) -> None:
    """
    Воскресенье 20:00 UTC: случайный этаж 50–80, HP от суммы этажей игроков, рассылка.
    """
    from db.database import get_session_factory
    from db.models.app_global import AppGlobal

    floor_n = random.randint(50, 80)
    now = datetime.now(UTC)
    iso_week = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"

    factory = get_session_factory()
    async with factory() as session:
        total_floors = await _sum_active_floors(session)
        hp = max(1, int(total_floors) * 150)
        payload = {
            "world_boss_floor": floor_n,
            "world_boss_hp": hp,
            "week": iso_week,
            "spawned_at": now.isoformat(),
        }
        row = await session.get(AppGlobal, 1)
        if row is None:
            session.add(AppGlobal(id=1, payload=payload))
        else:
            base = dict(row.payload or {})
            base.update(payload)
            row.payload = base
        await session.commit()

    text_msg = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👹 <b>МИРОВОЙ БОСС</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Появление на <b>этаже {floor_n}</b>!\n"
        f"Запас сил (HP пула): <b>{hp:,}</b>\n"
        f"Неделя: <code>{iso_week}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await _broadcast_html(bot, text_msg)
    logger.info("[WORLD_BOSS] Появился на этаже {}", floor_n)


async def _sum_active_floors(session: AsyncSession) -> int:
    from db.models.character import Character
    from db.models.user import User

    stmt = (
        select(func.coalesce(func.sum(Character.floor_number), 0))
        .select_from(Character)
        .join(User, Character.user_id == User.id)
        .where(User.is_banned.is_(False))
    )
    return int((await session.execute(stmt)).scalar_one())


async def _broadcast_html(bot: Bot, html: str) -> None:
    from db.database import get_session_factory
    from db.models.user import User

    factory = get_session_factory()
    async with factory() as session:
        res = await session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))
        ids = [int(r[0]) for r in res.all()]

    ok = 0
    for tid in ids:
        try:
            await bot.send_message(chat_id=tid, text=html, parse_mode="HTML")
            ok += 1
        except (TelegramForbiddenError, TelegramNotFound):
            pass
        except Exception:
            logger.exception("[WORLD_BOSS] Не удалось отправить игроку {}", tid)
        await asyncio.sleep(0.05)
    logger.info("[WORLD_BOSS] Уведомления отправлены: {}/{}", ok, len(ids))
