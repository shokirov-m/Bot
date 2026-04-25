"""
Задачи APScheduler: стамина, ежедневный сброс мета-полей, рейтинг, мировой босс.
"""

from __future__ import annotations

import asyncio
import html
import random
import time
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings

_apscheduler: AsyncIOScheduler | None = None


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Регистрация всех фоновых задач (UTC)."""
    global _apscheduler
    _apscheduler = scheduler
    regen_secs = max(60, int(settings.STAMINA_REGEN_INTERVAL))
    passive_hp_mp_secs = max(60, int(settings.PASSIVE_HP_MP_INTERVAL_SECONDS))

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
        task_passive_hp_mp_full,
        IntervalTrigger(seconds=passive_hp_mp_secs),
        id="tower_passive_hp_mp",
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

    async def job_golden_goblin() -> None:
        try:
            await task_golden_goblin_tick(bot)
        except Exception:
            logger.exception("[GOLDEN_GOBLIN] Ошибка задачи")

    scheduler.add_job(
        job_golden_goblin,
        IntervalTrigger(hours=3),
        id="tower_golden_goblin",
        replace_existing=True,
    )

    async def job_golden_goblin_escape() -> None:
        try:
            await task_golden_goblin_escape_check(bot)
        except Exception:
            logger.exception("[GOLDEN_GOBLIN] Ошибка проверки побега")

    scheduler.add_job(
        job_golden_goblin_escape,
        IntervalTrigger(minutes=5),
        id="tower_golden_goblin_escape",
        replace_existing=True,
    )

    async def job_arena_season_rollover() -> None:
        try:
            from services.arena_service import ARENA_SEASON_ID

            logger.info(
                "[ARENA] Сезон %s: плановый тик (лиги/MMR в meta; награды сезона — вручную/позже).",
                ARENA_SEASON_ID,
            )
        except Exception:
            logger.exception("[ARENA] season tick")

    scheduler.add_job(
        job_arena_season_rollover,
        CronTrigger(day=1, hour=6, minute=0, timezone="UTC"),
        id="tower_arena_season_monthly",
        replace_existing=True,
    )


def schedule_rest_completion_notification(
    bot: Bot,
    *,
    chat_id: int,
    telegram_id: int,
    until: float,
) -> None:
    """Одноразовое уведомление в чат, когда истечёт rest_until_ts."""
    if _apscheduler is None:
        logger.warning("[REST] Планировщик не привязан — уведомление о передышке не запланировано")
        return
    run_at = datetime.fromtimestamp(until, tz=UTC)
    jid = f"rest_notify_{telegram_id}"

    async def _job() -> None:
        try:
            await deliver_rest_completion_notification(
                bot, chat_id=chat_id, telegram_id=telegram_id
            )
        except Exception:
            logger.exception("[REST] Ошибка задачи уведомления о передышке")

    _apscheduler.add_job(
        _job,
        DateTrigger(run_date=run_at),
        id=jid,
        replace_existing=True,
        misfire_grace_time=300,
    )


async def deliver_rest_completion_notification(
    bot: Bot, *, chat_id: int, telegram_id: int
) -> None:
    from bot.i18n import get_locale, t
    from db.database import get_session_factory
    from db.repository import character_repo, user_repo
    from services.rest_service import apply_completed_rest_if_needed

    try:
        factory = get_session_factory()
        async with factory() as session:
            user = await user_repo.get_by_telegram_id(session, telegram_id)
            if user is None or getattr(user, "is_banned", False):
                return
            char = await character_repo.get_by_user_id(session, user.id)
            if char is None:
                return
            loc = get_locale(char, None)
            applied = apply_completed_rest_if_needed(char)
            if not applied:
                mp = dict(char.meta_progress or {})
                raw_ts = mp.get("rest_until_ts")
                if raw_ts is None:
                    return
                try:
                    until2 = float(raw_ts)
                except (TypeError, ValueError):
                    return
                if time.time() < until2:
                    schedule_rest_completion_notification(
                        bot,
                        chat_id=chat_id,
                        telegram_id=telegram_id,
                        until=until2,
                    )
                    return
                return
            await session.commit()

        await bot.send_message(
            chat_id,
            t(loc, "rest_complete_notify"),
            parse_mode=ParseMode.HTML,
        )
    except (TelegramForbiddenError, TelegramNotFound):
        pass
    except Exception:
        logger.exception("[REST] Не удалось отправить уведомление о передышке")


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


async def task_passive_hp_mp_full() -> None:
    """
    Пассивное восстановление: периодически HP/MP → максимум (независимо от передышки).
    Активный бой идёт в FSM; здесь обновляется только строка персонажа в БД.
    """
    from db.database import get_session_factory

    try:
        factory = get_session_factory()
        async with factory() as session:
            res = await session.execute(
                text(
                    """
                    UPDATE characters
                    SET hp_current = hp_max, mp_current = mp_max
                    WHERE hp_current < hp_max OR mp_current < mp_max
                    """,
                ),
            )
            await session.commit()
            n = int(res.rowcount or 0)
        logger.info("[HP_MP] Пассивное восстановление до макс.: {} персонажей", n)
    except Exception:
        logger.exception("[HP_MP] Ошибка задачи пассивной регенерации")


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


async def bootstrap_golden_goblin_if_needed(bot: Bot) -> None:
    """При пустом app_global создаёт первую волну золотого гоблина и рассылает анонс."""
    from db.database import get_session_factory
    from services import golden_goblin_service

    try:
        factory = get_session_factory()
        async with factory() as session:
            created, fl, wave = await golden_goblin_service.ensure_initial_spawn(session)
            await session.commit()
        if created and fl is not None and wave is not None:
            await broadcast_golden_goblin_html(bot, int(fl), int(wave))
            logger.info("[GOLDEN_GOBLIN] Стартовая волна {} на этаже {}", wave, fl)
    except Exception:
        logger.exception("[GOLDEN_GOBLIN] Bootstrap")


async def broadcast_golden_goblin_html(bot: Bot, floor_n: int, wave: int) -> None:
    """Оповещение всем игрокам: появился золотой гоблин."""
    text_msg = (
        "🔔 <b>Оповещение башни</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Золотой гоблин</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Появился на <b>этаже {floor_n}</b>.\n"
        "Первый победитель получит <b>1000–2000</b> 💰 и <b>1000</b> опыта.\n"
        f"<i>Волна <code>{wave}</code>.</i>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await _broadcast_html(bot, text_msg)


async def broadcast_golden_goblin_slain(
    bot: Bot,
    *,
    winner_display_name: str,
) -> None:
    """Оповещение всем: первый победитель (ник из игры), гоблин исчез."""
    name_h = html.escape((winner_display_name or "").strip() or "Герой")
    text_msg = (
        "🔔 <b>Оповещение башни</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Золотой гоблин побеждён!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Первым победил: {name_h}.\n"
        "Гоблин исчез — событие закрыто.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await _broadcast_html(bot, text_msg)


async def task_golden_goblin_tick(bot: Bot) -> None:
    """Каждые 3 часа: новый случайный этаж 5–20 и рассылка."""
    from db.database import get_session_factory
    from services import golden_goblin_service

    factory = get_session_factory()
    async with factory() as session:
        wave, fl = await golden_goblin_service.roll_next_spawn(session)
        await session.commit()
    await broadcast_golden_goblin_html(bot, int(fl), int(wave))
    logger.info("[GOLDEN_GOBLIN] Новая волна {} на этаже {}", wave, fl)


async def task_golden_goblin_escape_check(bot: Bot) -> None:
    """
    Каждые 5 минут: проверяет, не сбежал ли золотой гоблин (30 мин без убийства).
    Если сбежал — рассылает оповещение всем.
    """
    from db.database import get_session_factory
    from services import golden_goblin_service

    factory = get_session_factory()
    async with factory() as session:
        escaped, fl = await golden_goblin_service.try_escape_if_timeout(session)
        await session.commit()

    if escaped:
        await broadcast_golden_goblin_escaped(bot, int(fl or 0))
        logger.info("[GOLDEN_GOBLIN] Гоблин сбежал с этажа {}", fl)


async def broadcast_golden_goblin_escaped(bot: Bot, floor_n: int) -> None:
    """Оповещение всем: золотой гоблин сбежал, никто не успел."""
    text_msg = (
        "🔔 <b>Оповещение башни</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💨 <b>Золотой гоблин сбежал!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Никто не успел поймать гоблина на <b>этаже {floor_n}</b>.\n"
        "<i>Хитрец исчез в тенях башни с полными карманами золота...</i>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await _broadcast_html(bot, text_msg)


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
