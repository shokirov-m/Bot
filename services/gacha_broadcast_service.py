"""
Уведомления о выпадении материала 6★ из гачи мастерской.

Основной канал задаётся в настройках (GACHA_BROADCAST_CHAT, опционально GACHA_BROADCAST_MESSAGE_THREAD_ID
для темы в форуме, напр. t.me/tower_of_trial). Дополнительно — chat_id в AppGlobal.payload.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from config import settings
from db.models.app_global import AppGlobal
from db.models.character import Character
from db.repository import user_repo


PAYLOAD_KEY = "gacha_star_broadcast_chat_ids"


def _parse_broadcast_chat_id() -> int | str | None:
    """Username (@channel) или int chat_id; пусто в .env — None."""
    raw = str(settings.GACHA_BROADCAST_CHAT or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    return raw if raw.startswith("@") else f"@{raw}"


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
    """Рассылка при ⭐6+ (гача): сначала чат из настроек, иначе из БД, иначе ЛС игроку."""
    if stars < 6:
        return
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
    primary = _parse_broadcast_chat_id()
    thread_id = settings.GACHA_BROADCAST_MESSAGE_THREAD_ID
    if primary is not None and thread_id is None:
        logger.warning(
            "gacha_broadcast: GACHA_BROADCAST_MESSAGE_THREAD_ID не задан — в форуме сообщение "
            "уйдёт в общий раздел. Задай число из ссылки на тему: t.me/tower_of_trial/<ЭТО_ЧИСЛО>",
        )
    await send_tower_community_announcement(bot, session, character=character, html_text=text)


async def send_tower_community_announcement(
    bot: Bot,
    session: AsyncSession,
    *,
    character: Character,
    html_text: str,
) -> None:
    """
    Сообщение в те же каналы, что и гача 6★: GACHA_BROADCAST_CHAT (+ thread), затем группы из payload, затем ЛС.
    """
    row = await _ensure_app_row(session)
    chat_ids = _chat_ids_from_payload(dict(row.payload or {}))
    user = await user_repo.get_by_id(session, int(character.user_id))

    sent_group = False
    primary = _parse_broadcast_chat_id()
    thread_id = settings.GACHA_BROADCAST_MESSAGE_THREAD_ID
    if primary is not None:
        try:
            kwargs: dict[str, Any] = {"parse_mode": ParseMode.HTML}
            if thread_id is not None:
                kwargs["message_thread_id"] = int(thread_id)
            await bot.send_message(primary, html_text, **kwargs)
            return
        except Exception:
            logger.exception(
                "gacha_broadcast: не удалось отправить в основной чат {} (thread_id={})",
                primary,
                thread_id,
            )

    for ch in chat_ids:
        try:
            await bot.send_message(int(ch), html_text, parse_mode=ParseMode.HTML)
            sent_group = True
        except Exception:
            logger.warning("gacha_broadcast: не удалось отправить в chat_id={}", ch)

    if sent_group:
        return

    if user is None:
        logger.warning(
            "tower_announce: нет доставки — нет чатов и нет user (character_id={})",
            character.id,
        )
        return
    tg = int(user.telegram_id)
    try:
        await bot.send_message(tg, html_text, parse_mode=ParseMode.HTML)
        logger.info("tower_announce: отправлено в ЛС telegram_id={}", tg)
    except Exception:
        logger.warning("tower_announce: не удалось отправить в ЛС telegram_id={}", tg)


async def broadcast_sticker_pack_activity(
    bot: Bot,
    session: AsyncSession,
    *,
    html_text: str,
    sticker_file_ids: tuple[str, ...] = (),
    image_paths: tuple[str, ...] = (),
) -> None:
    """
    Крутка карточной гачи / итог дуэли — в те же цели, что и объявления гачи башни:
    сначала GACHA_BROADCAST_CHAT (+ ветка форума), затем chat_id из payload, без ЛС.
    """
    if not getattr(settings, "STICKER_MIRROR_TO_GACHA_CHAT", True):
        return
    primary = _parse_broadcast_chat_id()
    row = await _ensure_app_row(session)
    chat_ids = _chat_ids_from_payload(dict(row.payload or {}))
    if primary is None and not chat_ids:
        return

    msg_kw: dict[str, Any] = {"parse_mode": ParseMode.HTML}
    st_kw: dict[str, Any] = {}
    thread_id = settings.GACHA_BROADCAST_MESSAGE_THREAD_ID
    if thread_id is not None:
        tid = int(thread_id)
        msg_kw["message_thread_id"] = tid
        st_kw["message_thread_id"] = tid

    async def _post_to(chat: int | str) -> bool:
        try:
            for fid in sticker_file_ids:
                if not fid:
                    continue
                try:
                    await bot.send_sticker(chat, fid, **st_kw)
                except Exception:
                    logger.debug("sticker_broadcast: send_sticker failed chat={}", chat)
            for img_path in image_paths:
                if not img_path:
                    continue
                p = Path(img_path)
                if not p.is_file():
                    continue
                try:
                    await bot.send_photo(chat, FSInputFile(p), **st_kw)
                except Exception:
                    logger.debug("sticker_broadcast: send_photo failed chat={}", chat)
            await bot.send_message(chat, html_text, **msg_kw)
            return True
        except Exception:
            logger.warning("sticker_broadcast: send_message failed chat={}", chat)
            return False

    if primary is not None and await _post_to(primary):
        return
    for ch in chat_ids:
        if await _post_to(int(ch)):
            return

