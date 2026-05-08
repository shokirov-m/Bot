"""
/start: лор башни, пол героя, ник, портрет (3 варианта по полу), создание странника.
Класс — с 10 ур. у наставника на 11 этаже, подкласс — на 57.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.profile import clamp_profile_caption_for_photo
from bot.i18n import get_locale, resolve_locale_from_telegram, t
from bot.keyboards.menu_kb import main_menu_keyboard, main_menu_with_tutorial_hints
from bot.states.registration_states import RegistrationStates
from bot.utils.safe_media import safe_answer_photo
from db.models.user import User
from db.models.character import Character
from db.repository import character_repo, user_repo
from game.characters.classes import get_class_or_none
from services.character_service import create_character_for_user
from services.menu_hub_service import format_menu_hub_html, resolve_menu_hub_photo_path
from services.referral_service import bind_invitee_to_referrer, parse_referrer_telegram_id_from_start_text
from utils.profile_portraits import (
    GENDER_FEMALE,
    portrait_key_from_gender_slot,
    portrait_paths_for_gender_album,
)

router = Router(name="start")

ADULT_CONSENT_VERSION = 1


async def _answer_with_menu_hub_photo(
    message: Message,
    character: Character,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    """Главное меню с фото: портрет героя (или заглушка хаба), иначе текст."""
    p = resolve_menu_hub_photo_path(character)
    if p is not None:
        cap = clamp_profile_caption_for_photo(text)
        sent = await safe_answer_photo(
            message,
            p,
            caption=cap,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        if sent is not None:
            return
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )


TOWER_WAKE_LORE = (
    "🌫️ Ты в <b>башне из 100 этажей</b>: бои, стамина, экипировка, города. "
    "Смерть на этаже — со штрафом.\n\n"
)

GENDER_PROMPT = (
    "👤 <b>Кого создаём?</b> Выбери пол героя кнопками ниже — затем ник и портрет."
)

ADULT_GATE_PROMPT = (
    "🔞 <b>ВНИМАНИЕ 18+</b>\n\n"
    "В игре есть раздел с контентом для взрослых. Подтверди, что тебе <b>18+</b>.\n\n"
    "<i>Если выберешь «Мне нет 18», включить 18+ раздел позже будет невозможно.</i>"
)

NICK_PROMPT = (
    "✏️ <b>Ник</b> — одним сообщением, <b>2–24</b> символа: буквы, цифры, пробел, "
    "<code>-</code> <code>_</code>.\n"
    "<i>Пример:</i> <code>Тень_7</code>"
)

NAME_RE = re.compile(r"^[\w\u0400-\u04FF \-]{2,24}$", re.UNICODE)


def _adult_gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мне 18+", callback_data="reg:age:yes")],
            [InlineKeyboardButton(text="Мне нет 18", callback_data="reg:age:no")],
        ],
    )


def _gender_pick_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мужской герой", callback_data="reg:gender:male"),
                InlineKeyboardButton(text="Женский герой", callback_data="reg:gender:female"),
            ],
        ],
    )


def _portrait_pick_keyboard_three() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="reg:pf:1"),
                InlineKeyboardButton(text="2", callback_data="reg:pf:2"),
                InlineKeyboardButton(text="3", callback_data="reg:pf:3"),
            ],
        ],
    )


async def _send_portrait_step(message: Message, gender: str) -> None:
    """До трёх фото выбранного пола и кнопки 1–3; альбом только при 2+ файлах (ограничение Telegram)."""
    paths = portrait_paths_for_gender_album(gender)
    kb = _portrait_pick_keyboard_three()
    gen_word = "женский" if gender == GENDER_FEMALE else "мужской"
    cap = (
        f"📷 <b>Выбери портрет</b>\n"
        f"Три варианта <b>{gen_word}</b> облика — как на фото сверху вниз, кнопки <b>1–3</b>."
    )
    if len(paths) >= 2:
        media: list[InputMediaPhoto] = []
        for i, p in enumerate(paths):
            media.append(
                InputMediaPhoto(
                    media=FSInputFile(p),
                    caption=cap if i == 0 else None,
                    parse_mode=ParseMode.HTML if i == 0 else None,
                ),
            )
        try:
            await message.bot.send_media_group(chat_id=message.chat.id, media=media)
            await message.answer("Номер портрета:", reply_markup=kb)
        except Exception:
            logger.exception("send_media_group портретов: откат на одно фото")
            sent = await safe_answer_photo(
                message,
                paths[0],
                caption=cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            if sent is None:
                await message.answer(
                    cap + "\n\n<i>Не удалось отправить фото — выбери номер 1–3 по кнопкам.</i>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
    elif len(paths) == 1:
        sent = await safe_answer_photo(
            message,
            paths[0],
            caption=cap,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        if sent is None:
            await message.answer(
                cap + "\n\n<i>Файл портрета не отправился — выбери номер 1–3.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
    else:
        await message.answer(
            cap + "\n\n<i>Файлы портретов не найдены — выбери номер 1–3; положи PNG в "
            "<code>assets/images/profile/</code> (male_1…3 / female_1…3).</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )


async def _finish_new_character_registration(
    *,
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    display_name: str,
    portrait_key: str,
) -> None:
    data = await state.get_data()
    pend_gender = data.get("pending_gender")
    reg_gender = pend_gender if pend_gender in ("male", "female") else None
    char = await create_character_for_user(
        session,
        user=user,
        display_name=display_name,
        class_key="wanderer",
        portrait_key=portrait_key,
        reg_gender=reg_gender,
    )
    ref_tid = data.get("referrer_telegram_id")
    if isinstance(ref_tid, int) or (isinstance(ref_tid, str) and str(ref_tid).isdigit()):
        await bind_invitee_to_referrer(
            session,
            invitee_user=user,
            referrer_telegram_id=int(ref_tid),
        )
    cls = get_class_or_none("wanderer")
    assert cls is not None

    await state.clear()

    loc = resolve_locale_from_telegram(message.from_user.language_code if message.from_user else None)

    passive = html.escape(cls.passive_ru)
    if len(passive) > 100:
        passive = passive[:97] + "…"
    body = (
        f"⚔️ <b>{html.escape(char.display_name)}</b> {cls.emoji} <b>{cls.name_ru}</b>. "
        f"Старт: этаж <b>1</b>, открыто: <b>{char.highest_floor_reached}</b>.\n"
        f"<i>С 10 ур. класс у наставника на 11 этаже; подкласс на 57. Учебный бой и звание — с 1 этажа.</i>\n"
        f"<i>Пассив:</i> {passive}\n"
        f"<i>Навыки:</i> {cls.skill_1}, {cls.skill_2}, {cls.skill_3}\n\n"
        f"{format_menu_hub_html(char, locale=loc)}"
    )
    await _answer_with_menu_hub_photo(
        message,
        char,
        text=body,
        reply_markup=main_menu_with_tutorial_hints(locale=loc, character=char),
    )


def _normalize_nickname(raw: str) -> str | None:
    text = (raw or "").strip()
    if not text:
        return None
    if len(text) > 24:
        return None
    if not NAME_RE.match(text):
        return None
    return text[:64]


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Регистрация: пол, ник, портрет, затем создание странника."""
    try:
        if message.from_user is None:
            return

        tg = message.from_user
        user = await user_repo.ensure_user(session, tg.id, tg.username)

        if user.is_banned:
            reason = html.escape(user.ban_reason or "не указана")
            await message.answer(f"⛔ Доступ закрыт. Причина: <i>{reason}</i>")
            return

        character = await character_repo.get_by_user_id(session, user.id)
        if character is not None:
            await state.clear()
            loc = get_locale(character, tg.language_code)
            await _answer_with_menu_hub_photo(
                message,
                character,
                text=t(loc, "welcome_back") + "\n\n" + format_menu_hub_html(character, locale=loc),
                reply_markup=main_menu_keyboard(locale=loc, character=character),
            )
            return

        # 18+ вопрос задаём только новым героям. Для уже зарегистрированных — в настройках.
        if user.adult_age_declared is None:
            await state.clear()
            ref_tid = parse_referrer_telegram_id_from_start_text(message.text)
            if ref_tid is not None and ref_tid == int(tg.id):
                ref_tid = None
            await state.update_data(referrer_telegram_id=ref_tid)
            await message.answer(
                ADULT_GATE_PROMPT,
                parse_mode=ParseMode.HTML,
                reply_markup=_adult_gate_keyboard(),
            )
            return

        await state.set_state(RegistrationStates.waiting_gender)
        ref_tid = parse_referrer_telegram_id_from_start_text(message.text)
        if ref_tid is not None and ref_tid == int(tg.id):
            ref_tid = None
        await state.update_data(
            pending_display_name=None,
            pending_gender=None,
            referrer_telegram_id=ref_tid,
        )
        await message.answer(
            f"{TOWER_WAKE_LORE}{GENDER_PROMPT}",
            parse_mode=ParseMode.HTML,
            reply_markup=_gender_pick_keyboard(),
        )
    except Exception:
        logger.exception("Ошибка в обработчике /start")


@router.callback_query(F.data.in_({"reg:age:yes", "reg:age:no"}))
async def on_adult_gate_answer(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return

        user = await user_repo.ensure_user(session, callback.from_user.id, callback.from_user.username)
        if user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        # Если герой уже создан — возрастной выбор не трогаем тут (для таких — настройки).
        existing = await character_repo.get_by_user_id(session, user.id)
        if existing is not None:
            await callback.answer()
            return

        if user.adult_age_declared is None:
            want_adult = (callback.data or "") == "reg:age:yes"
            user.adult_age_declared = bool(want_adult)
            user.adult_content_enabled = bool(want_adult)
            if want_adult:
                user.adult_consent_at = datetime.now(timezone.utc)
                user.adult_consent_version = ADULT_CONSENT_VERSION
            else:
                user.adult_consent_at = None
                user.adult_consent_version = None
            await session.commit()

        # Продолжаем регистрацию: пол → ник → портрет.
        await state.set_state(RegistrationStates.waiting_gender)
        data = await state.get_data()
        ref_tid = data.get("referrer_telegram_id")
        await state.update_data(
            pending_display_name=None,
            pending_gender=None,
            referrer_telegram_id=ref_tid,
        )
        await callback.message.edit_text(
            f"{TOWER_WAKE_LORE}{GENDER_PROMPT}",
            parse_mode=ParseMode.HTML,
            reply_markup=_gender_pick_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка 18+ gate")
        await callback.answer("Ошибка. /start", show_alert=True)


@router.callback_query(StateFilter(RegistrationStates.waiting_gender), F.data.startswith("reg:gender:"))
async def on_gender_selected(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        raw = (callback.data or "").removeprefix("reg:gender:")
        if raw not in ("male", "female"):
            await callback.answer()
            return
        await state.update_data(pending_gender=raw)
        await state.set_state(RegistrationStates.waiting_nickname)
        await callback.message.answer(NICK_PROMPT, parse_mode=ParseMode.HTML)
        await callback.answer()
    except Exception:
        logger.exception("Ошибка при выборе пола")
        await callback.answer("Ошибка. /start", show_alert=True)


@router.message(StateFilter(RegistrationStates.waiting_gender), F.text)
async def on_gender_waiting_text(message: Message) -> None:
    if (message.text or "").strip().startswith("/"):
        await message.answer("Сначала нажми кнопку пола или /start.")
        return
    await message.answer(
        "Нажми кнопку «Мужской герой» или «Женский герой».",
        reply_markup=_gender_pick_keyboard(),
    )


@router.message(StateFilter(RegistrationStates.waiting_nickname), F.text)
async def on_nickname_entered(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """После ника — выбор портрета по полу, затем создание странника."""
    try:
        if message.from_user is None:
            return

        text = message.text or ""
        if text.startswith("/"):
            await message.answer(
                "Сейчас жду ник текстом. Либо пришли имя без слэша, либо нажми /start заново.",
            )
            return

        data = await state.get_data()
        gender = data.get("pending_gender")
        if gender not in ("male", "female"):
            await message.answer("Сначала выбери пол кнопками в сообщении выше или нажми /start.")
            return

        name = _normalize_nickname(text)
        if name is None:
            await message.answer(
                "Не подходит. Нужно 2–24 символа: буквы, цифры, пробел, «-» или «_».",
            )
            return

        user = await user_repo.ensure_user(session, message.from_user.id, message.from_user.username)
        if user.is_banned:
            await state.clear()
            await message.answer("⛔ Аккаунт заблокирован.")
            return

        existing = await character_repo.get_by_user_id(session, user.id)
        if existing is not None:
            await state.clear()
            loc = get_locale(existing, message.from_user.language_code if message.from_user else None)
            await message.answer(
                "У тебя уже есть герой. Используй меню ниже.",
                reply_markup=main_menu_keyboard(locale=loc, character=existing),
            )
            return

        await state.update_data(pending_display_name=name)
        await state.set_state(RegistrationStates.waiting_portrait)
        await _send_portrait_step(message, str(gender))
    except Exception:
        logger.exception("Ошибка при вводе ника")
        await message.answer("Ошибка. Попробуй /start.")


@router.message(StateFilter(RegistrationStates.waiting_portrait), F.text)
async def on_portrait_waiting_text(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip().startswith("/"):
        await message.answer("Сначала выбери портрет кнопкой 1–3 или нажми /start.")
        return
    await message.answer(
        "Нажми кнопку с номером портрета (1–3).",
        reply_markup=_portrait_pick_keyboard_three(),
    )


@router.callback_query(StateFilter(RegistrationStates.waiting_portrait), F.data.startswith("reg:pf:"))
async def on_portrait_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return

        raw = (callback.data or "").removeprefix("reg:pf:")
        if not raw.isdigit():
            await callback.answer()
            return
        slot = int(raw)
        data = await state.get_data()
        gender = data.get("pending_gender")
        if gender not in ("male", "female"):
            await state.clear()
            await callback.answer("Сессия устарела. Нажми /start.", show_alert=True)
            return
        portrait_key = portrait_key_from_gender_slot(str(gender), slot)
        if portrait_key is None:
            await callback.answer("Номер 1–3.", show_alert=True)
            return

        pending = data.get("pending_display_name")
        if not isinstance(pending, str) or not pending.strip():
            await state.clear()
            await callback.answer("Сессия устарела. Нажми /start.", show_alert=True)
            return

        user = await user_repo.ensure_user(session, callback.from_user.id, callback.from_user.username)
        if user.is_banned:
            await state.clear()
            await callback.answer("Аккаунт заблокирован.", show_alert=True)
            return

        existing = await character_repo.get_by_user_id(session, user.id)
        if existing is not None:
            await state.clear()
            await callback.answer("Герой уже создан.", show_alert=True)
            loc = get_locale(existing, callback.from_user.language_code)
            await callback.message.answer(
                "У тебя уже есть герой.",
                reply_markup=main_menu_keyboard(locale=loc, character=existing),
            )
            return

        await _finish_new_character_registration(
            message=callback.message,
            session=session,
            state=state,
            user=user,
            display_name=pending.strip(),
            portrait_key=portrait_key,
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка при выборе портрета")
        await callback.answer("Ошибка. /start", show_alert=True)


@router.callback_query(
    F.data.startswith("reg:pf:"),
    ~StateFilter(RegistrationStates.waiting_portrait),
)
async def on_portrait_stale_callback(callback: CallbackQuery) -> None:
    """Кнопки портрета вне шага регистрации (старое сообщение)."""
    await callback.answer("Меню регистрации устарело. Нажми /start.", show_alert=True)


@router.callback_query(
    F.data.startswith("reg:gender:"),
    ~StateFilter(RegistrationStates.waiting_gender),
)
async def on_gender_stale_callback(callback: CallbackQuery) -> None:
    """Кнопки пола вне шага регистрации."""
    await callback.answer("Меню регистрации устарело. Нажми /start.", show_alert=True)


@router.callback_query(F.data.startswith("reg:class:"))
async def on_outdated_class_callback(callback: CallbackQuery) -> None:
    """Старые сообщения с выбором класса при регистрации."""
    await callback.answer(
        "Регистрация обновлена: нажми /start — класс с 10 ур. у наставника на 11 этаже.",
        show_alert=True,
    )
