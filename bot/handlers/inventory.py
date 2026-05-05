"""
Инвентарь и экипировка: /inv, сумка по категориям, надеть/снять.
"""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.menu_kb import main_menu_keyboard, menu_nav_button_row
from bot.keyboards.inventory_kb import (
    BAG_PAGE_SIZE,
    bag_tab_keyboard,
    equipment_tab_keyboard,
    inventory_hub_keyboard,
    item_detail_keyboard,
)
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from bot.utils.ui_photos import inventory_menu_photo_path
from bot.utils.safe_media import normalize_photo_media
from db.repository import character_repo, inventory_repo, user_repo
from game.items import equipment as equip_meta
from game.items import item_categories
from game.items.equipment.defaults import apply_item_payload_defaults
from services import character_service, shop_service, stat_bonus_service
from services.workshop_enchant_service import (
    USE_TAG_ALCHEMY_ENCHANT,
    list_compatible_targets as list_alchemy_enchant_targets,
    try_apply_alchemy_enchant,
)
from services.menu_hub_service import format_menu_hub_html, resolve_menu_hub_photo_path
from utils.game_images_prefs import game_images_enabled
from utils.ui import format_inventory_item_html

router = Router(name="inventory")

INV_HEADER = "🧰 <b>Инвентарь</b>\n"

_SECTION_INFER_ORDER: tuple[str, ...] = (
    item_categories.INV_SEC_WEAPON,
    item_categories.INV_SEC_ARMOR_BODY,
    item_categories.INV_SEC_ACCESSORY,
    item_categories.INV_SEC_HELMET,
    item_categories.INV_SEC_PANTS,
    item_categories.INV_SEC_OTHER_GEAR,
    item_categories.INV_SEC_CONSUMABLE,
    item_categories.INV_SEC_RESOURCE,
)


def infer_inv_section_from_item_data(data: dict | None) -> str:
    """Подобрать секцию сумки для карточки предмета (для «Назад» после снятия)."""
    ic = item_categories
    d = dict(data or {})
    for sec in _SECTION_INFER_ORDER:
        if ic.item_data_matches_inv_section(d, sec):
            return sec
    return ic.INV_SEC_RESOURCE


def _normalize_inv_section(raw: str | None) -> str:
    ic = item_categories
    if raw and raw in ic.ALL_INV_SECTIONS:
        return raw
    if raw == ic.BAG_CAT_USE:
        return ic.INV_SEC_CONSUMABLE
    if raw == ic.BAG_CAT_OTHER:
        return ic.INV_SEC_RESOURCE
    return ic.INV_SEC_WEAPON


def _inventory_hub_text(floor_number: int) -> str:
    return (
        f"{INV_HEADER}"
        "<i>Выбери категорию сумки. Надеть предметы можно здесь или в разделе "
        "<b>Что надето</b>.</i>\n\n"
        f"📊 Этаж героя: <b>{int(floor_number)}</b>"
    )


def _section_bag_intro(
    total_bag: int,
    *,
    section: str,
    n_in_section: int,
    floor_number: int,
) -> str:
    ic = item_categories
    title = ic.inv_section_title_ru(section)
    summary = (
        f"📊 В сумке всего: <b>{total_bag}</b> · в категории: <b>{n_in_section}</b> · "
        f"этаж: <b>{int(floor_number)}</b>"
    )
    hint = (
        "<i>Сортировка: выше редкость. До <b>8</b> предметов на экран; ◀️ ▶️ — страницы.</i>\n"
        "Выбери предмет:"
    )
    if total_bag <= 0:
        return (
            f"{INV_HEADER}<i>Сумка пуста — побеждай врагов и открывай лавки.</i>\n{summary}"
        )
    if n_in_section <= 0:
        return f"{INV_HEADER}<b>{title}</b>\n{summary}\n\n<i>В этой категории пока пусто.</i>"
    return f"{INV_HEADER}<b>{title}</b>\n{summary}\n\n{hint}"


def _eq_intro() -> str:
    return (
        f"{INV_HEADER}⚔️ <b>Что надето</b>\n"
        "<i>Цветной маркер — редкость. Пустой слот открывает сумку по этой категории.</i>"
    )


async def _load_character(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    return user, char


async def _show_bag_section(
    *,
    state: FSMContext,
    bot,
    chat_id: int,
    message,
    session: AsyncSession,
    char,
    section: str,
    page: int,
) -> None:
    ic = item_categories
    sec = section if section in ic.ALL_INV_SECTIONS else ic.INV_SEC_WEAPON
    bag = await inventory_repo.list_bag_items(session, char.id)
    filtered = [it for it in bag if ic.item_data_matches_inv_section(it.item_data, sec)]
    max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
    pg = max(0, min(int(page), max_page))
    text = _section_bag_intro(
        len(bag),
        section=sec,
        n_in_section=len(filtered),
        floor_number=int(char.floor_number),
    )
    await push_game_ui(
        state,
        bot,
        chat_id=chat_id,
        text=text,
        reply_markup=bag_tab_keyboard(bag, pg, section=sec),
        target_message=message,
        character=char,
    )


async def _consolidate_legacy_stacks(session: AsyncSession, character_id: int) -> None:
    """Тихо подружить старые стакаемые предметы у уже существующих персонажей."""
    try:
        merged = await inventory_repo.consolidate_bag_stacks(session, character_id)
        if merged:
            await session.commit()
    except Exception:
        logger.exception("inv:consolidate")


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
        await _consolidate_legacy_stacks(session, int(char.id))
        text = _inventory_hub_text(int(char.floor_number))
        await push_game_ui(
            state,
            message.bot,
            chat_id=message.chat.id,
            text=text,
            reply_markup=inventory_hub_keyboard(),
            fallback_message=message,
            photo_path=inventory_menu_photo_path(),
            character=char,
        )
    except Exception:
        logger.exception("Ошибка /inv")


@router.callback_query(F.data == "inv:hub")
async def inv_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        await _consolidate_legacy_stacks(session, int(char.id))
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=_inventory_hub_text(int(char.floor_number)),
            reply_markup=inventory_hub_keyboard(),
            target_message=callback.message,
            photo_path=inventory_menu_photo_path(),
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:hub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:sec:"))
async def inv_section_bag(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Сумка в выбранной секции и странице."""
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        parts = (callback.data or "").split(":")
        if len(parts) < 4:
            await callback.answer()
            return
        sec = parts[2]
        page = int(parts[3])
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        if sec not in item_categories.ALL_INV_SECTIONS:
            await callback.answer("Неизвестная категория.", show_alert=True)
            return
        await _show_bag_section(
            state=state,
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message=callback.message,
            session=session,
            char=char,
            section=sec,
            page=page,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:sec")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "inv:noop")
async def inv_noop(callback: CallbackQuery) -> None:
    await callback.answer("Пустой слот")


@router.callback_query(F.data == "inv:close")
async def inv_close(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if callback.message is None or callback.bot is None or callback.from_user is None:
            await callback.answer()
            return
        user = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        if user is None or getattr(user, "is_banned", False):
            await callback.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        loc = get_locale(char, callback.from_user.language_code)
        hub_text = format_menu_hub_html(char, locale=loc)
        pp = resolve_menu_hub_photo_path(char)
        photo_p = str(pp) if pp is not None else None
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=hub_text,
            reply_markup=main_menu_keyboard(locale=loc, character=char),
            target_message=callback.message,
            photo_path=photo_p,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:close")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:sb:"))
async def inv_slotbag_legacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Старые кнопки inv:sb:* → секция сумки по слоту."""
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        parts = (callback.data or "").split(":")
        if len(parts) < 3:
            await callback.answer()
            return
        slot = parts[2]
        if slot not in equip_meta.EQUIP_ORDER:
            await callback.answer("Неизвестный слот.", show_alert=True)
            return
        page = int(parts[3]) if len(parts) >= 4 else 0
        sec = item_categories.equip_slot_to_inv_section(slot)
        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        await _show_bag_section(
            state=state,
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message=callback.message,
            session=session,
            char=char,
            section=sec,
            page=page,
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
            await push_game_ui(
                state,
                callback.bot,
                chat_id=callback.message.chat.id,
                text=_inventory_hub_text(int(char.floor_number)),
                reply_markup=inventory_hub_keyboard(),
                target_message=callback.message,
                photo_path=inventory_menu_photo_path(),
                character=char,
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
                character=char,
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
        source = "b" if from_bag else "e"
        bag_page = int(parts[4])
        inv_section = item_categories.INV_SEC_WEAPON
        if from_bag and len(parts) >= 6:
            inv_section = _normalize_inv_section(parts[5])

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
        show_alchemy_enchant = (
            not item.is_equipped
            and item.bag_slot is not None
            and utag == USE_TAG_ALCHEMY_ENCHANT
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
            inv_section=inv_section if from_bag else item_categories.INV_SEC_WEAPON,
            show_ration_eat=show_ration,
            show_bread_eat=show_bread,
            show_alchemy_enchant=show_alchemy_enchant,
            source=source,
        )
        raw_img = str(data.get("image_url") or "").strip()
        photo_arg = (
            normalize_photo_media(raw_img)
            if raw_img and game_images_enabled(char)
            else None
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            photo_path=photo_arg,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:it")
        await callback.answer("Ошибка.", show_alert=True)


def _parse_sec_from_equip_callback(data: str | None) -> str:
    parts = (data or "").split(":")
    if len(parts) >= 4 and parts[3] in item_categories.ALL_INV_SECTIONS:
        return parts[3]
    return item_categories.INV_SEC_WEAPON


def _parse_source_from_callback(data: str | None, expected_index: int) -> str:
    """Извлечь `e`/`b` суффикс источника из колбэка eq/uneq, по умолчанию 'e'."""
    parts = (data or "").split(":")
    if len(parts) > expected_index:
        v = str(parts[expected_index]).strip().lower()
        if v in ("e", "b"):
            return v
    return "e"


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
        sec = _normalize_inv_section(parts[4]) if len(parts) >= 5 else item_categories.INV_SEC_CONSUMABLE

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = await shop_service.try_use_bag_ration_by_id(session, char, item_id)
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return

        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_inv_section(it.item_data, sec)]
        max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
        safe_page = min(bag_page, max_page)
        text = (
            f"{_section_bag_intro(len(bag), section=sec, n_in_section=len(filtered), floor_number=int(char.floor_number))}"
            f"\n\n{msg}"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, safe_page, section=sec),
            target_message=callback.message,
            character=char,
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
        sec = _normalize_inv_section(parts[4]) if len(parts) >= 5 else item_categories.INV_SEC_CONSUMABLE

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = await shop_service.try_use_bag_bread_by_id(session, char, item_id)
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return

        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_inv_section(it.item_data, sec)]
        max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
        safe_page = min(bag_page, max_page)
        text = (
            f"{_section_bag_intro(len(bag), section=sec, n_in_section=len(filtered), floor_number=int(char.floor_number))}"
            f"\n\n{msg}"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, safe_page, section=sec),
            target_message=callback.message,
            character=char,
        )
        await callback.answer("Передышка!")
    except Exception:
        logger.exception("inv:bread")
        await callback.answer("Ошибка.", show_alert=True)


_ENCH_PER_PAGE = 8


@router.callback_query(F.data.startswith("inv:enchmenu:"))
async def inv_alchemy_enchant_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Выбор предмета в сумке для наложения алхимического зачарования."""
    try:
        if callback.data is None or callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Снаружи боя.", show_alert=True)
            return
        parts = callback.data.split(":")
        if len(parts) < 6:
            await callback.answer()
            return
        scroll_id = int(parts[2])
        bag_page = int(parts[3])
        sec = _normalize_inv_section(parts[4])
        page = max(0, int(parts[5]))

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        scroll_it = await inventory_repo.get_item_for_character(session, char.id, scroll_id)
        if scroll_it is None:
            await callback.answer("Предмет не найден.", show_alert=True)
            return
        sd = dict(scroll_it.item_data or {})
        if str(sd.get("use_tag") or "") != USE_TAG_ALCHEMY_ENCHANT:
            await callback.answer("Это не зачарование.", show_alert=True)
            return

        targets = await list_alchemy_enchant_targets(session, char.id, sd)
        if not targets:
            await callback.answer("Нет подходящих предметов в сумке.", show_alert=True)
            return

        total_pages = max(0, (len(targets) - 1) // _ENCH_PER_PAGE)
        page = min(page, total_pages)
        start = page * _ENCH_PER_PAGE
        chunk = targets[start : start + _ENCH_PER_PAGE]

        rows: list[list[InlineKeyboardButton]] = []
        for t in chunk:
            nm = str((t.item_data or {}).get("name", f"#{t.id}"))[:44]
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"➡ {nm}",
                        callback_data=f"inv:enchdo:{scroll_id}:{t.id}:{bag_page}:{sec}",
                    ),
                ],
            )
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="◀",
                    callback_data=f"inv:enchmenu:{scroll_id}:{bag_page}:{sec}:{page - 1}",
                ),
            )
        if page < total_pages:
            nav.append(
                InlineKeyboardButton(
                    text="▶",
                    callback_data=f"inv:enchmenu:{scroll_id}:{bag_page}:{sec}:{page + 1}",
                ),
            )
        if nav:
            rows.append(nav)
        rows.append(
            [InlineKeyboardButton(text="⬅ К свитку", callback_data=f"inv:it:{scroll_id}:b:{bag_page}:{sec}")],
        )
        rows.append(menu_nav_button_row())

        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=(
                "🧪 <b>Выбери предмет в сумке</b>\n\n"
                "<i>Совместимые слоты показаны ниже. Свиток расходуется при наложении.</i>"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            target_message=callback.message,
            character=char,
        )
        await callback.answer()
    except Exception:
        logger.exception("inv:enchmenu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:enchdo:"))
async def inv_alchemy_enchant_apply(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.data is None or callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await callback.answer("Снаружи боя.", show_alert=True)
            return
        parts = callback.data.split(":")
        if len(parts) < 6:
            await callback.answer()
            return
        scroll_id = int(parts[2])
        target_id = int(parts[3])
        bag_page = int(parts[4])
        sec = _normalize_inv_section(parts[5])

        _, char = await _load_character(session, callback.from_user.id)
        if char is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return

        ok, msg = await try_apply_alchemy_enchant(session, char, scroll_id, target_id)
        await session.commit()
        if not ok:
            await callback.answer(msg[:180], show_alert=True)
            return

        bag = await inventory_repo.list_bag_items(session, char.id)
        filtered = [it for it in bag if item_categories.item_data_matches_inv_section(it.item_data, sec)]
        max_page = max(0, (len(filtered) - 1) // BAG_PAGE_SIZE)
        safe_page = min(bag_page, max_page)
        text = (
            f"{_section_bag_intro(len(bag), section=sec, n_in_section=len(filtered), floor_number=int(char.floor_number))}"
            f"\n\n{msg}"
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=bag_tab_keyboard(bag, safe_page, section=sec),
            target_message=callback.message,
            character=char,
        )
        await callback.answer("Готово.")
    except Exception:
        logger.exception("inv:enchdo")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("inv:eq:"))
async def inv_equip(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        sec = _parse_sec_from_equip_callback(callback.data)
        item_id = int((callback.data or "").split(":")[2])
        # source — 5-й сегмент в `inv:eq:{id}:{sec}:{src}`; default 'b' для совместимости со старыми кнопками.
        parts = (callback.data or "").split(":")
        source = "e" if (len(parts) > 4 and parts[4] == "e") else "b"
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
        # Источник 'e' (пользователь пришёл из «Что надето») → «Назад» возвращает туда же.
        from_bag_after_eq = source != "e"
        kb = item_detail_keyboard(
            item.id,
            is_equipped=True,
            can_equip=can_equip,
            from_bag=from_bag_after_eq,
            bag_page=0,
            inv_section=sec,
            show_ration_eat=False,
            show_bread_eat=False,
            show_alchemy_enchant=False,
            source=source,
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            character=char,
        )
        try:
            from services import tutorial_service

            tutorial_service.mark_equipped_any(char)
            tutorial_service.advance_step_if_needed(char)
            await session.flush()
        except Exception:
            pass
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
        parts = (callback.data or "").split(":")
        item_id = int(parts[2])
        # source: `inv:uneq:{id}:{src}`; default 'e' (раньше unequip был только из карточки экипа).
        source = "b" if (len(parts) > 3 and parts[3] == "b") else "e"
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
        sec = infer_inv_section_from_item_data(dict(data))
        text = (
            f"{INV_HEADER}"
            f"{format_inventory_item_html(data)}\n\n"
            f"<b>Статус:</b> в сумке"
        )
        # После снятия предмет в сумке — кнопка «Назад» ведёт в сумку (это удобно: можно сразу
        # надеть замену из этой же категории). Источник 'e'/'b' пробрасываем дальше через
        # повторный equip — чтобы возврат к «Что надето» отрабатывал корректно.
        kb = item_detail_keyboard(
            item.id,
            is_equipped=False,
            can_equip=can_equip,
            from_bag=True,
            bag_page=0,
            inv_section=sec,
            show_ration_eat=item.bag_slot is not None and utag == "stamina_flat",
            show_bread_eat=item.bag_slot is not None and utag == "heal_hp_flat",
            show_alchemy_enchant=item.bag_slot is not None and utag == USE_TAG_ALCHEMY_ENCHANT,
            source=source,
        )
        await push_game_ui(
            state,
            callback.bot,
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=callback.message,
            character=char,
        )
        await callback.answer("Снято в сумку.")
    except Exception:
        logger.exception("inv:uneq")
        await callback.answer("Ошибка.", show_alert=True)
