"""
Улица красных фонарей (18+) — доступна только в городе 31 этажа.

Explicit-контент (откровенные тексты) — только для админа и хранится в data-файле.
Для не-админов explicit раздел показывает teaser и сообщение о закрытии.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.city_kb import city_hub_keyboard
from bot.utils.game_art import menu_city_photo_path
from bot.utils.game_ui import push_game_ui
from config import is_admin as config_is_admin
from db.repository import character_repo, user_repo
from game.floors import floor_data
from services.floor_service import format_city_hub_message

router = Router(name="red_light")

FLOOR_KEY = 31
EXPLICIT_DATA_PATH = Path(__file__).resolve().parents[2] / "game" / "data" / "red_light_explicit_ru.json"
SAFE_DATA_PATH = Path(__file__).resolve().parents[2] / "game" / "data" / "red_light_safe_ru.json"
EXPLICIT_IMAGE_DIR = Path(__file__).resolve().parents[2] / "game" / "assets" / "red_light" / "explicit"
META_KEY = "red_light_v1"
EXPLICIT_ROOT_ID = "root"


def _rl_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Safe-ивент", callback_data=f"rl:safe:{FLOOR_KEY}")],
            [InlineKeyboardButton(text="🚪 Закрытая дверь (explicit)", callback_data=f"rl:explicit:{FLOOR_KEY}")],
            [InlineKeyboardButton(text="⬅️ В город", callback_data=f"rl:back:{FLOOR_KEY}")],
        ],
    )


def _explicit_locked_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rl:hub:{FLOOR_KEY}")],
            [InlineKeyboardButton(text="⬅️ В город", callback_data=f"rl:back:{FLOOR_KEY}")],
        ],
    )


def _load_explicit_scenes() -> list[dict]:
    if not EXPLICIT_DATA_PATH.is_file():
        return []
    try:
        raw = json.loads(EXPLICIT_DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
    except Exception:
        logger.exception("red_light: explicit json load failed")
    return []


def _index_by_id(items: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for it in items:
        k = str(it.get("id") or "").strip()
        if k:
            out[k] = it
    return out


def _explicit_kb(scene: dict) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    choices = scene.get("choices")
    if isinstance(choices, list):
        for ch in choices[:10]:
            if not isinstance(ch, dict):
                continue
            label = str(ch.get("label") or "").strip()
            nxt = str(ch.get("next") or "").strip()
            if not label or not nxt:
                continue
            rows.append([InlineKeyboardButton(text=label[:64], callback_data=f"rl:ex:{FLOOR_KEY}:{nxt}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rl:hub:{FLOOR_KEY}")])
    rows.append([InlineKeyboardButton(text="⬅️ В город", callback_data=f"rl:back:{FLOOR_KEY}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _explicit_photo_path(scene: dict) -> str | None:
    image_name = str(scene.get("image") or "").strip()
    if not image_name:
        return None
    p = EXPLICIT_IMAGE_DIR / image_name
    return str(p) if p.is_file() else None


def _explicit_render(scene: dict) -> str:
    title = str(scene.get("title") or "Закрытая дверь").strip()
    body = str(scene.get("text") or "").strip() or "<i>(пусто)</i>"
    return f"🚪 <b>{title}</b> (admin)\n\n{body}"

def _load_safe_events() -> list[dict]:
    if not SAFE_DATA_PATH.is_file():
        return []
    try:
        raw = json.loads(SAFE_DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
    except Exception:
        logger.exception("red_light: safe json load failed")
    return []


def _adult_gate_status_text(user) -> str | None:
    if user.adult_age_declared is False:
        return "⛔ Этот раздел доступен только совершеннолетним."
    if user.adult_age_declared is None:
        return "🔞 Для доступа подтверди 18+ в настройках (/settings)."
    if user.adult_content_enabled is False:
        return "🔞 18+ контент отключён. Включи в настройках (/settings)."
    return None


def _safe_event_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Ещё событие", callback_data=f"rl:safe_roll:{FLOOR_KEY}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rl:hub:{FLOOR_KEY}")],
            [InlineKeyboardButton(text="⬅️ В город", callback_data=f"rl:back:{FLOOR_KEY}")],
        ],
    )


def _apply_safe_event_outcome(char, event: dict) -> str:
    """
    Safe-ивенты: без explicit текста. Дают небольшие изменения (репутация квартала / золото).
    Всё хранится в character.meta_progress[META_KEY].
    """
    mp = dict(getattr(char, "meta_progress", None) or {})
    st = dict(mp.get(META_KEY) or {})
    rep = int(st.get("rep", 0) or 0)
    gold_delta = int(event.get("gold_delta", 0) or 0)
    rep_delta = int(event.get("rep_delta", 0) or 0)
    rep = max(-100, min(100, rep + rep_delta))
    st["rep"] = rep
    st["last_event_id"] = str(event.get("id") or "")
    mp[META_KEY] = st
    char.meta_progress = mp
    if gold_delta:
        char.gold = max(0, int(getattr(char, "gold", 0) or 0) + gold_delta)
    tail = []
    if rep_delta:
        tail.append(f"🏮 Репутация квартала: <b>{rep:+d}</b>")
    if gold_delta:
        tail.append(f"💰 Золото: <b>{gold_delta:+d}</b>")
    return "\n".join(tail)


def _pick_safe_event(events: list[dict], *, seed: int) -> dict | None:
    if not events:
        return None
    rng = random.Random(seed)
    return rng.choice(events)


@router.callback_query(F.data == f"rl:hub:{FLOOR_KEY}")
async def rl_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        if int(char.floor_number) != FLOOR_KEY:
            await callback.answer("Ты не в этом городе. Открой /floor.", show_alert=True)
            return
        if floor_data.get_city_for_floor(char.floor_number) is None:
            await callback.answer()
            return

        gate_msg = _adult_gate_status_text(user)
        if gate_msg is not None:
            await callback.answer(gate_msg[:180], show_alert=True)
            return

        loc = get_locale(char, callback.from_user.language_code)
        text = (
            "🏮 <b>Улица красных фонарей</b>\n"
            "<i>Квартал взрослых развлечений. Здесь можно найти закрытые двери и опасные сделки.</i>\n\n"
            "Выбери, куда идти."
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_rl_hub_keyboard(),
            target_message=callback.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("rl:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == f"rl:safe:{FLOOR_KEY}")
async def rl_safe_open(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    # Просто делаем первый ролл.
    await rl_safe_roll(callback, session, state)


@router.callback_query(F.data == f"rl:safe_roll:{FLOOR_KEY}")
async def rl_safe_roll(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        if int(char.floor_number) != FLOOR_KEY:
            await callback.answer("Ты не в этом городе. Открой /floor.", show_alert=True)
            return
        gate_msg = _adult_gate_status_text(user)
        if gate_msg is not None:
            await callback.answer(gate_msg[:180], show_alert=True)
            return

        events = _load_safe_events()
        seed = int(char.id) * 1000003 + int(callback.from_user.id)
        ev = _pick_safe_event(events, seed=seed)
        if ev is None:
            await callback.answer("Нет событий.", show_alert=True)
            return

        # Применяем исход безопасного события.
        await character_repo.lock_character_row(session, char.id)
        footer = _apply_safe_event_outcome(char, ev)
        await session.commit()

        title = str(ev.get("title") or "Событие").strip()
        body = str(ev.get("text") or "").strip()
        if not body:
            body = "<i>Пусто.</i>"
        text = f"🎲 <b>{title}</b>\n\n{body}"
        if footer:
            text += f"\n\n{footer}"

        loc = get_locale(char, callback.from_user.language_code)
        _ = loc  # под локаль оставляем место
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_safe_event_keyboard(),
            target_message=callback.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("rl:safe_roll")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == f"rl:explicit:{FLOOR_KEY}")
async def rl_explicit(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        if int(char.floor_number) != FLOOR_KEY:
            await callback.answer("Ты не в этом городе. Открой /floor.", show_alert=True)
            return

        gate_msg = _adult_gate_status_text(user)
        if gate_msg is not None:
            await callback.answer(gate_msg[:180], show_alert=True)
            return

        if not config_is_admin(callback.from_user.id):
            teaser = (
                "🚪 <b>Закрытая дверь</b>\n\n"
                "Ты чувствуешь тяжёлый аромат духов и слышишь приглушённый смех.\n"
                "<i>Раздел закрыт на обслуживании.</i>"
            )
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=teaser,
                reply_markup=_explicit_locked_keyboard(),
                target_message=callback.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            await callback.answer()
            return

        scenes = _load_explicit_scenes()
        idx = _index_by_id(scenes)
        if not idx:
            await callback.answer("Нет данных.", show_alert=True)
            return
        scene0 = idx.get(EXPLICIT_ROOT_ID) or next(iter(idx.values()))
        text = _explicit_render(scene0)
        photo_path = _explicit_photo_path(scene0) or menu_city_photo_path()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_explicit_kb(scene0),
            target_message=callback.message,
            photo_path=photo_path,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("rl:explicit")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(rf"^rl:ex:{FLOOR_KEY}:[a-zA-Z0-9_\\-]+$"))
async def rl_explicit_scene(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None or callback.data is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        if int(char.floor_number) != FLOOR_KEY:
            await callback.answer("Ты не в этом городе. Открой /floor.", show_alert=True)
            return
        gate_msg = _adult_gate_status_text(user)
        if gate_msg is not None:
            await callback.answer(gate_msg[:180], show_alert=True)
            return
        if not config_is_admin(callback.from_user.id):
            await callback.answer("Недоступно.", show_alert=True)
            return

        scene_id = callback.data.split(":")[-1]
        scenes = _load_explicit_scenes()
        idx = _index_by_id(scenes)
        scene = idx.get(scene_id)
        if scene is None:
            await callback.answer("Сцена не найдена.", show_alert=True)
            return

        text = _explicit_render(scene)
        photo_path = _explicit_photo_path(scene) or menu_city_photo_path()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=_explicit_kb(scene),
            target_message=callback.message,
            photo_path=photo_path,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("rl:ex")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == f"rl:back:{FLOOR_KEY}")
async def rl_back_city(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or user.is_banned:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Сначала /start.", show_alert=True)
            return
        if int(char.floor_number) != FLOOR_KEY:
            await callback.answer("Город устарел. Открой /floor.", show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=format_city_hub_message(char),
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc, user=user),
            target_message=callback.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("rl:back")
        await callback.answer("Ошибка.", show_alert=True)

