"""Гримуары навыков и цепочка наставника."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.grimoire_kb import (
    grimoire_read_confirm_keyboard,
    grimoires_inventory_list_keyboard,
    grimoires_learned_keyboard,
    grimoires_menu_keyboard,
    mentor_quest_keyboard,
    supreme_use_confirm_keyboard,
)
from bot.keyboards.profile_kb import profile_spec_submenu_keyboard
from db.repository import character_repo, user_repo
from game.archetypes.grimoires import (
    SKILL_GRIMOIRES,
    SUPREME_GRIMOIRES,
    apply_supreme_grimoire_class_change,
    format_grimoires_profile_html_ru,
    grimoire_usable_by_character,
    inventory_keys,
    learned_keys,
    learn_grimoire,
)
from game.archetypes import manager as arch_manager
from game.characters.player_skills import ensure_skill_meta
from utils.media.ui_photos import specialization_menu_photo_path
from utils.telegram.game_ui import push_game_ui
import services.progression.character_service as character_service
import services.progression.class_mentor_quest_service as mentor_quest_mod

router = Router(name="grimoires")


@router.callback_query(F.data == "prf:grimoires")
async def on_grimoires_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ensure_skill_meta(char)
        inv = inventory_keys(char)
        learned = learned_keys(char)
        text = (
            "📖 <b>Гримуары</b>\n\n"
            "Навыки и бонусы из древа теперь открываются <b>гримуарами</b>: "
            "получите книгу (квест, награда, лут) и прочитайте её здесь.\n\n"
            f"В сумке: <b>{len(inv)}</b> · изучено: <b>{len(learned)}</b>\n\n"
            "<i>Высший гримуар — смена специализации (tier‑2). "
            "Его даёт наставник после цепочки заданий.</i>"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=grimoires_menu_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:grimoires")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "prf:mentor")
async def on_mentor_quest(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        text = mentor_quest_mod.format_quest_html(char)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=mentor_quest_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("prf:mentor")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "grim:list")
@router.callback_query(F.data.startswith("grim:list:"))
async def on_grim_inventory_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        offset = 8
        if callback.data and callback.data.startswith("grim:list:"):
            try:
                offset = max(8, int(callback.data.split(":")[2]))
            except (IndexError, ValueError):
                offset = 8
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        inv = inventory_keys(char)
        if len(inv) <= 8:
            await callback.answer("Все книги уже в списке.", show_alert=True)
            return
        total = len(inv)
        shown_end = min(total, offset + 8)
        text = (
            f"📖 <b>Гримуары в сумке</b> ({offset + 1}–{shown_end} из {total})\n\n"
            "<i>Выберите книгу, чтобы прочитать.</i>"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=grimoires_inventory_list_keyboard(char, offset),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("grim:list")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "grim:learned")
async def on_grim_learned_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        learned = sorted(learned_keys(char))
        lines = [f"📚 <b>Изученные гримуары</b> — <b>{len(learned)}</b>\n"]
        if not learned:
            lines.append("<i>Пока ничего не изучено. Прочитайте книгу из сумки.</i>")
        else:
            for gk in learned:
                if not grimoire_usable_by_character(char, gk):
                    continue
                g = SKILL_GRIMOIRES.get(gk)
                sg = SUPREME_GRIMOIRES.get(gk)
                if sg:
                    lines.append(f"{sg.emoji} <b>{html.escape(sg.name_ru)}</b> — <i>высший гримуар</i>")
                elif g:
                    kind = {"active_skill": "активный", "passive_bonus": "пассив", "stat_boost": "стат"}.get(
                        g.node_type,
                        g.node_type,
                    )
                    lines.append(f"📖 <b>{html.escape(g.name_ru)}</b> — <i>{kind}</i>")
        passive = format_grimoires_profile_html_ru(char).strip()
        if passive:
            lines.extend(["", "—", "", "📌 <b>Пассивные бонусы</b>", passive])
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text="\n".join(lines),
            reply_markup=grimoires_learned_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("grim:learned")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("grim:read:"))
async def on_grim_read_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        gk = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer()
            return
        g = SKILL_GRIMOIRES.get(gk)
        sg = SUPREME_GRIMOIRES.get(gk)
        if g:
            text = (
                f"{html.escape(g.name_ru)}\n\n"
                f"{html.escape(g.description_ru)}\n\n"
                f"<i>Тип: {g.node_type}</i>"
            )
            kb = grimoire_read_confirm_keyboard(gk)
        elif sg:
            text = (
                f"{sg.emoji} <b>{html.escape(sg.name_ru)}</b>\n\n"
                f"{html.escape(sg.description_ru)}\n\n"
                "<i>После изучения — отдельная кнопка «Сменить класс».</i>"
            )
            kb = grimoire_read_confirm_keyboard(gk)
        else:
            await callback.answer("Гримуар не найден.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("grim:read")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("grim:confirm:"))
async def on_grim_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        gk = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer()
            return
        ok, msg = learn_grimoire(char, gk)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.commit()
        ensure_skill_meta(char)
        sg = SUPREME_GRIMOIRES.get(gk)
        if sg:
            text = (
                f"✅ {html.escape(msg)}\n\n"
                "Нажмите «Сменить класс», когда будете готовы."
            )
            kb = supreme_use_confirm_keyboard(gk)
        else:
            text = f"✅ {html.escape(msg)}\n\nНавык доступен в «Экипировать навыки»."
            kb = grimoires_menu_keyboard(char)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            character=char,
        )
        await callback.answer("Изучено!")
    except Exception:
        logger.exception("grim:confirm")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("grim:supreme:"))
async def on_grim_supreme_use(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        gk = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer()
            return
        ok, msg = apply_supreme_grimoire_class_change(char, gk)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        arch = arch_manager.get_character_archetype(char)
        char.hp_max = character_service._compute_hp_max(
            char.stat_vitality, char.stat_strength, arch,
        )
        char.mp_max = character_service._compute_mp_max(char.stat_intelligence, arch)
        char.hp_current = char.hp_max
        char.mp_current = char.mp_max
        await session.commit()
        ensure_skill_meta(char)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=(
                f"🎉 <b>{html.escape(msg)}</b>\n\n"
                "Специализация открыта. Экипируйте навыки в профиле."
            ),
            reply_markup=profile_spec_submenu_keyboard(char),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer("Класс изменён!")
    except Exception:
        logger.exception("grim:supreme")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("mentor:pick:"))
async def on_mentor_pick_reward(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        sk = callback.data.split(":")[-1]
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id) if user else None
        if char is None:
            await callback.answer()
            return
        ok, msg = mentor_quest_mod.grant_supreme_reward(char, sk)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await session.commit()
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=f"✅ {html.escape(msg)}",
            reply_markup=grimoires_menu_keyboard(char),
            target_message=callback.message,
            character=char,
        )
        await callback.answer("Награда!")
    except Exception:
        logger.exception("mentor:pick")
        await callback.answer("Ошибка.", show_alert=True)
