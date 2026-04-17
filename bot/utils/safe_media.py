"""
Безопасная отправка и правка фото в Telegram (ошибки API, отсутствующий файл).
"""

from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InputMediaPhoto, Message
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


def _photo_input_file(photo: Path | str):
    if isinstance(photo, str) and photo.startswith(("http://", "https://")):
        return photo
    return FSInputFile(photo)


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def safe_edit_message_photo(
    message: Message,
    *,
    photo_path: Path | str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> bool:
    """Поменять медиа у сообщения с фото. False — нужен другой путь (удалить/отправить заново)."""
    try:
        media = InputMediaPhoto(
            media=_photo_input_file(photo_path),
            caption=caption,
            parse_mode=parse_mode,
        )
        await message.edit_media(media=media, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if _is_not_modified(e):
            return True
        logger.debug("safe_edit_message_photo: {}", e)
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
    parse_mode: ParseMode | str = ParseMode.HTML,
) -> Message | None:
    try:
        return await bot.send_photo(
            chat_id=chat_id,
            photo=_photo_input_file(photo_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        logger.warning("safe_send_photo TelegramBadRequest: {}", e)
        return None
    except OSError as e:
        logger.warning("safe_send_photo OSError (чтение файла): {}", e)
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
