"""
Инвентарь и экипировка: /inv, сумка (20 ячеек), надеть/снять.
"""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inventory_kb import (
    BAG_PAGE_SIZE,
    bag_tab_keyboard,
    equipment_tab_keyboard,
    item_detail_keyboard,
)
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, inventory_repo, user_repo
from game.items import equipment as equip_meta
from game.items import item_categories
from services import shop_service
from utils.ui import format_inventory_item_html

router = Router(name="inventory")

INV_HEADER = "🧰 <b>Инвентарь</b>\n"


def _bag_intro(count: int) -> str:
    return (
        f"{INV_HEADER}🎒 <b>Сумка</b> — <b>{count}</b>/20 ячеек.\n"
        "<i>Сначала редкие предметы; в ряд по две кнопки — открой карточку.</i>\n"
        "Выбери предмет:"
    )


def _eq_intro() -> str:
    return (
        f"{INV_HEADER}⚔️ <b>Экипировка</b>\n"
        "<i>Цветной маркер — редкость.</i> Нажми слот, чтобы снять или открыть карточку."
    )


async def _load_character(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    return user, char


@router.message(Command("inv"))
@router.message(Command("инвентарь"))
async def cmd_inventory(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        _, char = await _load_character(session, message.from_user.id)
        if char is None:
            await message.answer("Сначала создай героя через /start.")
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        text = _bag_intro(len(bag))
        await push_game_ui(
            state,
            message.bot,
            chat_id=message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, 0),
            fallback_message=message,
        )
    except Exception:
        logger.exception("Ошибка /inv")


@router.callback_query(F.data == "inv:noop")
async def inv_noop(callback: CallbackQuery) -> None:
    await callback.answer("Пустой слот")


@router.callback_query(F.data == "inv:close")
async def inv_close(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message:
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text="Инвентарь закрыт.",
            reply_markup=None,
            target_message=callback.message,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("inv:tab:"))
async def inv_tab(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        parts = (callback.data or "").split(":")
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        if len(parts) >= 4 and parts[2] == "bag":
            page = int(parts[3])
            bag_cat = (
                parts[4]
                if len(parts) >= 5
                and parts[4]
                in (
                    item_categories.BAG_CAT_ALL,
                    item_categories.BAG_CAT_EQUIP,
                    item_categories.BAG_CAT_USE,
                    item_categories.BAG_CAT_OTHER,
                )
                else item_categories.BAG_CAT_ALL
            )
            bag = await inventory_repo.list_bag_items(session, char.id)
            filtered = [it for it in bag if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)]
            max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
            page = max(0, min(page, max_page))
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=_bag_intro(len(bag)),
                reply_markup=bag_tab_keyboard(bag, page, bag_cat=bag_cat),
                target_message=callback.message,
            )
        elif len(parts) >= 3 and parts[2] == "eq":
            eq = await inventory_repo.list_equipped_items(session, char.id)
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=_eq_intro(),
                reply_markup=equipment_tab_keyboard(eq),
                target_message=callback.message,
            )
        else:
            await callback.answer()
            return
        await callback.answer()
    except Exception:
        logger.exception("inv:tab")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:it:"))
async def inv_item_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        parts = (callback.data or "").split(":")
        if len(parts) < 5:
            await callback.answer()
            return
        item_id = int(parts[2])
        from_bag = parts[3] == "b"
        bag_page = int(parts[4])
        bag_cat = item_categories.BAG_CAT_ALL
        if (
            len(parts) >= 6
            and parts[5]
            in (
                item_categories.BAG_CAT_ALL,
                item_categories.BAG_CAT_EQUIP,
                item_categories.BAG_CAT_USE,
                item_categories.BAG_CAT_OTHER,
            )
        ):
            bag_cat = parts[5]

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        item = await inventory_repo.get_item_for_character(session, char.id, item_id)
        if item is None:
            await callback.answer("Предмет не найден.", show_alert=True)
            return

        data = item.item_data or {}
        can_equip = equip_meta.equip_slot_for_kind(data.get("kind")) is not None
        utag = data.get("use_tag")
        show_ration = (
            not item.is_equipped
            and item.bag_slot is not None
            and utag == "stamina_flat"
        )
        show_bread = (
            not item.is_equipped
            and item.bag_slot is not None
            and utag == "heal_hp_flat"
        )
        status = "надето" if item.is_equipped else "в сумке"
        if item.bag_slot is not None and not item.is_equipped:
            status = f"сумка, ячейка {item.bag_slot}"
        text = (
            f"{INV_HEADER}"
            f"{format_inventory_item_html(data)}\n\n"
            f"<b>Статус:</b> {html.escape(status)}"
        )
        kb = item_detail_keyboard(
            item.id,
            is_equipped=item.is_equipped,
            can_equip=can_equip,
            from_bag=from_bag,
            bag_page=bag_page,
            bag_cat=bag_cat if from_bag else item_categories.BAG_CAT_ALL,
            show_ration_eat=show_ration,
            show_bread_eat=show_bread,
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:it")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:eat:"))
async def inv_eat_ration(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("В бою используй кнопку «Предмет».", show_alert=True)
            return
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer()
            return
        item_id = int(parts[2])
        bag_page = int(parts[3])
        bag_cat = item_categories.BAG_CAT_ALL
        if len(parts) >= 5 and parts[4] in (
            item_categories.BAG_CAT_ALL,
            item_categories.BAG_CAT_EQUIP,
            item_categories.BAG_CAT_USE,
            item_categories.BAG_CAT_OTHER,
        ):
            bag_cat = parts[4]

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = await shop_service.try_use_bag_ration_by_id(session, char, item_id)
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return

        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)]
        max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
        safe_page = min(bag_page, max_page)
        text = f"{_bag_intro(len(bag))}\n\n{msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, safe_page, bag_cat=bag_cat),
            target_message=callback.message,
        )
        await callback.answer("Приятного!")
    except Exception:
        logger.exception("inv:eat")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:bread:"))
async def inv_eat_bread(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("В бою используй кнопку «Предмет».", show_alert=True)
            return
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer()
            return
        item_id = int(parts[2])
        bag_page = int(parts[3])
        bag_cat = item_categories.BAG_CAT_ALL
        if len(parts) >= 5 and parts[4] in (
            item_categories.BAG_CAT_ALL,
            item_categories.BAG_CAT_EQUIP,
            item_categories.BAG_CAT_USE,
            item_categories.BAG_CAT_OTHER,
        ):
            bag_cat = parts[4]

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = await shop_service.try_use_bag_bread_by_id(session, char, item_id)
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return

        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)]
        max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
        safe_page = min(bag_page, max_page)
        text = f"{_bag_intro(len(bag))}\n\n{msg}"
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, safe_page, bag_cat=bag_cat),
            target_message=callback.message,
        )
        await callback.answer("Передышка!")
    except Exception:
        logger.exception("inv:bread")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:eq:"))
async def inv_equip(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        item_id = int((callback.data or "").split(":")[2])
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        item = await inventory_repo.get_item_for_character(session, char.id, item_id)
        if item is None:
            await callback.answer("Предмет не найден.", show_alert=True)
            return
        err = await inventory_repo.equip_item_from_bag(session, item)
        if err:
            await callback.answer(err, show_alert=True)
            return
        data = item.item_data or {}
        can_equip = equip_meta.equip_slot_for_kind(data.get("kind")) is not None
        text = (
            f"{INV_HEADER}"
            f"{format_inventory_item_html(data)}\n\n"
            "<b>Статус:</b> надето"
        )
        kb = item_detail_keyboard(
            item.id,
            is_equipped=True,
            can_equip=can_equip,
            from_bag=True,
            bag_page=0,
            bag_cat=item_categories.BAG_CAT_ALL,
            show_ration_eat=False,
            show_bread_eat=False,
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
        )
        await callback.answer("Надето!")
    except Exception:
        logger.exception("inv:eq")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:uneq:"))
async def inv_unequip(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        item_id = int((callback.data or "").split(":")[2])
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        item = await inventory_repo.get_item_for_character(session, char.id, item_id)
        if item is None:
            await callback.answer("Предмет не найден.", show_alert=True)
            return
        err = await inventory_repo.unequip_item(session, item)
        if err:
            await callback.answer(err, show_alert=True)
            return
        data = item.item_data or {}
        can_equip = equip_meta.equip_slot_for_kind(data.get("kind")) is not None
        utag = (item.item_data or {}).get("use_tag")
        slot_note = f"ячейка {item.bag_slot}" if item.bag_slot is not None else "сумка"
        text = (
            f"{INV_HEADER}"
            f"{format_inventory_item_html(data)}\n\n"
            f"<b>Статус:</b> {html.escape(slot_note)}"
        )
        kb = item_detail_keyboard(
            item.id,
            is_equipped=False,
            can_equip=can_equip,
            from_bag=True,
            bag_page=0,
            bag_cat=item_categories.BAG_CAT_ALL,
            show_ration_eat=item.bag_slot is not None and utag == "stamina_flat",
            show_bread_eat=item.bag_slot is not None and utag == "heal_hp_flat",
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
        )
        await callback.answer("Снято в сумку.")
    except Exception:
        logger.exception("inv:uneq")
        await callback.answer("Ошибка.", show_alert=True)
