"""
Инвентарь и экипировка: /inv, сумка (без лимита ячеек), надеть/снять.
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
from bot.utils.safe_media import normalize_photo_media
from db.repository import character_repo, inventory_repo, user_repo
from game.items import equipment as equip_meta
from game.items import item_categories
from game.items.equipment.defaults import apply_item_payload_defaults
from services import character_service, shop_service, stat_bonus_service
from utils.ui import format_inventory_item_html

router = Router(name="inventory")

INV_HEADER = "🧰 <b>Инвентарь</b>\n"


def _bag_filter_empty_hint(
    total: int,
    *,
    bag_cat: str,
    slot_filter: str | None,
    matched: int | None,
    n_in_category: int | None,
) -> str:
    if total <= 0:
        return ""
    if slot_filter:
        if int(matched or 0) <= 0:
            return (
                "\n\n⚠️ <i>Нет вещей для этого слота — смени категорию фильтра или вкладку "
                "<b>Все</b>.</i>"
            )
        return ""
    if bag_cat != item_categories.BAG_CAT_ALL:
        if int(n_in_category or 0) <= 0:
            return "\n\n⚠️ <i>В этой категории пусто — выбери <b>Все</b> или другой фильтр.</i>"
        return ""
    return ""


def _bag_summary_line(
    count: int,
    *,
    bag_cat: str,
    floor_number: int | None,
) -> str:
    cat_label = item_categories.bag_category_label_ru(bag_cat)
    parts: list[str] = [f"📊 В сумке: <b>{count}</b> предм.", f"фильтр: <b>{html.escape(cat_label)}</b>"]
    if floor_number is not None:
        parts.insert(1, f"этаж героя: <b>{int(floor_number)}</b>")
    return " · ".join(parts)


def _bag_intro(
    count: int,
    *,
    bag_cat: str = item_categories.BAG_CAT_ALL,
    n_in_category: int | None = None,
    slot_filter: str | None = None,
    matched: int | None = None,
    floor_number: int | None = None,
) -> str:
    summary = _bag_summary_line(count, bag_cat=bag_cat, floor_number=floor_number)
    empty_hint = _bag_filter_empty_hint(
        count,
        bag_cat=bag_cat,
        slot_filter=slot_filter,
        matched=matched,
        n_in_category=n_in_category,
    )
    hint = (
        "<i>Сначала редкие; по две кнопки в ряд — открой карточку. Номера ячеек не показываем.</i>\n"
        "Выбери предмет:"
    )
    if count <= 0:
        return (
            f"{INV_HEADER}🎒 <b>Сумка</b> пуста.\n{summary}\n\n"
            "<i>Побеждай врагов и открывай лавки — добыча попадёт сюда.</i>"
        )
    if slot_filter and slot_filter in equip_meta.EQUIP_ORDER:
        lab = equip_meta.slot_label_ru(slot_filter)
        m = int(matched) if matched is not None else 0
        return (
            f"{INV_HEADER}🎒 <b>Сумка</b> — слот <b>{html.escape(lab)}</b>: "
            f"подходит <b>{m}</b> из <b>{count}</b>.\n"
            f"{summary}\n{hint}"
            f"{empty_hint}"
        )
    return f"{INV_HEADER}🎒 <b>Сумка</b>\n{summary}\n\n{hint}{empty_hint}"


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
        text = _bag_intro(len(bag), floor_number=int(char.floor_number))
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


def _slot_from_inv_item_parts(parts: list[str]) -> str | None:
    if len(parts) < 7:
        return None
    raw = str(parts[6]).strip()
    return raw if raw in equip_meta.EQUIP_ORDER else None


@router.callback_query(F.data.startswith("inv:sb:"))
async def inv_slotbag(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Сумка, отфильтрованная по слоту экипировки (кнопка пустого слота)."""
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        parts = (callback.data or "").split(":")
        if len(parts) < 5:
            await callback.answer()
            return
        slot = parts[2]
        if slot not in equip_meta.EQUIP_ORDER:
            await callback.answer("Неизвестный слот.", show_alert=True)
            return
        page = int(parts[3])
        bag_cat = (
            parts[4]
            if parts[4]
            in (
                item_categories.BAG_CAT_ALL,
                item_categories.BAG_CAT_EQUIP,
                item_categories.BAG_CAT_USE,
                item_categories.BAG_CAT_OTHER,
            )
            else item_categories.BAG_CAT_EQUIP
        )
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        matched = len(
            [
                it
                for it in bag
                if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)
                and item_categories.item_data_matches_equip_slot(it.item_data, slot)
            ],
        )
        max_page = max(
            0,
            (
                len(
                    [
                        it
                        for it in bag
                        if item_categories.item_data_matches_bag_category(it.item_data, bag_cat)
                        and item_categories.item_data_matches_equip_slot(it.item_data, slot)
                    ],
                )
                - 1
            )
            // BAG_PAGE_SIZE,
        )
        page = max(0, min(page, max_page))
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_bag_intro(
                len(bag),
                bag_cat=bag_cat,
                n_in_category=matched,
                slot_filter=slot,
                matched=matched,
                floor_number=int(char.floor_number),
            ),
            reply_markup=bag_tab_keyboard(bag, page, bag_cat=bag_cat, slot_target=slot),
            target_message=callback.message,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:sb")
        await callback.answer("Ошибка.", show_alert=True)


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
                text=_bag_intro(
                    len(bag),
                    bag_cat=bag_cat,
                    n_in_category=len(filtered),
                    floor_number=int(char.floor_number),
                ),
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
        slot_target = _slot_from_inv_item_parts(parts)

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        item = await inventory_repo.get_item_for_character(session, char.id, item_id)
        if item is None:
            await callback.answer("Предмет не найден.", show_alert=True)
            return

        data = dict(item.item_data or {})
        apply_item_payload_defaults(data)
        item.item_data = data
        can_equip = equip_meta.resolve_equip_slot_for_item_data(data) is not None
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
        if item.is_equipped:
            status = "✓ Надето"
        else:
            status = "в сумке"
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
            slot_target=slot_target,
        )
        raw_img = str(data.get("image_url") or "").strip()
        photo_arg = normalize_photo_media(raw_img) if raw_img else None
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=photo_arg,
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
        text = f"{_bag_intro(len(bag), bag_cat=bag_cat, n_in_category=len(filtered), floor_number=int(char.floor_number))}\n\n{msg}"
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
        text = f"{_bag_intro(len(bag), bag_cat=bag_cat, n_in_category=len(filtered), floor_number=int(char.floor_number))}\n\n{msg}"
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
        prior_eff = await stat_bonus_service.effective_primary_stats(session, char)
        prior_armor_hp = await stat_bonus_service.equipped_armor_hp_bonus_flat(session, int(char.id))
        err = await inventory_repo.equip_item_from_bag(session, item)
        if err:
            await callback.answer(err, show_alert=True)
            return
        await character_service.refresh_hp_mp_from_effective(
            session,
            char,
            prior_effective_stats=prior_eff,
            prior_armor_hp_bonus_flat=prior_armor_hp,
        )
        data = item.item_data or {}
        can_equip = equip_meta.resolve_equip_slot_for_item_data(data) is not None
        text = (
            f"{INV_HEADER}"
            f"{format_inventory_item_html(data)}\n\n"
            "<b>Статус:</b> ✓ Надето"
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
        prior_eff = await stat_bonus_service.effective_primary_stats(session, char)
        prior_armor_hp = await stat_bonus_service.equipped_armor_hp_bonus_flat(session, int(char.id))
        err = await inventory_repo.unequip_item(session, item)
        if err:
            await callback.answer(err, show_alert=True)
            return
        await character_service.refresh_hp_mp_from_effective(
            session,
            char,
            prior_effective_stats=prior_eff,
            prior_armor_hp_bonus_flat=prior_armor_hp,
        )
        data = item.item_data or {}
        can_equip = equip_meta.resolve_equip_slot_for_item_data(data) is not None
        utag = (item.item_data or {}).get("use_tag")
        text = (
            f"{INV_HEADER}"
            f"{format_inventory_item_html(data)}\n\n"
            f"<b>Статус:</b> в сумке"
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
