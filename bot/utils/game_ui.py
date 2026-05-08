"""Одно «якорное» сообщение для этажа / инвентаря (редактирование вместо спама)."""

from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.enums import ContentType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message
from loguru import logger

from bot.utils.safe_media import (
    normalize_animation_media,
    normalize_photo_media,
    normalize_video_media,
    safe_answer_animation,
    safe_answer_photo,
    safe_answer_video,
    safe_bot_edit_message_animation,
    safe_bot_edit_message_photo,
    safe_bot_edit_message_video,
    safe_delete_message,
    safe_edit_message_animation,
    safe_edit_message_photo,
    safe_edit_message_video,
    safe_send_animation,
    safe_send_photo,
    safe_send_video,
)
from utils.game_images_prefs import game_images_enabled

GAME_UI_CHAT_ID = "game_ui_chat_id"
GAME_UI_MESSAGE_ID = "game_ui_message_id"

# Сообщения, у которых контент правится через edit_message_caption, а не edit_message_text.
_CAPTION_CONTENT_TYPES = frozenset({
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.ANIMATION,
    ContentType.DOCUMENT,
    ContentType.AUDIO,
})


def _clamp_telegram_caption(text: str, *, limit: int = 1024) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 4)] + "\n…"


def _message_supports_caption_edit(message: Message) -> bool:
    ct = getattr(message, "content_type", None)
    return ct in _CAPTION_CONTENT_TYPES


async def edit_game_message_content(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
    disable_web_page_preview: bool | None = None,
) -> bool:
    """Текст или подпись к медиа — иначе при включённых картинках падает ``edit_text`` на медиа-сообщении."""
    try:
        if _message_supports_caption_edit(message):
            cap = _clamp_telegram_caption(text)
            await message.edit_caption(caption=cap, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            kw: dict = {"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode}
            if disable_web_page_preview is not None:
                kw["disable_web_page_preview"] = disable_web_page_preview
            await message.edit_text(**kw)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return True
        logger.warning("edit_game_message_content: {}", e)
        return False


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
    character: object | None = None,
) -> None:
    """
    Показать игровой экран: сначала правим target_message (колбэк), иначе якорь из FSM,
    иначе ответ на команду или новое сообщение в чат.

    Если задан ``photo_path`` и файл есть — сообщение с фото и подписью (HTML).
    При смене типа (текст ↔ фото) старое сообщение удаляется и отправляется новое.
    Отправка фото идёт через ``safe_send_photo`` / ``safe_edit_message_photo`` с откатом на текст при ошибке.

    Если передан ``character`` и в настройках выключены игровые картинки, ``photo_path`` игнорируется
    (как фон этажа и портрет в профиле).
    """
    if character is not None and photo_path is not None and not game_images_enabled(character):
        photo_path = None
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
        if _message_supports_caption_edit(target_message):
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
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "message is not modified" in err:
                return
            logger.debug("push_game_ui: якорь — не текст, пробуем подпись: {}", e)
            try:
                await bot.edit_message_caption(
                    chat_id=cid,
                    message_id=int(mid),
                    caption=_clamp_telegram_caption(text_kw["text"]),
                    reply_markup=text_kw["reply_markup"],
                    parse_mode=text_kw["parse_mode"],
                )
                return
            except TelegramBadRequest as e2:
                if "message is not modified" in str(e2).lower():
                    return
                logger.debug("push_game_ui: правка подписи якоря не вышла, шлём новое: {}", e2)
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


async def push_game_ui_animation(
    state: FSMContext,
    bot: Bot,
    *,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    target_message: Message | None = None,
    fallback_message: Message | None = None,
    animation_path: str | Path | None = None,
) -> None:
    """
    Упрощённый вариант push_game_ui для GIF/animation.
    Нужен для 18+ explicit: один якорь, но с анимацией.
    """
    p = normalize_animation_media(animation_path)
    text_kw: dict = {
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": ParseMode.HTML,
    }

    if target_message is not None and target_message.chat.id == chat_id:
        if p is not None:
            if getattr(target_message, "animation", None):
                if await safe_edit_message_animation(
                    target_message,
                    animation_path=p,
                    caption=text,
                    reply_markup=reply_markup,
                ):
                    await remember_game_ui_anchor(state, target_message)
                    return
            await safe_delete_message(bot, chat_id, target_message.message_id)
            sent = await safe_send_animation(
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
        # animation_path None -> fallback to text
        if _message_supports_caption_edit(target_message):
            await safe_delete_message(bot, chat_id, target_message.message_id)
            sent = await bot.send_message(chat_id=chat_id, **text_kw)
            await remember_game_ui_anchor(state, sent)
            return
        try:
            await target_message.edit_text(**text_kw)
            await remember_game_ui_anchor(state, target_message)
            return
        except TelegramBadRequest:
            logger.debug("push_game_ui_animation: edit target_message не вышел, пробуем якорь")

    data = await state.get_data()
    mid = data.get(GAME_UI_MESSAGE_ID)
    cid = data.get(GAME_UI_CHAT_ID)
    if mid is not None and cid == chat_id:
        if p is not None:
            if await safe_bot_edit_message_animation(
                bot,
                cid,
                int(mid),
                animation_path=p,
                caption=text,
                reply_markup=reply_markup,
            ):
                return
            await safe_delete_message(bot, cid, int(mid))
            sent = await safe_send_animation(
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
            pass
        await safe_delete_message(bot, cid, int(mid))
        sent = await bot.send_message(chat_id=chat_id, **text_kw)
        await remember_game_ui_anchor(state, sent)
        return

    if fallback_message is not None and fallback_message.chat.id == chat_id:
        if p is not None:
            sent = await safe_answer_animation(
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
        sent = await safe_send_animation(
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


async def push_game_ui_video(
    state: FSMContext,
    bot: Bot,
    *,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    target_message: Message | None = None,
    fallback_message: Message | None = None,
    video_path: str | Path | None = None,
) -> None:
    """push_game_ui для видео (MP4/WebM) через send_video/edit_message_media(InputMediaVideo)."""
    p = normalize_video_media(video_path)
    text_kw: dict = {
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": ParseMode.HTML,
    }

    if target_message is not None and target_message.chat.id == chat_id:
        if p is not None:
            if getattr(target_message, "video", None):
                if await safe_edit_message_video(
                    target_message,
                    video_path=p,
                    caption=text,
                    reply_markup=reply_markup,
                ):
                    await remember_game_ui_anchor(state, target_message)
                    return
            await safe_delete_message(bot, chat_id, target_message.message_id)
            sent = await safe_send_video(
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
        # video_path None -> fallback to text
        if _message_supports_caption_edit(target_message):
            await safe_delete_message(bot, chat_id, target_message.message_id)
            sent = await bot.send_message(chat_id=chat_id, **text_kw)
            await remember_game_ui_anchor(state, sent)
            return
        try:
            await target_message.edit_text(**text_kw)
            await remember_game_ui_anchor(state, target_message)
            return
        except TelegramBadRequest:
            logger.debug("push_game_ui_video: edit target_message не вышел, пробуем якорь")

    data = await state.get_data()
    mid = data.get(GAME_UI_MESSAGE_ID)
    cid = data.get(GAME_UI_CHAT_ID)
    if mid is not None and cid == chat_id:
        if p is not None:
            if await safe_bot_edit_message_video(
                bot,
                cid,
                int(mid),
                video_path=p,
                caption=text,
                reply_markup=reply_markup,
            ):
                return
            await safe_delete_message(bot, cid, int(mid))
            sent = await safe_send_video(
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
            pass
        await safe_delete_message(bot, cid, int(mid))
        sent = await bot.send_message(chat_id=chat_id, **text_kw)
        await remember_game_ui_anchor(state, sent)
        return

    if fallback_message is not None and fallback_message.chat.id == chat_id:
        if p is not None:
            sent = await safe_answer_video(
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
        sent = await safe_send_video(
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
