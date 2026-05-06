"""
Кузница: заточка надетой экипировки в городах-хабах. Колбэки frg:*.
"""

from __future__ import annotations

import copy

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.utils.game_art import menu_city_photo_path
from bot.utils.game_ui import push_game_ui
from bot.keyboards.forge_kb import (
    city_hub_keyboard,
    forge_actions_keyboard,
    forge_craft_recipes_keyboard,
    forge_dis_bag_keyboard,
    forge_enchant_slots_keyboard,
    forge_quest_keyboard,
    forge_repair_keyboard,
    forge_set_shop_keyboard,
)
from db.repository import character_repo, inventory_repo, user_repo
from game.items.equipment import RARITY_NAME_RU, item_kind_label_ru
from game.floors import floor_data
from game.locations import forge as forge_loc
from game.crafting.recipes_data import forge_recipes_only
from services import crafting_service, forge_service
from services.floor_service import format_city_hub_message
from game.items.equipment.starters import promo_starter_armor_amulet_payloads, starter_pants_payload
from services import character_service
from game.items.equipment.defaults import apply_item_payload_defaults

router = Router(name="forge")

async def _answer_forge_runes_moved(query: CallbackQuery) -> None:
    await query.answer(
        "Руны: Мастерская → Ювелирная (кнопка «Мастерская» в меню).",
        show_alert=True,
    )


def _basic_set_goods() -> list[tuple[str, dict, int]]:
    armor, amulet = promo_starter_armor_amulet_payloads()
    pants = starter_pants_payload()
    helmet = {
        "name": "Шлем новичка",
        "kind": "helmet",
        "rarity": "common",
        "defense": 1,
        "vit": 1,
        "summary": "Тусклый шлем — защищает от мелких ударов.",
    }
    gloves = {
        "name": "Перчатки новичка",
        "kind": "gloves",
        "rarity": "common",
        "defense": 1,
        "dex": 1,
        "summary": "Не даёт соскальзывать руке с рукояти.",
    }
    ring = {
        "name": "Кольцо новичка",
        "kind": "ring",
        "rarity": "common",
        "defense": 1,
        "luck": 1,
        "summary": "Простое кольцо, найденное у входа в Башню.",
    }
    for d in (helmet, gloves, ring):
        apply_item_payload_defaults(d)
    # Prices (gold): low, intended for early game
    return [
        ("armor", armor, 250),
        ("pants", pants, 150),
        ("helmet", helmet, 150),
        ("gloves", gloves, 120),
        ("ring", ring, 160),
        ("amulet", amulet, 180),
    ]


@router.callback_query(F.data.startswith("frg:set:"))
async def forge_set_shop_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return
        goods = _basic_set_goods()
        items = [(k, str(p.get("name", k)), int(price)) for k, p, price in goods]
        body = (
            "🛒 <b>Базовый сет кузнеца</b>\n"
            "<i>Простая экипировка для старта. Покупки кладутся в сумку.</i>\n\n"
            "Выбери предмет:"
        )
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=body,
            reply_markup=forge_set_shop_keyboard(floor_key, items),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:set")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:setbuy:"))
async def forge_set_shop_buy(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        sp = query.data.split(":")
        if len(sp) < 4:
            await query.answer()
            return
        floor_key = int(sp[2])
        key = str(sp[3])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return
        goods = {k: (payload, int(price)) for k, payload, price in _basic_set_goods()}
        if key not in goods:
            await query.answer("Товар недоступен.", show_alert=True)
            return
        payload, price = goods[key]
        if int(char.gold or 0) < int(price):
            await query.answer("Не хватает золота.", show_alert=True)
            return
        await character_repo.lock_character_row(session, char.id)
        # spend + add item
        character_service.add_gold(char, -int(price), spend_for="Кузница: покупка сета", spend_kind="forge")
        added = await inventory_repo.add_bag_item(session, int(char.id), copy.deepcopy(payload))
        await session.flush()
        if added is None:
            # rollback spent gold
            character_service.add_gold(char, int(price))
            await session.flush()
            await query.answer("Сумка переполнена.", show_alert=True)
            return
        items = [(k, str(p.get("name", k)), int(pr)) for k, (p, pr) in goods.items()]
        text = f"✅ Куплено: <b>{str(payload.get('name', key))}</b> за <b>{price}💰</b>."
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=forge_set_shop_keyboard(floor_key, items),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer("Куплено!")
    except Exception:
        logger.exception("frg:setbuy")
        await query.answer("Ошибка.", show_alert=True)


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None
    return await character_repo.get_by_user_id(session, user.id)


@router.callback_query(F.data.startswith("frg:main:"))
async def forge_open_main(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже. Обнови /floor.", show_alert=True)
            return
        if not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Здесь нет кузницы.", show_alert=True)
            return
        text = await forge_service.build_forge_message_html(session, char)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=forge_actions_keyboard(char.floor_number),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:main")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:rpr:\d+$"))
async def forge_repair_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(str(query.data).split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Кузница недоступна.", show_alert=True)
            return
        text = await forge_service.build_repair_message_html(session, char)
        rows = await forge_service.list_repair_slot_button_rows(session, char.id)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=forge_repair_keyboard(char.floor_number, rows),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:rpr")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:rpr1:\d+:\w+$"))
async def forge_repair_slot_apply(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        _, _, fl_s, slot = str(query.data).split(":", 3)
        floor_key = int(fl_s)
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Кузница недоступна.", show_alert=True)
            return
        ok, lines = await forge_service.try_repair_equipped_slot(session, char, slot)
        if ok:
            text = await forge_service.build_repair_message_html(session, char)
            rows = await forge_service.list_repair_slot_button_rows(session, char.id)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=forge_repair_keyboard(char.floor_number, rows),
                target_message=query.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            await query.answer("Починено.", show_alert=False)
        else:
            await query.answer(lines[0] if lines else "Нельзя.", show_alert=True)
    except Exception:
        logger.exception("frg:rpr1")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:rpra:\d+$"))
async def forge_repair_all_apply(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(str(query.data).split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Кузница недоступна.", show_alert=True)
            return
        ok, lines = await forge_service.try_repair_all_equipped(session, char)
        if ok:
            text = await forge_service.build_repair_message_html(session, char)
            rows = await forge_service.list_repair_slot_button_rows(session, char.id)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=forge_repair_keyboard(char.floor_number, rows),
                target_message=query.message,
                photo_path=menu_city_photo_path(),
                character=char,
            )
            await query.answer("Вся экипировка починена.", show_alert=False)
        else:
            await query.answer(lines[0] if lines else "Нельзя.", show_alert=True)
    except Exception:
        logger.exception("frg:rpra")
        await query.answer("Ошибка.", show_alert=True)


async def _handle_forge_enchant_callback(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    *,
    rune_ward: bool,
) -> None:
    if query.data is None or query.from_user is None or query.message is None:
        await query.answer()
        return
    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer()
        return
    floor_key = int(parts[2])
    char = await _load_char(session, query.from_user.id)
    if char is None:
        await query.answer("Нет персонажа.", show_alert=True)
        return
    if char.floor_number != floor_key:
        await query.answer("Ты не на этом этаже.", show_alert=True)
        return
    if not forge_loc.forge_available_on_floor(char.floor_number):
        await query.answer("Здесь нет кузницы.", show_alert=True)
        return

    if len(parts) == 3:
        rows = await forge_service.list_enchant_slot_button_rows(session, char.id)
        if not rows:
            await query.answer("Нет надетых предметов для заточки.", show_alert=True)
            return
        text = await forge_service.build_forge_message_html(session, char)
        hint = (
            "\n\n<i>Выбери слот с рунной подстраховкой (без −1):</i>"
            if rune_ward
            else "\n\n<i>Выбери слот для заточки:</i>"
        )
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text + hint,
            reply_markup=forge_enchant_slots_keyboard(floor_key, rows, ward=rune_ward),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer("Выбери слот")
        return

    slot = parts[3]
    ok, result_lines = await forge_service.try_enchant_equipped_in_slot(
        session,
        char,
        slot,
        rune_ward=rune_ward,
    )
    if not ok:
        msg = result_lines[0] if result_lines else "Нельзя."
        await query.answer(msg[:180], show_alert=True)
        return

    body = "\n".join(result_lines)
    refreshed = await forge_service.build_forge_message_html(session, char)
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=f"{refreshed}\n\n{body}",
        reply_markup=forge_actions_keyboard(char.floor_number),
        target_message=query.message,
        photo_path=menu_city_photo_path(),
        character=char,
    )
    await query.answer("Готово!")


@router.callback_query(F.data.startswith("frg:ench:"))
async def forge_enchant(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _handle_forge_enchant_callback(query, session, state, rune_ward=False)
    except Exception:
        logger.exception("frg:ench")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:enchw:"))
async def forge_enchant_rune_ward(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _handle_forge_enchant_callback(query, session, state, rune_ward=True)
    except Exception:
        logger.exception("frg:enchw")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:craft:"))
async def forge_craft_menu(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        if not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Здесь нет кузницы.", show_alert=True)
            return
        rows: list[tuple[str, str]] = []
        for r in forge_recipes_only():
            rid = str(r.get("id", ""))
            if not rid:
                continue
            name = str(r.get("name_ru", rid))
            desc = str(r.get("description", ""))[:32]
            rows.append((rid, f"{name} — {desc}"))
        if not rows:
            await query.answer("Нет рецептов.", show_alert=True)
            return
        top = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{top}\n\n<i>Выбери рецепт (с материалами в сумке):</i>",
            reply_markup=forge_craft_recipes_keyboard(floor_key, rows),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:craft")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:crf:"))
async def forge_craft_run(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        sp = query.data.split(":")
        if len(sp) < 4:
            await query.answer()
            return
        floor_key = int(sp[2])
        recipe_id = str(sp[3])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        ok, lines = await crafting_service.try_craft(session, char, recipe_id)
        if not ok:
            await query.answer((lines[0] if lines else "Нельзя.")[:180], show_alert=True)
            return
        body = "\n".join(lines)
        refreshed = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{refreshed}\n\n{body}",
            reply_markup=forge_actions_keyboard(char.floor_number),
            parse_mode=ParseMode.HTML,
        )
        await query.answer("Сварено!" if "насто" in body.lower() else "Готово!")
    except Exception:
        logger.exception("frg:crf")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:brew:"))
async def forge_brew_elixir(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return

        ok, result_lines = await forge_service.try_brew_city_elixir(session, char)
        if not ok:
            msg = result_lines[0] if result_lines else "Нельзя."
            await query.answer(msg[:180], show_alert=True)
            return

        body = "\n".join(result_lines)
        refreshed = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{refreshed}\n\n{body}",
            reply_markup=forge_actions_keyboard(char.floor_number),
        )
        await query.answer("Сварено!")
    except Exception:
        logger.exception("frg:brew")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:city:"))
async def forge_back_city(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Этаж устарел.", show_alert=True)
            return
        if floor_data.get_city_for_floor(char.floor_number) is None:
            await query.answer()
            return
        text = format_city_hub_message(char)
        loc = get_locale(char, query.from_user.language_code)
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=city_hub_keyboard(char.floor_number, char, locale=loc),
            target_message=query.message,
            photo_path=menu_city_photo_path(),
            character=char,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:city")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rnm:"))
async def forge_rune_menu(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _answer_forge_runes_moved(query)
    except Exception:
        logger.exception("frg:rnm")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rsl:"))
async def forge_rune_pick_bag(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _answer_forge_runes_moved(query)
    except Exception:
        logger.exception("frg:rsl")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rsi:"))
async def forge_rune_socket_apply(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _answer_forge_runes_moved(query)
    except Exception:
        logger.exception("frg:rsi")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rrm:"))
async def forge_rune_remove_menu(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _answer_forge_runes_moved(query)
    except Exception:
        logger.exception("frg:rrm")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rrx:"))
async def forge_rune_remove_apply(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _answer_forge_runes_moved(query)
    except Exception:
        logger.exception("frg:rrx")
        await query.answer("Ошибка.", show_alert=True)


def _norm_filter(v: str) -> str | None:
    if not v or v == "all":
        return None
    return str(v).lower()


@router.callback_query(F.data.regexp(r"^frg:dis:\d+$"))
async def forge_disassemble_menu(query: CallbackQuery, session: AsyncSession) -> None:
    """Показать список предметов из сумки для разбора (без фильтров)."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Здесь нет кузницы.", show_alert=True)
            return
        pairs = await forge_service.list_disassemblable_items(session, char)
        if not pairs:
            await query.answer("В сумке нет предметов для разбора.", show_alert=True)
            return
        await query.message.edit_text(
            "🔨 <b>Разбор предмета</b>\n"
            "<i>Выбери вещь или используй фильтры/свип ниже.</i>",
            reply_markup=forge_dis_bag_keyboard(floor_key, pairs),
            parse_mode="HTML",
        )
        await query.answer("Выбери предмет для разбора")
    except Exception:
        logger.exception("frg:dis")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:disf:\d+:[a-z]+:[a-z]+$"))
async def forge_disassemble_filter(query: CallbackQuery, session: AsyncSession) -> None:
    """Применить фильтры (редкость/тип) для списка разбора."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        rar_code = parts[3]
        knd_code = parts[4]
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        if not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Здесь нет кузницы.", show_alert=True)
            return
        rar = _norm_filter(rar_code)
        knd = _norm_filter(knd_code)
        pairs = await forge_service.list_disassemblable_items(
            session, char, rarity_filter=rar, kind_filter=knd,
        )
        title = "🔨 <b>Разбор предмета</b>"
        if rar or knd:
            rar_s = RARITY_NAME_RU.get(str(rar), rar) if rar else "все редкости"
            knd_s = item_kind_label_ru(str(knd)) if knd else "все типы"
            title += f"\n<i>Фильтр:</i> {rar_s} / {knd_s}"
        if not pairs:
            title += "\n<i>Под фильтр ничего не попало.</i>"
        await query.message.edit_text(
            title,
            reply_markup=forge_dis_bag_keyboard(
                floor_key, pairs, rarity_filter=rar, kind_filter=knd,
            ),
            parse_mode="HTML",
        )
        await query.answer()
    except Exception:
        logger.exception("frg:disf")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:dsweep:\d+:[a-z]+$"))
async def forge_disassemble_sweep(query: CallbackQuery, session: AsyncSession) -> None:
    """Свип: разобрать всё (≤max_rarity) пачкой."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        max_rar = parts[3]
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        ok, msg = await forge_service.try_sweep_disassemble(session, char, max_rarity=max_rar)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        body = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{body}\n\n{msg}",
            reply_markup=forge_actions_keyboard(char.floor_number),
            parse_mode="HTML",
        )
        await query.answer("Свип готов!")
    except Exception:
        logger.exception("frg:dsweep")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:disx:"))
async def forge_disassemble_apply(query: CallbackQuery, session: AsyncSession) -> None:
    """Разобрать выбранный предмет."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        item_id = int(parts[3])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        ok, msg = await forge_service.try_disassemble_bag_item(session, char, item_id)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        body = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{body}\n\n{msg}",
            reply_markup=forge_actions_keyboard(char.floor_number),
            parse_mode="HTML",
        )
        await query.answer("Разобрано!")
    except Exception:
        logger.exception("frg:disx")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rca:"))
async def forge_rune_craft_auto(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _answer_forge_runes_moved(query)
    except Exception:
        logger.exception("frg:rca")
        await query.answer("Ошибка.", show_alert=True)


# ── Задания кузнеца (цепочка) ─────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^frg:qst:\d+$"))
async def forge_quest_open(query: CallbackQuery, session: AsyncSession) -> None:
    """Открыть экран цепочки заданий кузнеца."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        from services import forge_quest_service as fqs
        text = fqs.format_forge_quest_html(char, floor_key)
        state = fqs._get_state(char, floor_key)
        await query.message.edit_text(
            text,
            reply_markup=forge_quest_keyboard(floor_key, state),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:qst open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:qst:start:\d+$"))
async def forge_quest_start(query: CallbackQuery, session: AsyncSession) -> None:
    """Начать цепочку заданий кузнеца."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[3])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        from services import forge_quest_service as fqs
        ok = fqs.start_chain(char, floor_key)
        if not ok:
            await query.answer("Цепочка уже начата или недоступна.", show_alert=True)
            return
        await session.flush()
        text = fqs.format_forge_quest_html(char, floor_key)
        state = fqs._get_state(char, floor_key)
        await query.message.edit_text(
            text,
            reply_markup=forge_quest_keyboard(floor_key, state),
            parse_mode=ParseMode.HTML,
        )
        await query.answer("📜 Цепочка заданий начата!")
    except Exception:
        logger.exception("frg:qst:start")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:qst:claim:\d+:\d+$"))
async def forge_quest_claim_step(query: CallbackQuery, session: AsyncSession) -> None:
    """Сдать шаг цепочки кузнеца."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[3])
        step = int(parts[4])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        from services import forge_quest_service as fqs
        ok, msg = await fqs.claim_step(session, char, floor_key, step)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        # Читаем state ДО commit, пока char не сброшен в сессии
        text = fqs.format_forge_quest_html(char, floor_key)
        state = fqs._get_state(char, floor_key)
        await session.commit()
        await query.message.edit_text(
            f"{text}\n\n{msg}",
            reply_markup=forge_quest_keyboard(floor_key, state),
            parse_mode=ParseMode.HTML,
        )
        await query.answer("✅ Шаг выполнен!")
    except Exception:
        logger.exception("frg:qst:claim")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^frg:qst:final:\d+$"))
async def forge_quest_final(query: CallbackQuery, session: AsyncSession) -> None:
    """Получить финальную награду цепочки кузнеца."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[3])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        from services import forge_quest_service as fqs
        ok, msg = await fqs.claim_final_reward(session, char, floor_key)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        # Читаем state ДО commit
        state = fqs._get_state(char, floor_key)
        await session.commit()
        await query.message.edit_text(
            msg,
            reply_markup=forge_quest_keyboard(floor_key, state),
            parse_mode=ParseMode.HTML,
        )
        await query.answer("🏆 Цепочка завершена!")
    except Exception:
        logger.exception("frg:qst:final")
        await query.answer("Ошибка.", show_alert=True)
