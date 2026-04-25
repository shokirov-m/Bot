"""Экран «Дом»: гардероб, верстак, алхимия, библиотека, улучшение."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.home_kb import (
    alchemy_keyboard,
    home_main_keyboard,
    library_keyboard,
    wardrobe_keyboard,
    wardrobe_preview_keyboard,
    workbench_keyboard,
)
from bot.i18n import get_locale
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from scheduler.tasks import schedule_rest_completion_notification
from services import home_service
from services.rest_service import try_begin_or_claim_rest

router = Router(name="home")


async def _char(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
    if user is None or getattr(user, "is_banned", False):
        return None
    return await character_repo.get_by_user_id(session, user.id)


# ---------------------------------------------------------------------------
# Главный экран дома
# ---------------------------------------------------------------------------

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
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_home_main_html(char),
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:hub")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Гардероб
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:mine")
async def home_mine_collect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = await home_service.collect_mine_farm_rewards(session, char)
        if not ok:
            await callback.answer(msg[:200], show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code)
        text = home_service.format_home_main_html(char) + f"\n\n✅ {msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await session.commit()
        await callback.answer("Собрано!")
    except Exception:
        logger.exception("hom:mine")
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
        from utils.profile_portraits import META_PORTRAIT_KEY

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        keys = home_service.wardrobe_all_selectable_keys(char)
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


# ---------------------------------------------------------------------------
# Передышка
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:rest")
async def home_rest(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        ok, payload, rest_until = try_begin_or_claim_rest(char)
        await session.flush()
        if ok and rest_until is not None:
            schedule_rest_completion_notification(
                callback.bot,
                chat_id=callback.message.chat.id,
                telegram_id=callback.from_user.id,
                until=rest_until,
            )
        loc = get_locale(char, callback.from_user.language_code)
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_home_main_html(char),
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer(payload[:200], show_alert=not ok)
    except Exception:
        logger.exception("hom:rest")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Улучшение уровня дома
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:lvup")
async def home_level_upgrade(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        # Считаем трофеев в сумке (если нужны)
        trophy_count = 0
        trophy_needed = home_service.next_home_trophy_cost(char)
        if trophy_needed > 0:
            from db.repository import inventory_repo
            from game.items.materials import total_boss_trophies_in_bag
            bag_items = await inventory_repo.list_bag_items(session, char.id)
            trophy_count = total_boss_trophies_in_bag(bag_items)

        ok, msg, trophies_to_consume = home_service.try_upgrade_home_level(char, trophy_count)

        # Списываем трофеи из сумки
        if ok and trophies_to_consume > 0:
            from db.repository import inventory_repo
            bag_items = await inventory_repo.list_bag_items(session, char.id)
            remaining = trophies_to_consume
            for it in bag_items:
                if remaining <= 0:
                    break
                d = it.item_data or {}
                if str(d.get("kind")) == "boss_trophy":
                    cnt = max(1, int(d.get("count", 1)))
                    if cnt <= remaining:
                        remaining -= cnt
                        await session.delete(it)
                    else:
                        d["count"] = cnt - remaining
                        it.item_data = d
                        remaining = 0

        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        body = home_service.format_home_main_html(char) + (f"\n\n{msg}" if ok else f"\n\n<i>{msg}</i>")
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=home_main_keyboard(char, locale=loc),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer("Готово!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:lvup")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Библиотека (ур.4+)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:lib")
async def home_library(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.message is None or callback.bot is None:
            await callback.answer()
            return
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if not home_service.can_access_library(char):
            await callback.answer("Библиотека откроется на ур. 4 дома.", show_alert=True)
            return
        ready = home_service.library_hours_until_ready(char) == 0
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=home_service.format_library_html(char),
            reply_markup=library_keyboard(ready=ready),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:lib")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("hom:lib:"))
async def home_library_apply(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        stat_key = callback.data.removeprefix("hom:lib:").strip()
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = home_service.try_use_library(char, stat_key)
        await session.flush()
        loc = get_locale(char, callback.from_user.language_code if callback.from_user else None)
        ready = home_service.library_hours_until_ready(char) == 0
        body = home_service.format_library_html(char) + f"\n\n{msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=body,
            reply_markup=library_keyboard(ready=ready),
            target_message=callback.message,
            photo_path=None,
        )
        await callback.answer("Готово!" if ok else msg[:180], show_alert=not ok)
    except Exception:
        logger.exception("hom:lib:stat")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Портреты
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "hom:pvcur")
async def home_portrait_already_equipped(callback: CallbackQuery) -> None:
    await callback.answer("Этот облик уже надет.", show_alert=True)


@router.callback_query(F.data.startswith("hom:pv:"))
async def home_portrait_preview(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.message is None or callback.bot is None:
            await callback.answer()
            return
        pk = callback.data.removeprefix("hom:pv:").strip()
        char = await _char(callback, session)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if pk not in home_service.wardrobe_all_selectable_keys(char):
            await callback.answer("Этот облик недоступен.", show_alert=True)
            return
        from utils.profile_portraits import META_PORTRAIT_KEY, portrait_path_if_exists

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        caption = home_service.portrait_preview_caption_html(char, pk)
        img = portrait_path_if_exists(pk)
        extra = "\n\n⚠️ <i>Изображение для этого облика пока не загружено.</i>" if img is None else ""
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=caption + extra,
            reply_markup=wardrobe_preview_keyboard(pk, is_current=(pk == cur)),
            target_message=callback.message,
            photo_path=str(img) if img is not None else None,
        )
        await callback.answer()
    except Exception:
        logger.exception("hom:pv")
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
        from utils.profile_portraits import META_PORTRAIT_KEY

        mp = char.meta_progress or {}
        cur = str(mp.get(META_PORTRAIT_KEY) or "")
        keys = home_service.wardrobe_all_selectable_keys(char)
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


# ---------------------------------------------------------------------------
# Верстак
# ---------------------------------------------------------------------------

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
        if not home_service.can_access_workbench(char):
            await callback.answer(
                "Верстак откроется на ур. 2 дома — улучши дом за золото.",
                show_alert=True,
            )
            return
        wt = home_service.workbench_tier(char)
        cost = home_service.upgrade_workbench_cost_gold(wt)
        can = cost is not None and int(char.gold) >= cost
        text = home_service.format_workbench_html(char)
        kb = workbench_keyboard(can_upgrade=can)
        from aiogram.enums import ParseMode
        from aiogram.exceptions import TelegramBadRequest
        try:
            if callback.message.photo:
                await callback.message.delete()
                await callback.bot.send_message(
                    callback.message.chat.id, text,
                    parse_mode=ParseMode.HTML, reply_markup=kb,
                )
            else:
                await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except TelegramBadRequest:
            await callback.bot.send_message(
                callback.message.chat.id, text,
                parse_mode=ParseMode.HTML, reply_markup=kb,
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
        kb = workbench_keyboard(can_upgrade=can_up)
        from aiogram.enums import ParseMode
        from aiogram.exceptions import TelegramBadRequest
        try:
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except TelegramBadRequest:
            await callback.bot.send_message(
                callback.message.chat.id, text,
                parse_mode=ParseMode.HTML, reply_markup=kb,
            )
        if ok:
            await callback.answer("Улучшено!")
        else:
            await callback.answer(msg[:180], show_alert=True)
    except Exception:
        logger.exception("hom:wb:up")
        await callback.answer("Ошибка.", show_alert=True)


# ---------------------------------------------------------------------------
# Алхимия
# ---------------------------------------------------------------------------

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
        if not home_service.can_access_alchemy(char):
            await callback.answer(
                "Алхимия откроется на ур. 3 дома — сначала улучши дом.",
                show_alert=True,
            )
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
