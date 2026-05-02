"""CRUD и выборки по пользователям Telegram."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from loguru import logger

from db.models.user import User


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    """Найти пользователя по Telegram ID."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Пользователь по PK users.id."""
    result = await session.execute(select(User).where(User.id == int(user_id)))
    return result.scalar_one_or_none()


async def find_by_username_ci(session: AsyncSession, username: str) -> User | None:
    """Поиск по @username без учёта регистра (как в Telegram)."""
    u = username.strip().lstrip("@")
    if not u:
        return None
    result = await session.execute(
        select(User).where(
            User.username.isnot(None),
            func.lower(User.username) == u.lower(),
        ),
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    """Создать нового пользователя (без персонажа)."""
    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.flush()
    return user


async def ensure_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    """Вернуть существующего или создать нового пользователя."""
    user = await get_by_telegram_id(session, telegram_id)
    if user is not None:
        if username and user.username != username:
            user.username = username
        return user
    try:
        return await create_user(session, telegram_id, username)
    except IntegrityError:
        # Гонка: два /start подряд или параллельные апдейты — второй INSERT на тот же telegram_id.
        await session.rollback()
        user = await get_by_telegram_id(session, telegram_id)
        if user is None:
            logger.error(
                "ensure_user: UNIQUE telegram_id после rollback, строка не найдена tid={}",
                telegram_id,
            )
            raise RuntimeError("ensure_user: inconsistent DB state after IntegrityError") from None
        if username and user.username != username:
            user.username = username
        return user


async def count_users(session: AsyncSession) -> int:
    r = await session.execute(select(func.count()).select_from(User))
    return int(r.scalar_one() or 0)


async def count_banned_users(session: AsyncSession) -> int:
    r = await session.execute(select(func.count()).where(User.is_banned.is_(True)))
    return int(r.scalar_one() or 0)


async def set_ban_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
    *,
    banned: bool,
    reason: str | None = None,
) -> bool:
    """True если строка обновлена."""
    res = await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(is_banned=banned, ban_reason=(reason if banned else None)),
    )
    await session.flush()
    return res.rowcount > 0


async def list_telegram_ids_for_broadcast(session: AsyncSession) -> list[int]:
    """Все не забаненные (для рассылки; осторожно с лимитами Telegram)."""
    r = await session.execute(
        select(User.telegram_id).where(User.is_banned.is_(False)),
    )
    return [int(row[0]) for row in r.fetchall()]


async def list_telegram_ids_for_golden_goblin_broadcast(session: AsyncSession) -> list[int]:
    """Не забаненные, у кого включены оповещения о золотом гоблине."""
    r = await session.execute(
        select(User.telegram_id).where(
            User.is_banned.is_(False),
            User.notify_golden_goblin.is_(True),
        ),
    )
    return [int(row[0]) for row in r.fetchall()]


async def count_users_with_referrer(session: AsyncSession) -> int:
    """Сколько аккаунтов зарегистрировано с указанным пригласившим (referred_by_user_id не NULL)."""
    r = await session.execute(
        select(func.count()).select_from(User).where(User.referred_by_user_id.isnot(None)),
    )
    return int(r.scalar_one() or 0)


async def referral_registrations_by_inviter(
    session: AsyncSession,
    *,
    limit: int = 80,
) -> list[tuple[int, int, str | None, int]]:
    """
    Топ пригласивших: (users.id пригласившего, telegram_id, username, число приглашённых аккаунтов).
    """
    inviter = aliased(User)
    cnt = func.count(User.id).label("invite_count")
    stmt = (
        select(inviter.id, inviter.telegram_id, inviter.username, cnt)
        .select_from(User)
        .join(inviter, User.referred_by_user_id == inviter.id)
        .group_by(inviter.id, inviter.telegram_id, inviter.username)
        .order_by(cnt.desc(), inviter.id.asc())
        .limit(int(limit))
    )
    r = await session.execute(stmt)
    out: list[tuple[int, int, str | None, int]] = []
    for row in r.all():
        out.append((int(row[0]), int(row[1]), row[2], int(row[3])))
    return out
