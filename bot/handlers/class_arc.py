"""
Handlers for choosing and evolving Archetypes 2.0.
Replacing legacy class_arc.
"""
from __future__ import annotations
import html
from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.archetype_kb import archetype_confirm_keyboard, archetype_selection_keyboard
from bot.keyboards.profile_kb import profile_spec_submenu_keyboard
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from game.archetypes import manager as arch_manager
from services import character_service

router = Router(name="archetype_v2")

@router.callback_query(F.data == "prf:arch_pick")
async def on_archetype_list(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
            
        if char.level < 10:
            await callback.answer("Нужен 10 уровень для выбора пути.", show_alert=True)
            return

        text = (
            "🌟 <b>Выбор пути</b>\n\n"
            "Вы достигли 10 уровня! Теперь вы можете выбрать специализацию. "
            "Это определит ваши будущие навыки и пассивные бонусы.\n\n"
            "Выберите архетип для просмотра деталей:"
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=archetype_selection_keyboard()
        )
        await callback.answer()
    except Exception:
        logger.exception("arch:list")
        await callback.answer("Ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("arch:view:"))
async def on_archetype_view(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.data is None:
            await callback.answer()
            return
        arch_key = callback.data.split(":")[-1]
        arch = arch_manager.get_archetype(arch_key)
        if not arch:
            await callback.answer("Ошибка данных.", show_alert=True)
            return

        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        
        can_ok, reason = arch_manager.can_unlock_archetype(char, arch_key)
        
        skills_text = "\n".join([f"• {arch_manager.get_skill(s).name_ru}" for s in arch.skills if arch_manager.get_skill(s)])
        passives_text = "\n".join([f"• <b>{p.name_ru}</b>: {p.description_ru}" for p in arch.passives])
        
        text = (
            f"{arch.emoji} <b>{arch.name_ru}</b>\n"
            f"<i>{arch.description_ru}</i>\n\n"
            f"⚔️ <b>Навыки:</b>\n{skills_text}\n\n"
            f"💎 <b>Пассивки:</b>\n{passives_text}\n\n"
        )
        
        if not can_ok:
            text += f"⚠️ <b>Требования не выполнены:</b>\n{reason}"
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=archetype_selection_keyboard())
        else:
            text += "✅ Вы можете выбрать этот путь."
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=archetype_confirm_keyboard(arch_key))
            
        await callback.answer()
    except Exception:
        logger.exception("arch:view")
        await callback.answer("Ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("arch:confirm:"))
async def on_archetype_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.data is None:
            await callback.answer()
            return
        arch_key = callback.data.split(":")[-1]
        arch = arch_manager.get_archetype(arch_key)
        
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        
        can_ok, reason = arch_manager.can_unlock_archetype(char, arch_key)
        if not can_ok:
            await callback.answer(reason, show_alert=True)
            return

        # Perform the change
        char.class_key = arch.key
        # Refresh HP/MP and restore
        char.hp_max = character_service._compute_hp_max(char.stat_vitality, char.stat_strength, arch)
        char.mp_max = character_service._compute_mp_max(char.stat_intelligence, arch)
        char.hp_current = char.hp_max
        char.mp_current = char.mp_max
        
        await session.flush()
        
        loc = get_locale(char, callback.from_user.language_code)
        await callback.message.edit_text(
            f"🎉 Поздравляем! Вы теперь <b>{arch.name_ru}</b>!\n\n"
            "Ваши характеристики обновлены, а новые навыки уже доступны в бою.",
            parse_mode="HTML",
            reply_markup=profile_spec_submenu_keyboard(char, locale=loc)
        )
        await callback.answer("Путь выбран!", show_alert=True)
    except Exception:
        logger.exception("arch:confirm")
        await callback.answer("Ошибка при смене пути.", show_alert=True)
