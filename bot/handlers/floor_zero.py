"""
Хендлер Этажа 0 — Туториал «Призыв».

Шаги:
  0 — Лор (вступление «Призыв»)
  1 — Объяснение механики боя
  2 — Бой с Тенью (scripted, 3 раунда, инлайн)
  3 — Итог боя + выбор пассивки
  4 — Получение пассивки
  5 — Переход на Этаж 1
"""
from __future__ import annotations

import random
from typing import Any

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import character_repo, user_repo
from db.models.character import Character
from game.floors.floor_zero import (
    FLOOR0_CHOICES,
    apply_floor0_passive,
    is_floor0_done,
)

router = Router(name="floor_zero")

# ─────────────────────────── Shadow enemy ──────────────────────────────
_SHADOW_MAX_HP = 80
_SHADOW_ATK_MIN = 6
_SHADOW_ATK_MAX = 14

# FSM state key for mini-combat
_FSM_KEY = "f0_combat"


def _shadow_state(hp: int) -> dict[str, Any]:
    return {"hp": hp, "max_hp": _SHADOW_MAX_HP, "round": 0, "player_used_skill": False}


# ─────────────────────────── Keyboards ─────────────────────────────────

def _start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️ Далее", callback_data="f0:step:1"),
    ]])


def _combat_intro_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚔️ Начать бой с Тенью", callback_data="f0:fight:start"),
    ]])


def _fight_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚔️ Атаковать", callback_data="f0:fight:atk"),
        InlineKeyboardButton(text="✨ Использовать навык", callback_data="f0:fight:skill"),
    ]])


def _passive_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=c["button"],
        callback_data=f"f0:choose:{key}",
    )] for key, c in FLOOR0_CHOICES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _enter_tower_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗼 Войти в Башню", callback_data="f0:enter"),
    ]])


# ─────────────────────────── Texts ─────────────────────────────────────

_LORE_TEXT = (
    "🗼 <b>ПРИЗЫВ</b>\n\n"
    "Сирена. Ослепительная вспышка.\n"
    "Ты стоишь у подножия огромной Башни в незнакомом мире.\n\n"
    "Голос звучит прямо в голове:\n"
    "<i>«Призванный. Ты выбран. Башня испытает тебя.\n"
    "Лишь достойные покорят её вершину — и встанут против внешних демонов.»</i>\n\n"
    "Рядом — такие же растерянные незнакомцы.\n"
    "Один уже вступает в схватку с тенью стены.\n"
    "Другой внимательно изучает каменные руны.\n"
    "Третий собирает людей вместе.\n\n"
    "Прежде чем идти дальше — тебе нужно пройти <b>испытание Башни</b>."
)

_COMBAT_INTRO_TEXT = (
    "⚔️ <b>КАК РАБОТАЕТ БОЙ</b>\n\n"
    "Бой проходит пошагово:\n"
    "• <b>Атаковать</b> — нанести физический урон\n"
    "• <b>Навык</b> — особое умение класса (тратит MP, наносит больше урона или накладывает эффект)\n"
    "• Монстры атакуют после каждого твоего хода\n"
    "• Побеждает тот, кто оставит противника с 0 HP\n\n"
    "📌 <b>Советы:</b>\n"
    "• Используй навыки — они сильнее обычной атаки\n"
    "• Следи за HP — зелья в сумке помогут восстановиться\n"
    "• Боссы на 10-м и 20-м этажах значительно сильнее обычных монстров\n\n"
    "🌑 <b>Первое испытание:</b> сразись с Тенью — бесформенным существом Башни.\n"
    "Она не убьёт тебя, но покажет — готов ли ты."
)

_PASSIVE_CHOICE_INTRO = (
    "✨ <b>СИСТЕМА ЗАФИКСИРОВАЛА ТВОЙ БОЙ</b>\n\n"
    "Тень рассеивается. Голос в голове снова:\n"
    "<i>«Ты выжил. Теперь выбери путь.»</i>\n\n"
    "Перед тобой три энергетических шара — каждый несёт дар.\n"
    "Выбор один. Навсегда.\n\n"
    "<b>Что делаешь ты?</b>"
)


# ─────────────────────────── Helpers ───────────────────────────────────

async def _get_char(query: CallbackQuery, session: AsyncSession) -> Character | None:
    if query.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, query.from_user.id)
    if user is None:
        await query.answer("Нет аккаунта.", show_alert=True)
        return None
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await query.answer("Нет персонажа.", show_alert=True)
    return char


def _player_atk(char: Character, use_skill: bool) -> tuple[int, str]:
    """Урон игрока в обучении. Возвращает (damage, note)."""
    base_str = int(char.stat_strength)
    base_dex = int(char.stat_dexterity)
    dmg = max(5, base_str // 2 + base_dex // 4 + random.randint(3, 10))
    if use_skill:
        dmg = int(dmg * 1.7) + random.randint(5, 15)
        note = "✨ <b>Навык!</b> "
    else:
        note = "⚔️ <b>Атака!</b> "
    return dmg, note


def _shadow_atk() -> int:
    return random.randint(_SHADOW_ATK_MIN, _SHADOW_ATK_MAX)


def _fight_screen(cs: dict[str, Any], char: Character, extra_log: str = "") -> str:
    hp = cs["hp"]
    max_hp = cs["max_hp"]
    rnd = cs["round"]
    p_hp = int(char.hp_current)
    p_hp_max = int(char.hp_max)

    bar_len = 10
    filled = max(0, round(hp / max_hp * bar_len))
    hp_bar = "█" * filled + "░" * (bar_len - filled)

    p_filled = max(0, round(p_hp / p_hp_max * bar_len))
    p_bar = "█" * p_filled + "░" * (bar_len - p_filled)

    text = (
        f"🌑 <b>ТЕНЬ БАШНИ</b>\n"
        f"HP: [{hp_bar}] {hp}/{max_hp}\n\n"
        f"👤 <b>Ты</b>\n"
        f"HP: [{p_bar}] {p_hp}/{p_hp_max}\n\n"
        f"<i>Раунд {rnd}</i>"
    )
    if extra_log:
        text += f"\n\n{extra_log}"
    return text


# ─────────────────────────── Public entry ──────────────────────────────

async def show_floor0(message: Message, state: FSMContext) -> None:
    """Показать экран Этажа 0 из обычного сообщения."""
    await message.answer(
        _LORE_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=_start_kb(),
    )


async def show_floor0_from_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Показать экран Этажа 0 из коллбэка."""
    if query.message is None:
        await query.answer()
        return
    await query.message.answer(
        _LORE_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=_start_kb(),
    )
    await query.answer()


# ─────────────────────────── Step handlers ─────────────────────────────

@router.callback_query(F.data == "f0:step:1")
async def on_floor0_step1(query: CallbackQuery, state: FSMContext) -> None:
    """Шаг 1: объяснение боя."""
    try:
        if query.message is None:
            await query.answer()
            return
        await query.message.edit_text(
            _COMBAT_INTRO_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=_combat_intro_kb(),
        )
        await query.answer()
    except Exception:
        logger.exception("f0:step:1")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "f0:fight:start")
async def on_floor0_fight_start(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начало боя с Тенью."""
    try:
        if query.message is None or query.from_user is None:
            await query.answer()
            return
        char = await _get_char(query, session)
        if char is None:
            return
        if is_floor0_done(char):
            await query.answer("Ты уже прошёл вступление.", show_alert=True)
            return

        cs = _shadow_state(_SHADOW_MAX_HP)
        await state.update_data({_FSM_KEY: cs})

        await query.message.edit_text(
            _fight_screen(cs, char, "🌑 <i>Тень материализуется перед тобой...</i>"),
            parse_mode=ParseMode.HTML,
            reply_markup=_fight_kb(),
        )
        await query.answer()
    except Exception:
        logger.exception("f0:fight:start")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.in_(("f0:fight:atk", "f0:fight:skill")))
async def on_floor0_fight_action(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Раунд боя с Тенью."""
    try:
        if query.message is None or query.data is None:
            await query.answer()
            return
        char = await _get_char(query, session)
        if char is None:
            return

        data = await state.get_data()
        cs: dict[str, Any] = data.get(_FSM_KEY) or _shadow_state(_SHADOW_MAX_HP)

        use_skill = query.data == "f0:fight:skill"
        cs["round"] = cs.get("round", 0) + 1
        if use_skill:
            cs["player_used_skill"] = True

        # Player attacks shadow
        p_dmg, note = _player_atk(char, use_skill)
        cs["hp"] = max(0, cs["hp"] - p_dmg)
        log = f"{note}наносишь <b>{p_dmg}</b> урона Тени."

        # Check shadow dead
        if cs["hp"] <= 0:
            cs["hp"] = 0
            await state.update_data({_FSM_KEY: cs})
            char.hp_current = int(char.hp_max)  # restore HP for next fight
            await session.flush()
            # Show victory → passive choice
            victory_text = (
                f"{_fight_screen(cs, char, log)}\n\n"
                "💥 <b>ТЕНЬ ПОВЕРЖЕНА!</b>\n"
                "<i>Твой удар рассекает тьму. Тень растворяется с тихим воем.</i>"
            )
            await query.message.edit_text(
                victory_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="▶️ К выбору пути", callback_data="f0:passive_choice"),
                ]]),
            )
            await query.answer("Победа!")
            return

        # Shadow counter-attack
        s_dmg = _shadow_atk()
        new_hp = max(1, int(char.hp_current) - s_dmg)  # never kill on tutorial
        char.hp_current = new_hp
        log += f"\n🌑 Тень наносит <b>{s_dmg}</b> урона тебе."

        # Check if HP dangerously low → reduce shadow HP to prevent death loop
        if int(char.hp_current) <= int(char.hp_max) * 0.2:
            cs["hp"] = min(cs["hp"], 15)
            log += "\n⚠️ <i>Тень слабеет — ты чувствуешь её страх!</i>"

        await state.update_data({_FSM_KEY: cs})
        await session.flush()

        await query.message.edit_text(
            _fight_screen(cs, char, log),
            parse_mode=ParseMode.HTML,
            reply_markup=_fight_kb(),
        )
        await query.answer()
    except Exception:
        logger.exception("f0:fight:action")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "f0:passive_choice")
async def on_floor0_passive_choice(
    query: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать выбор пассивки после победы над Тенью."""
    try:
        if query.message is None:
            await query.answer()
            return
        await query.message.edit_text(
            _PASSIVE_CHOICE_INTRO,
            parse_mode=ParseMode.HTML,
            reply_markup=_passive_kb(),
        )
        await query.answer()
    except Exception:
        logger.exception("f0:passive_choice")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("f0:choose:"))
async def on_floor0_choice(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка выбора пассивки → применить и показать результат."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return

        choice_key = query.data.removeprefix("f0:choose:").strip()
        if choice_key not in FLOOR0_CHOICES:
            await query.answer("Неизвестный выбор.", show_alert=True)
            return

        char = await _get_char(query, session)
        if char is None:
            return
        if is_floor0_done(char):
            await query.answer("Ты уже прошёл вступление.", show_alert=True)
            return

        result_text = apply_floor0_passive(char, choice_key)
        await session.flush()

        await query.message.edit_text(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=_enter_tower_kb(),
        )
        await query.answer()
    except Exception:
        logger.exception("f0:choose")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "f0:enter")
async def on_floor0_enter_tower(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Переход с Этажа 0 → Этаж 1 (город Тихий Ручей)."""
    try:
        if query.from_user is None or query.message is None:
            await query.answer()
            return

        char = await _get_char(query, session)
        if char is None:
            return
        if not is_floor0_done(char):
            await query.answer("Сначала сделай выбор.", show_alert=True)
            return

        char.floor_number = 1
        char.highest_floor_reached = max(int(char.highest_floor_reached), 2)
        # Restore HP after tutorial
        char.hp_current = int(char.hp_max)
        await session.flush()

        from services.floor_service import floor_keyboard_for_character, push_floor_screen_ui
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
            target_message=query.message,
        )
        await query.answer("Добро пожаловать в Башню!")
    except Exception:
        logger.exception("f0:enter")
        await query.answer("Ошибка.", show_alert=True)
