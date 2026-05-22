"""Некромант: меню, ритуал класса, ковчег."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.necromancer_kb import (
    necromancer_coffin_keyboard,
    necromancer_menu_keyboard,
    necromancer_ritual_keyboard,
)
from bot.states.combat_states import CombatStates
from db.repository import character_repo, user_repo
from game.archetypes import manager as arch_manager
from game.necromancer.service import (
    NECROMANCER_COST_GOLD,
    NECROMANCER_MIN_LEVEL,
    MAX_SKELETONS_IN_BATTLE,
    can_purchase_necromancer,
    get_party_skeleton_keys,
    is_necromancer,
    purchase_necromancer,
    set_party_skeleton_keys,
    skeleton_role_label,
    unlocked_skeleton_keys,
)
from utils.telegram.game_ui import push_game_ui
from utils.media.ui_photos import specialization_menu_photo_path

router = Router(name="necromancer")


def _menu_intro_html(char) -> str:
    if is_necromancer(char):
        return (
            "💀 <b>Некромант</b>\n\n"
            "Ковчег костей и гримуары пути — в библиотеке (Меню → Локации)."
        )
    can_ok, reason = can_purchase_necromancer(char)
    extra = f"\n\n⚠️ {html.escape(reason)}" if not can_ok else ""
    return (
        "💀 <b>Некромант</b>\n\n"
        f"Престиж-класс: уровень <b>{NECROMANCER_MIN_LEVEL}+</b>, "
        f"<b>{NECROMANCER_COST_GOLD:,} 💰</b>, базовый путь уже выбран. "
        "Смена на некроманта — <b>один раз</b> на героя."
        f"{extra}"
    ).replace(",", " ")


def _ritual_intro_html(char) -> str:
    arch = arch_manager.get_archetype("necromancer")
    if arch is None:
        return "Класс некроманта не настроен."
    can_ok, reason = can_purchase_necromancer(char)
    skills = [arch_manager.get_skill(s) for s in arch.skills]
    sk_lines = "\n".join(
        f"• <b>{html.escape(s.name_ru)}</b> — {html.escape(s.description_ru)}"
        for s in skills
        if s
    )
    status = (
        "✅ Можно провести ритуал."
        if can_ok
        else f"⚠️ {html.escape(reason)}"
    )
    return (
        f"{arch.emoji} <b>Ритуал некроманта</b>\n\n"
        f"<i>{html.escape(arch.description_ru)}</i>\n\n"
        f"📋 <b>Условия:</b>\n"
        f"• Уровень <b>{NECROMANCER_MIN_LEVEL}+</b> (у вас {int(char.level)})\n"
        f"• <b>{NECROMANCER_COST_GOLD:,} 💰</b> (у вас {int(char.gold):,})\n"
        f"• Смена класса — <b>один раз</b> на героя\n\n"
        f"⚔️ <b>Навыки:</b>\n{sk_lines or '—'}\n\n"
        f"☠️ До <b>{MAX_SKELETONS_IN_BATTLE}</b> скелетов в бою вместо наёмников.\n\n"
        f"{status}"
    ).replace(",", " ")


def _coffin_html(char) -> str:
    party = get_party_skeleton_keys(char)
    unlocked = sorted(unlocked_skeleton_keys(char))
    lines = [
        f"• {html.escape(skeleton_role_label(k))}"
        + (" — <b>в бою</b>" if k in party else "")
        for k in unlocked
    ]
    return (
        "⚰️ <b>Ковчег костей</b>\n\n"
        f"Выберите до <b>{MAX_SKELETONS_IN_BATTLE}</b> союзников (колосс — 2 слота). "
        "Нажмите, чтобы добавить или убрать:\n\n"
        + ("\n".join(lines) if lines else "• Нет открытых типов нежити.")
    )


@router.callback_query(F.data.in_(("prf:necro", "prf:necro:menu")))
async def on_necro_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_menu_intro_html(char),
            reply_markup=necromancer_menu_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("necro:menu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:necro:ritual")
async def on_necro_ritual_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
        if is_necromancer(char):
            await callback.answer("Вы уже некромант.", show_alert=True)
            return
        can_ok, _ = can_purchase_necromancer(char)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_ritual_intro_html(char),
            reply_markup=necromancer_ritual_keyboard(can_buy=can_ok),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("necro:ritual")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:necro:buy")
async def on_necro_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
        ok, msg = purchase_necromancer(char)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.flush()
        arch = arch_manager.get_character_archetype(char)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=(
                f"🎉 {html.escape(msg)}\n\n"
                "Откройте <b>Ковчег костей</b> и выберите скелетов. Наёмники больше не сражаются с вами."
            ),
            reply_markup=necromancer_menu_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer(f"Вы — {arch.name_ru}!", show_alert=True)
    except Exception:
        logger.exception("necro:buy")
        await callback.answer("Ошибка ритуала.", show_alert=True)


@router.callback_query(F.data == "prf:necro:coffin")
async def on_necro_coffin(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None or not is_necromancer(char):
            await callback.answer("Сначала пройдите ритуал некроманта.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_coffin_html(char),
            reply_markup=necromancer_coffin_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("necro:coffin")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("prf:necro:tog:"))
async def on_necro_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Сначала заверши бой.", show_alert=True)
            return
        key = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None or not is_necromancer(char):
            await callback.answer("Нет доступа.", show_alert=True)
            return
        party = list(get_party_skeleton_keys(char))
        if key in party:
            party = [k for k in party if k != key]
        else:
            party.append(key)
        set_party_skeleton_keys(char, party)
        await session.flush()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_coffin_html(char),
            reply_markup=necromancer_coffin_keyboard(char),
            target_message=callback.message,
            character=char,
        )
        await callback.answer("Отряд нежити обновлён")
    except Exception:
        logger.exception("necro:tog")
        await callback.answer("Ошибка.", show_alert=True)
