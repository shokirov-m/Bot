"""
Кузница: заточка надетой экипировки в городах-хабах. Колбэки frg:*.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.forge_kb import (
    city_hub_keyboard,
    forge_actions_keyboard,
    forge_enchant_slots_keyboard,
    forge_rune_bag_pick_keyboard,
    forge_rune_menu_keyboard,
    forge_rune_socket_pick_keyboard,
)
from db.repository import character_repo, inventory_repo, user_repo
from game.items.runes import RuneData, ensure_rune_socket_list, extract_rune_from_item
from game.floors import floor_data
from game.locations import forge as forge_loc
from services import forge_service
from services.floor_service import format_city_hub_message

router = Router(name="forge")


async def _load_char(session: AsyncSession, telegram_id: int):
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user is None or user.is_banned:
        return None
    return await character_repo.get_by_user_id(session, user.id)


@router.callback_query(F.data.startswith("frg:main:"))
async def forge_open_main(query: CallbackQuery, session: AsyncSession) -> None:
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
        await query.message.edit_text(
            text,
            reply_markup=forge_actions_keyboard(char.floor_number),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("frg:main")
        await query.answer("Ошибка.", show_alert=True)


async def _handle_forge_enchant_callback(
    query: CallbackQuery,
    session: AsyncSession,
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
        await query.message.edit_text(
            text + hint,
            reply_markup=forge_enchant_slots_keyboard(floor_key, rows, ward=rune_ward),
            parse_mode=ParseMode.HTML,
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
    await query.message.edit_text(
        f"{refreshed}\n\n{body}",
        reply_markup=forge_actions_keyboard(char.floor_number),
        parse_mode=ParseMode.HTML,
    )
    await query.answer("Готово!")


@router.callback_query(F.data.startswith("frg:ench:"))
async def forge_enchant(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _handle_forge_enchant_callback(query, session, rune_ward=False)
    except Exception:
        logger.exception("frg:ench")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:enchw:"))
async def forge_enchant_rune_ward(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await _handle_forge_enchant_callback(query, session, rune_ward=True)
    except Exception:
        logger.exception("frg:enchw")
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
async def forge_back_city(query: CallbackQuery, session: AsyncSession) -> None:
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
        await query.message.edit_text(text, reply_markup=city_hub_keyboard(char.floor_number))
        await query.answer()
    except Exception:
        logger.exception("frg:city")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rnm:"))
async def forge_rune_menu(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        if char.floor_number != floor_key or not forge_loc.forge_available_on_floor(char.floor_number):
            await query.answer("Здесь нет кузницы.", show_alert=True)
            return
        text = (
            await forge_service.build_forge_message_html(session, char)
            + "\n\n💎 <b>Руны</b>\nВставляй камни в гнёзда оружия (редкость влияет на число гнёз). "
            "Извлечение — 50% потерять руну.\n⚠️ <i>Авто-крафт: две руны I одной стихии → II (−1000 💰).</i>"
        )
        await query.message.edit_text(text, reply_markup=forge_rune_menu_keyboard(char.floor_number))
        await query.answer()
    except Exception:
        logger.exception("frg:rnm")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rsl:"))
async def forge_rune_pick_bag(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Нельзя.", show_alert=True)
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        pairs: list[tuple[int, str]] = []
        for it in bag:
            rd = extract_rune_from_item(dict(it.item_data or {}))
            if rd is not None:
                pairs.append((int(it.id), rd.display_name))
        if not pairs:
            await query.answer("В сумке нет рун.", show_alert=True)
            return
        await query.message.edit_text(
            "💎 <b>Выбери руну из сумки</b> — вставим в надетое оружие.",
            reply_markup=forge_rune_bag_pick_keyboard(char.floor_number, pairs),
        )
        await query.answer()
    except Exception:
        logger.exception("frg:rsl")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rsi:"))
async def forge_rune_socket_apply(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        rune_id = int(parts[3])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Нельзя.", show_alert=True)
            return
        ok, msg = await forge_service.socket_rune_into_equipped_weapon(
            session,
            char,
            rune_bag_item_id=rune_id,
        )
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        body = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{body}\n\n{msg}",
            reply_markup=forge_rune_menu_keyboard(char.floor_number),
        )
        await query.answer("Готово!")
    except Exception:
        logger.exception("frg:rsi")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rrm:"))
async def forge_rune_remove_menu(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Нельзя.", show_alert=True)
            return
        weapon = await inventory_repo.get_equipped_weapon(session, char.id)
        if weapon is None:
            await query.answer("Нет оружия.", show_alert=True)
            return
        wdata = dict(weapon.item_data or {})
        ensure_rune_socket_list(wdata)
        sockets = wdata.get("rune_sockets") or []
        labels: list[tuple[int, str]] = []
        for i, cell in enumerate(sockets):
            if isinstance(cell, dict) and cell.get("element"):
                try:
                    rd = RuneData.from_dict(cell)
                    labels.append((i, f"#{i + 1} {rd.display_name}"))
                except (ValueError, TypeError, KeyError):
                    labels.append((i, f"#{i + 1} ?"))
        if not labels:
            await query.answer("Нет вставленных рун.", show_alert=True)
            return
        await query.message.edit_text(
            "🔓 <b>Извлечь руну</b>\n⚠️ 50% шанс, что руна рассыплется.",
            reply_markup=forge_rune_socket_pick_keyboard(char.floor_number, labels),
        )
        await query.answer()
    except Exception:
        logger.exception("frg:rrm")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rrx:"))
async def forge_rune_remove_apply(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        parts = query.data.split(":")
        floor_key = int(parts[2])
        idx = int(parts[3])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Нельзя.", show_alert=True)
            return
        ok, msg, _saved = await forge_service.remove_rune_from_equipped_weapon(
            session,
            char,
            socket_index=idx,
        )
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        body = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{body}\n\n{msg}",
            reply_markup=forge_rune_menu_keyboard(char.floor_number),
        )
        await query.answer()
    except Exception:
        logger.exception("frg:rrx")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("frg:rca:"))
async def forge_rune_craft_auto(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor_key = int(query.data.split(":")[2])
        char = await _load_char(session, query.from_user.id)
        if char is None or char.floor_number != floor_key:
            await query.answer("Нельзя.", show_alert=True)
            return
        ok, msg = await forge_service.craft_rune_auto_pair_rank1(session, char)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        body = await forge_service.build_forge_message_html(session, char)
        await query.message.edit_text(
            f"{body}\n\n{msg}",
            reply_markup=forge_rune_menu_keyboard(char.floor_number),
        )
        await query.answer("Слито!")
    except Exception:
        logger.exception("frg:rca")
        await query.answer("Ошибка.", show_alert=True)
