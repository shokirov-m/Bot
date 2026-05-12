"""
Безопасная отправка и правка фото в Telegram (ошибки API, отсутствующий файл).
"""

from __future__ import annotations

import re
from pathlib import Path

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    FSInputFile,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from loguru import logger


def resolve_photo_path(photo_path: str | Path | None) -> Path | None:
    if photo_path is None:
        return None
    p = Path(photo_path)
    if not p.is_file():
        logger.warning("resolve_photo_path: файл не найден: {}", p)
        return None
    return p


def normalize_photo_media(photo_arg: str | Path | None) -> Path | str | None:
    """Локальный файл или HTTPS-URL для send_photo / edit_media."""
    if photo_arg is None:
        return None
    if isinstance(photo_arg, str) and photo_arg.startswith(("http://", "https://")):
        return photo_arg
    return resolve_photo_path(Path(photo_arg) if isinstance(photo_arg, str) else photo_arg)


def normalize_animation_media(anim_arg: str | Path | None) -> Path | str | None:
    """Локальный файл или HTTPS-URL для send_animation / edit_media."""
    # Для анимации нам достаточно тех же правил, что и для фото.
    return normalize_photo_media(anim_arg)


def normalize_video_media(video_arg: str | Path | None) -> Path | str | None:
    """Локальный файл или HTTPS-URL для send_video / edit_media."""
    return normalize_photo_media(video_arg)


def _animation_input_file(anim: Path | str):
    if isinstance(anim, str) and anim.startswith(("http://", "https://")):
        return anim
    return FSInputFile(anim)


def _photo_input_file(photo: Path | str):
    if isinstance(photo, str) and photo.startswith(("http://", "https://")):
        return photo
    return FSInputFile(photo)


def _video_input_file(video: Path | str):
    if isinstance(video, str) and video.startswith(("http://", "https://")):
        return video
    return FSInputFile(video)


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def safe_edit_message_photo(
    message: Message,
    *,
    photo_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
) -> bool:
    """Поменять медиа у сообщения с фото. False — нужен другой путь (удалить/отправить заново)."""
    try:
        kw_media: dict = {
            "media": _photo_input_file(photo_path),
            "caption": caption,
        }
        if parse_mode is not None:
            kw_media["parse_mode"] = parse_mode
        media = InputMediaPhoto(**kw_media)
        await message.edit_media(media=media, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_edit_message_photo: {}", e)
        if parse_mode is None:
            return False
        plain = re.sub(r"<[^>]+>", "", caption).strip() or "…"
        try:
            media = InputMediaPhoto(
                media=_photo_input_file(photo_path),
                caption=plain[:1024],
            )
            await message.edit_media(media=media, reply_markup=reply_markup)
            return True
        except TelegramBadRequest as e2:
            logger.debug("safe_edit_message_photo plain caption: {}", e2)
            return False


async def safe_bot_edit_message_photo(
    bot: Bot,
    chat_id: int,
    message_id: int,
    *,
    photo_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> bool:
    """edit_message_media по chat_id + message_id."""
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=_photo_input_file(photo_path),
                caption=caption,
                parse_mode=parse_mode,
            ),
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_bot_edit_message_photo: {}", e)
        return False


async def safe_send_photo(
    bot: Bot,
    chat_id: int,
    photo_path: Path | str,
    *,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str | None = ParseMode.HTML,
) -> Message | None:
    try:
        kw: dict = {
            "chat_id": chat_id,
            "photo": _photo_input_file(photo_path),
            "caption": caption,
            "reply_markup": reply_markup,
        }
        if parse_mode is not None:
            kw["parse_mode"] = parse_mode
        return await bot.send_photo(**kw)
    except TelegramBadRequest as e:
        logger.warning("safe_send_photo TelegramBadRequest: {}", e)
        if parse_mode is None:
            return None
        plain = re.sub(r"<[^>]+>", "", caption).strip() or "…"
        try:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=_photo_input_file(photo_path),
                caption=plain[:1024],
                reply_markup=reply_markup,
            )
        except TelegramBadRequest as e2:
            logger.warning("safe_send_photo plain caption retry: {}", e2)
            return None
    except OSError as e:
        logger.warning("safe_send_photo OSError (чтение файла): {}", e)
        return None


async def safe_edit_message_animation(
    message: Message,
    *,
    animation_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> bool:
    """Поменять медиа у сообщения на GIF/animation. False — нужен другой путь (удалить/отправить заново)."""
    try:
        media = InputMediaAnimation(
            media=_animation_input_file(animation_path),
            caption=caption,
            parse_mode=parse_mode,
        )
        await message.edit_media(media=media, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_edit_message_animation: {}", e)
        return False


async def safe_bot_edit_message_animation(
    bot: Bot,
    chat_id: int,
    message_id: int,
    *,
    animation_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> bool:
    """edit_message_media (animation) по chat_id + message_id."""
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaAnimation(
                media=_animation_input_file(animation_path),
                caption=caption,
                parse_mode=parse_mode,
            ),
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_bot_edit_message_animation: {}", e)
        return False


async def safe_send_animation(
    bot: Bot,
    chat_id: int,
    animation_path: Path | str,
    *,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> Message | None:
    try:
        return await bot.send_animation(
            chat_id=chat_id,
            animation=_animation_input_file(animation_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        logger.warning("safe_send_animation TelegramBadRequest: {}", e)
        return None
    except OSError as e:
        logger.warning("safe_send_animation OSError (чтение файла): {}", e)
        return None


async def safe_answer_animation(
    message: Message,
    animation_path: Path | str,
    *,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> Message | None:
    try:
        return await message.answer_animation(
            animation=_animation_input_file(animation_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        logger.warning("safe_answer_animation TelegramBadRequest: {}", e)
        return None
    except OSError as e:
        logger.warning("safe_answer_animation OSError: {}", e)
        return None


async def safe_edit_message_video(
    message: Message,
    *,
    video_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> bool:
    """Поменять медиа у сообщения на video. False — нужен другой путь (удалить/отправить заново)."""
    try:
        media = InputMediaVideo(
            media=_video_input_file(video_path),
            caption=caption,
            parse_mode=parse_mode,
        )
        await message.edit_media(media=media, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_edit_message_video: {}", e)
        return False


async def safe_bot_edit_message_video(
    bot: Bot,
    chat_id: int,
    message_id: int,
    *,
    video_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> bool:
    """edit_message_media (video) по chat_id + message_id."""
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaVideo(
                media=_video_input_file(video_path),
                caption=caption,
                parse_mode=parse_mode,
            ),
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_bot_edit_message_video: {}", e)
        return False


async def safe_send_video(
    bot: Bot,
    chat_id: int,
    video_path: Path | str,
    *,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> Message | None:
    try:
        return await bot.send_video(
            chat_id=chat_id,
            video=_video_input_file(video_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        logger.warning("safe_send_video TelegramBadRequest: {}", e)
        return None
    except OSError as e:
        logger.warning("safe_send_video OSError (чтение файла): {}", e)
        return None


async def safe_answer_video(
    message: Message,
    video_path: Path | str,
    *,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> Message | None:
    try:
        return await message.answer_video(
            video=_video_input_file(video_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        logger.warning("safe_answer_video TelegramBadRequest: {}", e)
        return None
    except OSError as e:
        logger.warning("safe_answer_video OSError: {}", e)
        return None


async def safe_answer_photo(
    message: Message,
    photo_path: Path | str,
    *,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> Message | None:
    try:
        return await message.answer_photo(
            photo=_photo_input_file(photo_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        logger.warning("safe_answer_photo TelegramBadRequest: {}", e)
        return None
    except OSError as e:
        logger.warning("safe_answer_photo OSError: {}", e)
        return None


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest as e:
        logger.debug("safe_delete_message: {}", e)
    except Exception as e:
        # Forbidden / network и т.д. — не рвём цепочку UI (якорь уже может указывать на новое сообщение)
        logger.warning("safe_delete_message: {}", e)
