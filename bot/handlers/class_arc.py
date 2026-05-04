"""
Handlers for choosing and evolving Archetypes 2.0.
Replacing legacy class_arc.
"""
from __future__ import annotations
import html
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale, t
from bot.keyboards.archetype_kb import archetype_confirm_keyboard, archetype_selection_keyboard
from bot.keyboards.profile_kb import profile_spec_submenu_keyboard
from bot.utils.game_ui import push_game_ui
from bot.utils.ui_photos import specialization_menu_photo_path
from db.repository import character_repo, user_repo
from game.archetypes import manager as arch_manager
from services import character_service

router = Router(name="archetype_v2")

_STAT_LABELS = {
    "level": "уровень",
    "str": "СИЛ",
    "dex": "ЛОВ",
    "int": "ИНТ",
    "vit": "ВЫН",
    "luck": "УДЧ",
}

_STAT_ATTRS = {
    "str": "stat_strength",
    "dex": "stat_dexterity",
    "int": "stat_intelligence",
    "vit": "stat_vitality",
    "luck": "stat_luck",
}


def _requirement_lines(char, arch) -> str:
    if not arch.requirements:
        return "• нет"
    lines: list[str] = []
    for key, need in arch.requirements.items():
        label = _STAT_LABELS.get(key, key.upper())
        current = int(char.level) if key == "level" else int(getattr(char, _STAT_ATTRS.get(key, key), 0))
        mark = "✅" if current >= int(need) else "❌"
        lines.append(f"{mark} {label}: <b>{current}</b> / {int(need)}")
    return "\n".join(lines)


def _skill_line(skill) -> str:
    kind = "физ." if skill.kind == "phys" else "маг."
    cd = f", КД {skill.cooldown}" if int(skill.cooldown) > 0 else ""
    effect = f", эффект {html.escape(skill.effect_key)} {int(skill.effect_chance * 100)}%" if skill.effect_key else ""
    return (
        f"• <b>{html.escape(skill.name_ru)}</b> [{kind}, MP {skill.mp_cost}{cd}] "
        f"x{skill.power_mult:g}{effect}\n"
        f"  <i>{html.escape(skill.description_ru)}</i>"
    )


def _archetype_preview_html(char, arch, *, can_ok: bool, reason: str) -> str:
    skills = [arch_manager.get_skill(s) for s in arch.skills]
    skills_text = "\n".join(_skill_line(s) for s in skills if s is not None) or "• нет"
    passives_text = "\n".join(
        f"• <b>{html.escape(p.name_ru)}</b>: {html.escape(p.description_ru)}"
        for p in arch.passives
    ) or "• нет"
    hp_line = f"+{int(round((arch.hp_multiplier - 1.0) * 100))}% HP" if arch.hp_multiplier != 1.0 else "без бонуса HP"
    mp_line = f"+{int(round((arch.mp_multiplier - 1.0) * 100))}% MP" if arch.mp_multiplier != 1.0 else "без бонуса MP"
    status = "✅ Можно выбрать. Нажмите кнопку ниже, если этот путь подходит." if can_ok else f"⚠️ Нельзя выбрать сейчас: {html.escape(reason)}"
    return (
        f"{arch.emoji} <b>{html.escape(arch.name_ru)}</b>\n"
        f"<i>{html.escape(arch.description_ru)}</i>\n\n"
        f"📌 <b>Что даёт:</b>\n"
        f"• {hp_line}; {mp_line}\n\n"
        f"📋 <b>Требования:</b>\n{_requirement_lines(char, arch)}\n\n"
        f"⚔️ <b>Навыки после выбора:</b>\n{skills_text}\n\n"
        f"💎 <b>Пассивные бонусы:</b>\n{passives_text}\n\n"
        f"{status}"
    )


@router.callback_query(F.data == "prf:arch_pick")
async def on_archetype_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer()
            return
            
        current = arch_manager.get_character_archetype(char)
        if current.tier >= 2:
            await callback.answer("Специализация уже выбрана.", show_alert=True)
            return
        target_tier = 1 if current.tier <= 0 else 2
        required_level = 10 if target_tier == 1 else 50
        if char.level < required_level:
            await callback.answer(f"Нужен {required_level} уровень для выбора пути.", show_alert=True)
            return

        title = "Выбор пути" if target_tier == 1 else "Выбор специализации"
        text = (
            f"🌟 <b>{title}</b>\n\n"
            f"Вы достигли {required_level} уровня и можете выбрать следующий этап развития. "
            "Он определит новые навыки и пассивные бонусы.\n\n"
            "Сначала откройте описание пути, затем подтвердите выбор:"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=archetype_selection_keyboard(
                tier=target_tier,
                allowed_keys=arch_manager.tier2_children(current.key) if target_tier == 2 else None,
            ),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("arch:list")
        await callback.answer("Ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("arch:view:"))
async def on_archetype_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None or callback.data is None:
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
        target_tier = arch.tier
        
        text = _archetype_preview_html(char, arch, can_ok=can_ok, reason=reason)
        
        if not can_ok:
            current = arch_manager.get_character_archetype(char)
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=archetype_selection_keyboard(
                    tier=target_tier,
                    allowed_keys=arch_manager.tier2_children(current.key) if target_tier == 2 else None,
                ),
                target_message=callback.message,
                photo_path=specialization_menu_photo_path(),
                character=char,
            )
        else:
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=archetype_confirm_keyboard(arch_key),
                target_message=callback.message,
                photo_path=specialization_menu_photo_path(),
                character=char,
            )

        await callback.answer()
    except Exception:
        logger.exception("arch:view")
        await callback.answer("Ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("arch:confirm:"))
async def on_archetype_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None or callback.data is None:
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
        mp = dict(char.meta_progress or {})
        mp["unlocked_nodes"] = []
        mp["equipped_skill_keys"] = []
        mp["unspent_sp"] = max(0, int(char.level) - 9)
        char.meta_progress = mp
        # Refresh HP/MP and restore
        char.hp_max = character_service._compute_hp_max(char.stat_vitality, char.stat_strength, arch)
        char.mp_max = character_service._compute_mp_max(char.stat_intelligence, arch)
        char.hp_current = char.hp_max
        char.mp_current = char.mp_max
        
        await session.flush()
        
        loc = get_locale(char, callback.from_user.language_code)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=(
                f"🎉 Поздравляем! Вы теперь <b>{arch.name_ru}</b>!\n\n"
                "Характеристики обновлены, дерево навыков сброшено под новый путь, новые навыки доступны в бою."
            ),
            reply_markup=profile_spec_submenu_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=specialization_menu_photo_path(),
            character=char,
        )
        await callback.answer("Путь выбран!", show_alert=True)
    except Exception:
        logger.exception("arch:confirm")
        await callback.answer("Ошибка при смене пути.", show_alert=True)
