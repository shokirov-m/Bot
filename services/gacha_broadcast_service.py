"""
Уведомления в групповые чаты о выпадении материала 6★ из гачи мастерской.
Список chat_id хранится в AppGlobal(id=1).payload["gacha_star_broadcast_chat_ids"].
"""

from __future__ import annotations

import html
from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.app_global import AppGlobal
from db.models.character import Character
from db.repository import user_repo


PAYLOAD_KEY = "gacha_star_broadcast_chat_ids"


async def _ensure_app_row(session: AsyncSession) -> AppGlobal:
    row = await session.get(AppGlobal, 1)
    if row is None:
        row = AppGlobal(id=1, payload={})
        session.add(row)
        await session.flush()
    return row


def _chat_ids_from_payload(payload: dict[str, Any] | None) -> list[int]:
    raw = (payload or {}).get(PAYLOAD_KEY)
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


async def register_broadcast_chat(session: AsyncSession, chat_id: int) -> None:
    cid = int(chat_id)
    row = await _ensure_app_row(session)
    p = dict(row.payload or {})
    ids = set(_chat_ids_from_payload(p))
    ids.add(cid)
    p[PAYLOAD_KEY] = sorted(ids)
    row.payload = p
    flag_modified(row, "payload")
    await session.flush()


async def unregister_broadcast_chat(session: AsyncSession, chat_id: int) -> None:
    cid = int(chat_id)
    row = await _ensure_app_row(session)
    p = dict(row.payload or {})
    ids = set(_chat_ids_from_payload(p))
    ids.discard(cid)
    p[PAYLOAD_KEY] = sorted(ids)
    row.payload = p
    flag_modified(row, "payload")
    await session.flush()


async def notify_high_star_material(
    bot: Bot,
    session: AsyncSession,
    character: Character,
    *,
    stars: int,
    material_name: str,
    quantity: int = 1,
) -> None:
    """Рассылка при ⭐6+ (гача): в подписанные группы; если туда не удалось — в ЛС игроку."""
    if stars < 6:
        return
    row = await _ensure_app_row(session)
    chat_ids = _chat_ids_from_payload(dict(row.payload or {}))

    user = await user_repo.get_by_id(session, int(character.user_id))
    uname = (user.username or "").strip() if user is not None else ""
    dn = html.escape((character.display_name or "?").strip() or "?")
    mat = html.escape((material_name or "?").strip() or "?")
    star_label = min(int(stars), 9)
    qty = max(1, int(quantity))
    stars_emoji = "⭐" * min(star_label, 6)
    who = f"{stars_emoji} <b>{dn}</b>"
    if uname:
        who += f" (@{html.escape(uname)})"
    tail = f"— в <b>гаче мастерской</b> выпал материал <b>{mat}</b>"
    if qty > 1:
        tail += f" ×{qty}"
    tail += f" ({star_label}★)."
    text = f"🎰 {who} {tail}"

    sent_group = False
    for ch in chat_ids:
        try:
            await bot.send_message(int(ch), text, parse_mode=ParseMode.HTML)
            sent_group = True
        except Exception:
            logger.warning("gacha_broadcast: не удалось отправить в chat_id={}", ch)

    if sent_group:
        return

    # Нет подписанных чатов или все отправки в группы не удались — дублируем в личку игроку
    if not chat_ids:
        logger.info("gacha_broadcast: нет групп в рассылке — отправка 6★ в ЛС игроку")
    else:
        logger.warning(
            "gacha_broadcast: ни одна группа не приняла сообщение — пробуем ЛС игроку",
        )
    if user is None:
        logger.warning(
            "gacha_broadcast: 6★ без доставки — нет чатов в payload и нет user для ЛС (character_id={})",
            character.id,
        )
        return
    tg = int(user.telegram_id)
    try:
        await bot.send_message(tg, text, parse_mode=ParseMode.HTML)
        logger.info("gacha_broadcast: 6★ отправлено в ЛС telegram_id={}", tg)
    except Exception:
        logger.warning("gacha_broadcast: не удалось отправить в ЛС telegram_id={}", tg)

