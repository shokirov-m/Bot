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
from bot.utils.game_ui import push_game_ui, push_game_ui_animation, push_game_ui_video
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
EXPLICIT_META_KEY = "explicit"


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


def _load_explicit_data() -> dict:
    """
    Explicit data can be either:
    - dict (preferred): { "character": {...}, "interactions": [...], "strings": {...} }
    - list (legacy): list[scene] with {id,title,text,choices,...}
    """
    if not EXPLICIT_DATA_PATH.is_file():
        return {}
    try:
        raw = json.loads(EXPLICIT_DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            return {"legacy_scenes": [x for x in raw if isinstance(x, dict)]}
    except Exception:
        logger.exception("red_light: explicit json load failed")
    return {}


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


def _explicit_state(char) -> dict:
    mp = dict(getattr(char, "meta_progress", None) or {})
    st = dict(mp.get(META_KEY) or {})
    ex = dict(st.get(EXPLICIT_META_KEY) or {})
    return ex


def _explicit_set_state(char, ex: dict) -> None:
    mp = dict(getattr(char, "meta_progress", None) or {})
    st = dict(mp.get(META_KEY) or {})
    st[EXPLICIT_META_KEY] = dict(ex)
    mp[META_KEY] = st
    char.meta_progress = mp


def _explicit_char_profile_text(char, user, data: dict) -> str:
    _ = (user,)
    c = data.get("character") if isinstance(data.get("character"), dict) else {}
    name = str(c.get("name") or "Незнакомка").strip()
    tagline = str(c.get("tagline") or "Голос в полумраке и взгляд, который держит паузу.").strip()
    ex = _explicit_state(char)
    aff = int(ex.get("aff", 0) or 0)
    return (
        f"🌙 <b>{name}</b>\n"
        f"<i>{tagline}</i>\n\n"
        f"💞 Близость: <b>{aff}</b>\n"
        "Выбери взаимодействие."
    )


def _explicit_interactions(data: dict) -> list[dict]:
    xs = data.get("interactions")
    if isinstance(xs, list):
        return [x for x in xs if isinstance(x, dict)]
    return []


def _explicit_interaction_index(data: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for it in _explicit_interactions(data):
        k = str(it.get("id") or "").strip()
        if k:
            out[k] = it
    return out


def _explicit_profile_kb(data: dict) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for it in _explicit_interactions(data)[:10]:
        label = str(it.get("label") or "").strip()
        iid = str(it.get("id") or "").strip()
        if not label or not iid:
            continue
        rows.append([InlineKeyboardButton(text=label[:64], callback_data=f"rl:exi:{FLOOR_KEY}:{iid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rl:hub:{FLOOR_KEY}")])
    rows.append([InlineKeyboardButton(text="⬅️ В город", callback_data=f"rl:back:{FLOOR_KEY}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _explicit_interaction_text(it: dict, *, aff_delta: int | None = None) -> str:
    title = str(it.get("title") or "Взаимодействие").strip()
    lines = it.get("lines")
    if isinstance(lines, list):
        body = "\n".join(str(x) for x in lines if isinstance(x, str) and x.strip())
    else:
        body = str(it.get("text") or "").strip()
    if not body:
        body = "<i>(пусто)</i>"
    tail = ""
    if aff_delta:
        tail = f"\n\n💞 Близость: <b>{aff_delta:+d}</b>"
    return f"💞 <b>{title}</b>\n\n{body}{tail}"


def _explicit_interaction_kb(iid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Повторить", callback_data=f"rl:exi:{FLOOR_KEY}:{iid}")],
            [InlineKeyboardButton(text="⬅️ К персонажу", callback_data=f"rl:exp:{FLOOR_KEY}")],
            [InlineKeyboardButton(text="⬅️ В город", callback_data=f"rl:back:{FLOOR_KEY}")],
        ],
    )

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

        # New explicit flow: character interactions (data-driven).
        data = _load_explicit_data()
        if _explicit_interactions(data):
            await _rl_explicit_profile(callback, session, state, user=user, char=char, data=data)
        else:
            # Legacy: show scene graph if present.
            scenes = list(data.get("legacy_scenes") or [])
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


async def _rl_explicit_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    *,
    user,
    char,
    data: dict,
) -> None:
    c = data.get("character") if isinstance(data.get("character"), dict) else {}
    media_type = str(c.get("media_type") or "photo").strip().lower()
    media_name = str(c.get("media") or c.get("image") or "").strip()
    media_path = str((EXPLICIT_IMAGE_DIR / media_name)) if media_name else ""
    text = _explicit_char_profile_text(char, user, data)
    kb = _explicit_profile_kb(data)
    if media_type == "animation" and media_name:
        await push_game_ui_animation(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            animation_path=media_path,
        )
    elif media_type == "video" and media_name:
        await push_game_ui_video(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            video_path=media_path,
        )
    else:
        photo = None
        if media_name:
            p = EXPLICIT_IMAGE_DIR / media_name
            if p.is_file():
                photo = str(p)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=photo or menu_city_photo_path(),
            character=char,
        )


@router.callback_query(F.data == f"rl:exp:{FLOOR_KEY}")
async def rl_explicit_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
            await callback.answer("Недоступно.", show_alert=True)
            return
        data = _load_explicit_data()
        if not _explicit_interactions(data):
            await callback.answer("Нет данных.", show_alert=True)
            return
        await _rl_explicit_profile(callback, session, state, user=user, char=char, data=data)
        await callback.answer()
    except Exception:
        logger.exception("rl:exp")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(rf"^rl:exi:{FLOOR_KEY}:[a-zA-Z0-9_\\-]+$"))
async def rl_explicit_interaction(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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

        iid = callback.data.split(":")[-1]
        data = _load_explicit_data()
        idx = _explicit_interaction_index(data)
        it = idx.get(iid)
        if it is None:
            await callback.answer("Взаимодействие не найдено.", show_alert=True)
            return

        # Apply simple affection delta (data-driven).
        aff_delta = int(it.get("aff_delta", 0) or 0)
        if aff_delta:
            await character_repo.lock_character_row(session, char.id)
            ex = _explicit_state(char)
            ex["aff"] = int(ex.get("aff", 0) or 0) + aff_delta
            ex["last_interaction"] = iid
            _explicit_set_state(char, ex)
            await session.commit()

        media_type = str(it.get("media_type") or "photo").strip().lower()
        media_name = str(it.get("media") or it.get("image") or "").strip()
        media_path = str((EXPLICIT_IMAGE_DIR / media_name)) if media_name else ""
        text = _explicit_interaction_text(it, aff_delta=aff_delta if aff_delta else None)
        kb = _explicit_interaction_kb(iid)
        if media_type == "animation" and media_name:
            await push_game_ui_animation(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                animation_path=media_path,
            )
        elif media_type == "video" and media_name:
            await push_game_ui_video(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                video_path=media_path,
            )
        else:
            photo = None
            if media_name:
                p = EXPLICIT_IMAGE_DIR / media_name
                if p.is_file():
                    photo = str(p)
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=callback.message,
                photo_path=photo or menu_city_photo_path(),
                character=char,
            )
        await callback.answer()
    except Exception:
        logger.exception("rl:exi")
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
        data = _load_explicit_data()
        scenes = list(data.get("legacy_scenes") or [])
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

