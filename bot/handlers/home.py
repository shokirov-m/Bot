"""Экран «Дом»: гардероб, верстак, алхимия."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.home_kb import (
    alchemy_keyboard,
    home_main_keyboard,
    wardrobe_keyboard,
    workbench_keyboard,
)
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from services import home_service

router = Router(name="home")


async def _char(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    if user is None or getattr(user, "is_banned", False):
        return None
    return await character_repo.get_by_user_id(session, user.id)


@router.callback_query(F.data == "hom:hub")
async def home_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_home_main_html(char),
            reply_markup=home_main_keyboard(floor_number=int(char.floor_number)),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:ward")
async def home_wardrobe(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        from utils.profile_portraits import META_PORTRAIT_KEY, PORTRAIT_ORDER

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        keys = list(PORTRAIT_ORDER) + [
            k for k in home_service.unlocked_portrait_keys(char) if k not in PORTRAIT_ORDER
        ]
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_wardrobe_html(char),
            reply_markup=wardrobe_keyboard(keys, current_key=cur),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:ward")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:setp:"))
async def home_set_portrait(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        pk = callback.data.removeprefix("hom:setp:").strip()
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_set_portrait_key(char, pk)
        await session.flush()
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return
        from utils.profile_portraits import META_PORTRAIT_KEY, PORTRAIT_ORDER

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        keys = list(PORTRAIT_ORDER) + [
            k for k in home_service.unlocked_portrait_keys(char) if k not in PORTRAIT_ORDER
        ]
        body = home_service.format_wardrobe_html(char) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=wardrobe_keyboard(keys, current_key=cur),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer("Готово.")
    except Exception:
        logger.exception("hom:setp")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:bench")
async def home_workbench(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        wt = home_service.workbench_tier(char)
        cost = home_service.upgrade_workbench_cost_gold(wt)
        can = cost is not None and int(char.gold) >= cost
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_workbench_html(char),
            reply_markup=workbench_keyboard(can_upgrade=can),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:bench")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:wb:up")
async def home_workbench_upgrade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = home_service.try_upgrade_workbench(char)
        await session.flush()
        wt = home_service.workbench_tier(char)
        cost = home_service.upgrade_workbench_cost_gold(wt)
        can_up = cost is not None and int(char.gold) >= int(cost)
        text = home_service.format_workbench_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=workbench_keyboard(can_upgrade=can_up),
            target_message=callback.message,
            photo_path=None,
        )
        if ok:
            await callback.answer("Улучшено!")
        else:
            await callback.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("hom:wb:up")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "hom:alch")
async def home_alchemy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_alchemy_stub_html(char),
            reply_markup=alchemy_keyboard(),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:alch")
        await callback.answer("Ошибка.", show_alert=True)
