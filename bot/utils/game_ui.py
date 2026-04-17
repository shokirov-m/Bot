"""Одно «якорное» сообщение для этажа / инвентаря (редактирование вместо спама)."""

from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message
from loguru import logger

from bot.utils.safe_media import (
    normalize_photo_media,
    safe_answer_photo,
    safe_bot_edit_message_photo,
    safe_delete_message,
    safe_edit_message_photo,
    safe_send_photo,
)

GAME_UI_CHAT_ID = "game_ui_chat_id"
GAME_UI_MESSAGE_ID = "game_ui_message_id"


async def remember_game_ui_anchor(state: FSMContext, message: Message) -> None:
    await state.update_data(
        **{GAME_UI_CHAT_ID: message.chat.id, GAME_UI_MESSAGE_ID: message.message_id},
    )


async def push_game_ui(
    state: FSMContext,
    bot: Bot,
    *,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    target_message: Message | None = None,
    fallback_message: Message | None = None,
    photo_path: str | Path | None = None,
) -> None:
    """
    Показать игровой экран: сначала правим target_message (колбэк), иначе якорь из FSM,
    иначе ответ на команду или новое сообщение в чат.

    Если задан ``photo_path`` и файл есть — сообщение с фото и подписью (HTML).
    При смене типа (текст ↔ фото) старое сообщение удаляется и отправляется новое.
    Отправка фото идёт через ``safe_send_photo`` / ``safe_edit_message_photo`` с откатом на текст при ошибке.
    """
    p = normalize_photo_media(photo_path)
    text_kw: dict = {
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": ParseMode.HTML,
    }

    if target_message is not None and target_message.chat.id == chat_id:
        if p is not None:
            if target_message.photo:
                if await safe_edit_message_photo(
                    target_message,
                    photo_path=p,
                    caption=text,
                    reply_markup=reply_markup,
                ):
                    await remember_game_ui_anchor(state, target_message)
                    return
            await safe_delete_message(bot, chat_id, target_message.message_id)
            sent = await safe_send_photo(
                bot,
                chat_id,
                p,
                caption=text,
                reply_markup=reply_markup,
            )
            if sent is not None:
                await remember_game_ui_anchor(state, sent)
                return
            sent = await bot.send_message(chat_id=chat_id, **text_kw)
            await remember_game_ui_anchor(state, sent)
            return
        if target_message.photo:
            await safe_delete_message(bot, chat_id, target_message.message_id)
            sent = await bot.send_message(chat_id=chat_id, **text_kw)
            await remember_game_ui_anchor(state, sent)
            return
        try:
            await target_message.edit_text(**text_kw)
            await remember_game_ui_anchor(state, target_message)
            return
        except TelegramBadRequest:
            logger.debug("push_game_ui: edit target_message не вышел, пробуем якорь")

    data = await state.get_data()
    mid = data.get(GAME_UI_MESSAGE_ID)
    cid = data.get(GAME_UI_CHAT_ID)
    if mid is not None and cid == chat_id:
        if p is not None:
            if await safe_bot_edit_message_photo(
                bot,
                cid,
                int(mid),
                photo_path=p,
                caption=text,
                reply_markup=reply_markup,
            ):
                return
            await safe_delete_message(bot, cid, int(mid))
            sent = await safe_send_photo(
                bot,
                chat_id,
                p,
                caption=text,
                reply_markup=reply_markup,
            )
            if sent is not None:
                await remember_game_ui_anchor(state, sent)
                return
            sent = await bot.send_message(chat_id=chat_id, **text_kw)
            await remember_game_ui_anchor(state, sent)
            return
        try:
            await bot.edit_message_text(chat_id=cid, message_id=int(mid), **text_kw)
            return
        except TelegramBadRequest:
            logger.debug("push_game_ui: якорь недоступен, шлём новое")
        await safe_delete_message(bot, cid, int(mid))
        sent = await bot.send_message(chat_id=chat_id, **text_kw)
        await remember_game_ui_anchor(state, sent)
        return

    if fallback_message is not None and fallback_message.chat.id == chat_id:
        if p is not None:
            sent = await safe_answer_photo(
                fallback_message,
                p,
                caption=text,
                reply_markup=reply_markup,
            )
            if sent is None:
                sent = await fallback_message.answer(**text_kw)
        else:
            sent = await fallback_message.answer(**text_kw)
        await remember_game_ui_anchor(state, sent)
        return

    if p is not None:
        sent = await safe_send_photo(
            bot,
            chat_id,
            p,
            caption=text,
            reply_markup=reply_markup,
        )
        if sent is None:
            sent = await bot.send_message(chat_id=chat_id, **text_kw)
    else:
        sent = await bot.send_message(chat_id=chat_id, **text_kw)
    await remember_game_ui_anchor(state, sent)
