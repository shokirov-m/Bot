"""
Экран текущего этажа: /floor, навигация по открытым этажам, выбор монстра.
"""

from __future__ import annotations

import html
import random
import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.floor_kb import secret_result_keyboard
from bot.keyboards.forest_kb import forest_mushroom_keyboard, forest_spirit_keyboard
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, user_repo
from config import is_admin
from game.characters import pets as pets_mod
from game.floors import floor_data
from game.floors import wandering_npcs as wandering_npcs_mod
from game.floors import forest_beginnings as fb
from game.floors import long_floor as long_floor_mod
from game.floors import room_clear_floor as rc_mod
from game.floors import room_clear_floor_10 as rc10_mod
from game.floors import room_clear_floor_24 as rc24_mod
from game.floors import wave_floor as wv_mod
from game.floors import wave_floor_27 as wv27_mod
from game.floors import explore_floor as exp_mod
from game.floors import explore_floor_4 as exp4_mod
from game.floors import explore_floor_22 as exp22_mod
from services import combat_service, golden_goblin_service
from services.floor_service import (
    floor_keyboard_for_character,
    get_spawns_for_character_session,
    push_floor_screen_ui,
    travel_by_delta,
    travel_to_floor,
    try_secret_search,
)
from utils.ui import LINE_SEP

router = Router(name="floor")

_FLOOR_CB = re.compile(r"^fl:(\d+):([a-z0-9_]+)$")
_SCR_CB = re.compile(r"^scr:(\d+|back|backmkt)$")


@router.message(Command("floor"))
@router.message(Command("этаж"))
async def cmd_floor(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показать этаж и доступных монстров."""
    try:
        if message.from_user is None:
            return
        tg = message.from_user
        user = await user_repo.get_by_telegram_id(session, tg.id)
        if user is None or user.is_banned:
            await message.answer("Сначала нажми /start.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Создай героя через /start.")
            return

        if int(char.floor_number) == 0:
            from bot.handlers.floor_zero import show_floor0
            await show_floor0(message, state)
            return

        kb = await floor_keyboard_for_character(session, char, telegram_user_id=tg.id)
        await push_floor_screen_ui(
            session,
            state,
            message.bot,
            chat_id=message.chat.id,
            character=char,
            reply_markup=kb,
            fallback_message=message,
        )
    except Exception:
        logger.exception("Ошибка в /floor")


@router.callback_query(F.data.in_(("flnav:up", "flnav:dn")))
async def on_floor_nav_step(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.from_user is None or query.message is None or query.data is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        delta = 1 if query.data == "flnav:up" else -1
        _adm_nav = is_admin(query.from_user.id)
        ok, err = await travel_by_delta(
            session,
            char,
            delta,
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            bot=query.bot,
            admin_floor_bypass=_adm_nav,
        )
        if not ok:
            await query.answer(err or "Нельзя.", show_alert=True)
            return
        await push_floor_screen_ui(
            session,
            state,
            query.bot,
            chat_id=query.message.chat.id,
            character=char,
            reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
            target_message=query.message,
        )
        await query.answer(f"Этаж {char.floor_number}")
    except Exception:
        logger.exception("flnav")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("scr:"))
async def on_scrap_merchant_callback(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        m = _SCR_CB.match(query.data)
        if m is None:
            await query.answer()
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        tok = m.group(1)
        if tok == "back":
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer()
            return
        if tok == "backmkt":
            if int(char.floor_number) != 3:
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                    target_message=query.message,
                )
            else:
                from bot.keyboards.city_market_kb import city_floor3_market_keyboard

                await query.message.edit_text(
                    "🏛️ <b>Рынок «Тихий Ручей»</b>\n"
                    "<i>Лавка, скупщик, сейф банка и храм призыва — выбери ниже.</i>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=city_floor3_market_keyboard(char.floor_number),
                )
            await query.answer()
            return
        from bot.keyboards.scrap_kb import scrap_merchant_keyboard, scrap_ui_back
        from db.repository import inventory_repo
        from services import scrap_merchant_service

        ok, msg = await scrap_merchant_service.try_sell_bag_item_by_id(
            session,
            char,
            int(tok),
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            bot=query.bot,
        )
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        await session.refresh(char)
        items = await inventory_repo.list_bag_items(session, char.id)
        text = scrap_merchant_service.format_scrap_menu_html(char, items)
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=scrap_merchant_keyboard(items, back=scrap_ui_back(char)),
        )
        await query.answer("Продано.", show_alert=False)
    except Exception:
        logger.exception("scr callback")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wv:locked")
async def on_wave_locked(query: CallbackQuery, **_: object) -> None:
    await query.answer("Сначала победи предыдущую волну.", show_alert=True)


@router.callback_query(F.data == "rc:locked")
async def on_room_locked(query: CallbackQuery, **_: object) -> None:
    await query.answer("Сначала зачисти предыдущую комнату.", show_alert=True)


@router.callback_query(F.data == "rc10:locked")
async def on_room_10_locked(query: CallbackQuery, **_: object) -> None:
    await query.answer("Сначала зачисти предыдущую комнату. 🔒", show_alert=True)


@router.callback_query(F.data == "rc24:locked")
async def on_room_24_locked(query: CallbackQuery, **_: object) -> None:
    await query.answer("Сначала зачисти предыдущую комнату Пещеры. 🔒", show_alert=True)


@router.callback_query(F.data == "wv27:locked")
async def on_wave_27_locked(query: CallbackQuery, **_: object) -> None:
    await query.answer("Сначала победи предыдущую волну теней.", show_alert=True)


@router.callback_query(F.data.startswith("fl:"))
async def on_floor_callback(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Выбор цели на этаже — старт боя."""
    try:
        if query.data is None or query.from_user is None:
            await query.answer()
            return

        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши текущий бой.", show_alert=True)
            return

        m = _FLOOR_CB.match(query.data)
        if m is None:
            await query.answer()
            return

        floor = int(m.group(1))
        code = m.group(2)

        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return

        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return

        # Авто-пополнение ресурсов для администратора
        if is_admin(query.from_user.id):
            try:
                from services.admin_utils import ensure_admin_resources
                await ensure_admin_resources(session, char)
            except Exception:
                pass

        if int(char.floor_number) == 0:
            from bot.handlers.floor_zero import show_floor0_from_callback
            await show_floor0_from_callback(query, state)
            return

        if floor != char.floor_number:
            await query.answer("Этаж устарел. Открой /floor снова.", show_alert=True)
            return

        if code == "tutorial":
            if int(char.floor_number) != 2:
                await query.answer("Обучение у наставника доступно на 2 этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            await combat_service.start_tutorial_combat(
                query=query,
                session=session,
                state=state,
                character=char,
            )
            return

        if code == "wnpc":
            info = wandering_npcs_mod.wandering_npc_for_floor(int(char.id), floor)
            if info is None:
                await query.answer("Сейчас здесь никого нет.", show_alert=True)
                return
            from services import wandering_npc_quest_service as wnpc_qs
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            text = wnpc_qs.format_npc_quest_screen(char, floor)
            q_state = wnpc_qs.get_quest_for_floor(char, floor)
            rows: list[list[InlineKeyboardButton]] = []
            if q_state is None:
                rows.append([InlineKeyboardButton(
                    text="📜 Взять задание",
                    callback_data=f"wnpc:take:{floor}",
                )])
            elif wnpc_qs.can_claim(char, floor):
                rows.append([InlineKeyboardButton(
                    text="🎁 Получить награду",
                    callback_data=f"wnpc:claim:{floor}",
                )])
            rows.append([InlineKeyboardButton(
                text="⬅ Назад",
                callback_data=f"fl:{floor}:back",
            )])
            kb = InlineKeyboardMarkup(inline_keyboard=rows)
            if query.message is not None:
                await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
            await query.answer()
            return

        if code == "story_npc":
            if int(char.floor_number) != 1:
                await query.answer("Сюжетные NPC только на 1 этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            from game.quests.story_quests import STORY_QUESTS, get_quest_state, claim_quest_reward, accept_quest
            rows_npc: list[list[InlineKeyboardButton]] = []
            for sq in STORY_QUESTS:
                st = get_quest_state(char, sq.quest_id)
                label = f"{sq.npc_emoji} {sq.npc_name}"
                if st == "done":
                    label += " ✅"
                elif st == "active":
                    label += " 🔄"
                rows_npc.append([InlineKeyboardButton(
                    text=label,
                    callback_data=f"sq:npc:{sq.npc_key}",
                )])
            rows_npc.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"fl:{floor}:back")])
            text_npc = (
                "📜 <b>Сюжетные NPC — Тихий Ручей</b>\n\n"
                "Здесь живут необычные обитатели Башни. "
                "У каждого — своя история и задание для тебя.\n\n"
                "🔄 = задание активно\n✅ = выполнено\n"
            )
            await query.message.edit_text(
                text_npc,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows_npc),
            )
            await query.answer()
            return

        if code in ("petg", "petr", "petw"):
            if query.message is None:
                await query.answer()
                return
            if code in ("petg", "petr"):
                await query.answer(
                    "Призыв питомца — в разделе «Город» (лавка хаба).",
                    show_alert=True,
                )
                return
            else:
                if int(char.floor_number) not in pets_mod.pet_gacha_floors_for_pet_switch():
                    await query.answer()
                    return
                disp = pets_mod.cycle_active_pet(char)
                await session.flush()
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                    target_message=query.message,
                )
                await query.answer(
                    (f"Активен: {disp}" if disp else "Нужно минимум 2 питомца.")[:200],
                    show_alert=True,
                )
                return

        if code == "scrap":
            if query.message is None:
                await query.answer()
                return
            from services import scrap_merchant_service as _scrap

            if not _scrap.is_scrap_floor(floor):
                await query.answer(_scrap.scrap_unavailable_message(int(floor)), show_alert=True)
                return
            from bot.keyboards.scrap_kb import scrap_merchant_keyboard, set_scrap_ui_back
            from db.repository import inventory_repo
            from services import scrap_merchant_service

            set_scrap_ui_back(char, "floor")
            items = await inventory_repo.list_bag_items(session, char.id)
            text = scrap_merchant_service.format_scrap_menu_html(char, items)
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=scrap_merchant_keyboard(items, back="floor"),
            )
            await query.answer()
            return

        if code == "classtalk":
            await query.answer(
                "Наставник Эрида больше не распределяет классы — используй «Профессии» в статусе или меню.",
                show_alert=True,
            )
            return

        if code == "back":
            if query.message is None:
                await query.answer()
                return
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer()
            return

        if code == "return":
            if query.message is None:
                await query.answer()
                return
            await state.update_data(svc_forest_spirit=None)
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer()
            return

        if code == "survival_info":
            from game.floors.floor_data import get_zone_raw, get_zone_for_floor
            zone_s = get_zone_for_floor(floor)
            zone_raw_s = get_zone_raw(floor)
            debuff_s = zone_raw_s.get("debuff", {})
            prot_name_s = debuff_s.get("protection_item_name", "защитный предмет")
            hp_s = debuff_s.get("hp_per_min", 50)
            mp_s = dict(char.meta_progress or {})
            has_prot_s = bool(mp_s.get(f"survival_prot_{zone_s.key}"))
            if has_prot_s:
                await query.answer(
                    f"🛡️ Защита активна! {prot_name_s} защищает тебя от −{hp_s} HP/мин холода.",
                    show_alert=True,
                )
            else:
                await query.answer(
                    f"🥶 Смертельный холод! Каждую минуту −{hp_s} HP.\n"
                    f"Скрафти «{prot_name_s}» у алхимика в городе (действует 12ч).",
                    show_alert=True,
                )
            return

        if code == "faction_choose":
            from game.floors.floor_data import get_zone_raw, get_zone_for_floor
            zone_fw = get_zone_for_floor(floor)
            zone_raw_fw = get_zone_raw(floor)
            factions_fw = zone_raw_fw.get("factions", {})
            if not factions_fw:
                await query.answer("Нет данных о фракциях.", show_alert=True)
                return
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            btn_rows = []
            for fkey, fdata in factions_fw.items():
                btn_rows.append([InlineKeyboardButton(
                    text=f"{fdata['emoji']} {fdata['name']} — {fdata.get('reward_passive_desc', '')}",
                    callback_data=f"fl:{floor}:faction_join:{fkey}",
                )])
            btn_rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"fl:{floor}:back")])
            kb_fw = InlineKeyboardMarkup(inline_keyboard=btn_rows)
            if query.message:
                from aiogram.enums import ParseMode
                fac_list = "\n".join(
                    f"{fd['emoji']} <b>{fd['name']}</b>\n"
                    f"  • Пассивка за верность: <i>{fd.get('reward_passive_desc', '?')}</i>"
                    for fd in factions_fw.values()
                )
                req_fw = zone_raw_fw.get("reputation_required", 1000)
                txt = (
                    f"⚔️ <b>Война Фракций — {zone_fw.name}</b>\n\n"
                    f"Убивай врагов выбранной фракции, чтобы набрать <b>{req_fw}</b> репутации.\n"
                    f"Достигнув порога, сможешь вызвать Генерала — финального босса этажа.\n\n"
                    f"<b>Фракции:</b>\n{fac_list}\n\n"
                    f"<i>Выбор постоянный для этой зоны.</i>"
                )
                from bot.utils.game_ui import push_game_ui
                await push_game_ui(state, query.bot, chat_id=query.message.chat.id,
                                   text=txt, reply_markup=kb_fw, target_message=query.message)
            await query.answer()
            return

        if code.startswith("faction_join:"):
            faction_key = code.split(":", 1)[1]
            from game.floors.floor_data import get_zone_raw, get_zone_for_floor
            zone_fw2 = get_zone_for_floor(floor)
            zone_raw_fw2 = get_zone_raw(floor)
            factions_fw2 = zone_raw_fw2.get("factions", {})
            if faction_key not in factions_fw2:
                await query.answer("Неизвестная фракция.", show_alert=True)
                return
            mp_fw2 = dict(char.meta_progress or {})
            existing_choice = mp_fw2.get(f"faction_choice_{zone_fw2.key}")
            if existing_choice:
                fac_name = factions_fw2.get(existing_choice, {}).get("name", existing_choice)
                await query.answer(f"Ты уже выбрал: {fac_name}. Смена невозможна.", show_alert=True)
                return
            mp_fw2[f"faction_choice_{zone_fw2.key}"] = faction_key
            char.meta_progress = mp_fw2
            await session.flush()
            fac_name2 = factions_fw2[faction_key]["name"]
            fac_emoji2 = factions_fw2[faction_key]["emoji"]
            await query.answer(f"✅ Ты вступил в {fac_emoji2} {fac_name2}! Убивай врагов для репутации.", show_alert=True)
            if query.message:
                await push_floor_screen_ui(
                    session, state, query.bot,
                    chat_id=query.message.chat.id, character=char,
                    reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                    target_message=query.message,
                )
            return

        if code.startswith("faction_boss:"):
            faction_key_boss = code.split(":", 1)[1]
            from game.floors.floor_data import get_zone_raw, get_zone_for_floor
            zone_bw = get_zone_for_floor(floor)
            zone_raw_bw = get_zone_raw(floor)
            factions_bw = zone_raw_bw.get("factions", {})
            req_bw = int(zone_raw_bw.get("reputation_required", 1000))
            if faction_key_boss not in factions_bw:
                await query.answer("Неизвестная фракция.", show_alert=True)
                return
            mp_bw = dict(char.meta_progress or {})
            rep_bw = int(mp_bw.get(f"faction_rep_{zone_bw.key}", {}).get(faction_key_boss, 0))
            if rep_bw < req_bw:
                await query.answer(f"Нужно {req_bw} репутации. У тебя: {rep_bw}.", show_alert=True)
                return
            # Start boss fight with faction general (use eternity_judge boss as placeholder)
            code = "b"  # route to major boss fight

        if code == "ascend":
            if query.message is None:
                await query.answer()
                return
            from game.floors.tower_ascent import tower_next_floor_pending, set_tower_ascent_pending

            pend = tower_next_floor_pending(char)
            if pend is None:
                if is_admin(query.from_user.id):
                    # Администратор: автоматически открываем следующий этаж
                    next_fl = int(char.floor_number) + 1
                    if next_fl > 135:
                        await query.answer("Это максимальный этаж.", show_alert=True)
                        return
                    set_tower_ascent_pending(char, next_fl)
                    # Обновить highest_floor_reached если нужно
                    if next_fl > int(char.highest_floor_reached):
                        char.highest_floor_reached = next_fl
                    await session.flush()
                    pend = next_fl
                else:
                    await query.answer("Сначала победи все цели на этом этаже.", show_alert=True)
                    return
            ok, err = await travel_to_floor(
                session,
                char,
                pend,
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                bot=query.bot,
                admin_floor_bypass=is_admin(query.from_user.id),
            )
            if not ok:
                await query.answer(err or "Нельзя подняться.", show_alert=True)
                return
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer(f"Этаж {char.floor_number}")
            return

        if code == "down":
            if query.message is None:
                await query.answer()
                return
            ok, err = await travel_by_delta(
                session,
                char,
                -1,
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                bot=query.bot,
                admin_floor_bypass=is_admin(query.from_user.id),
            )
            if not ok:
                await query.answer(err or "Нельзя.", show_alert=True)
                return
            await push_floor_screen_ui(
                session,
                state,
                query.bot,
                chat_id=query.message.chat.id,
                character=char,
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer(f"Этаж {char.floor_number}")
            return

        # ── Этаж 24: зачистка комнат Пещер Теней ────────────────────────────
        if code in rc24_mod.ROOM_CLEAR_24_ALL_SLOTS:
            if not rc24_mod.is_room_clear_floor_24(floor):
                await query.answer("Этот сценарий только на 24-м этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            from db.repository import floor_progress_repo as fpr
            _row = await fpr.ensure_floor_row(session, char.id, floor)
            _ex = dict(_row.extra or {})
            _beaten = frozenset(str(x) for x in (_ex.get("slots_cleared") or []))

            _actual_slot = code
            _room_idx = rc24_mod.room_index_for_button(code)
            if _room_idx is not None:
                if rc24_mod.is_room_complete(_room_idx, _beaten):
                    await query.answer("Эта комната уже зачищена. ✅", show_alert=True)
                    return
                _next = rc24_mod.next_slot_in_room(_room_idx, _beaten)
                if _next is None:
                    await query.answer("Нет доступных целей.", show_alert=True)
                    return
                _actual_slot = _next

            if _actual_slot == rc24_mod.SLOT_BOSS and not rc24_mod.is_boss_unlocked(_beaten):
                rooms_left = rc24_mod.TOTAL_ROOMS - rc24_mod.rooms_cleared_count(_beaten)
                await query.answer(
                    f"Сначала зачисти все комнаты. Осталось: {rooms_left}.",
                    show_alert=True,
                )
                return

            if _actual_slot in rc24_mod.SLOT_ROOMS and _actual_slot in _beaten:
                await query.answer("Этот монстр уже побеждён.", show_alert=True)
                return

            spawn = rc24_mod.spawn_by_slot(_actual_slot)
            if spawn is None:
                await query.answer("Цель не найдена.", show_alert=True)
                return
            _r24_mi = rc24_mod.slot_room_and_monster_index(_actual_slot)
            _r24_free_stam = (_r24_mi is not None and _r24_mi[1] > 0)
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
                free_stamina=_r24_free_stam,
            )
            return

        # ── Этаж 27: волны теней ─────────────────────────────────────────────
        if code in wv27_mod.WAVE_FLOOR_27_ALL_SLOTS or code == "wv27:locked":
            if code == "wv27:locked":
                await query.answer("Сначала победи предыдущую волну теней.", show_alert=True)
                return
            if not wv27_mod.is_wave_floor_27(floor):
                await query.answer("Этот сценарий только на 27-м этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            from db.repository import floor_progress_repo as fpr
            _row = await fpr.ensure_floor_row(session, char.id, floor)
            _ex = dict(_row.extra or {})
            _beaten = frozenset(str(x) for x in (_ex.get("slots_cleared") or []))
            spawn = wv27_mod.spawn_by_slot(code)
            if spawn is None:
                await query.answer("Цель не найдена.", show_alert=True)
                return
            current_slot = wv27_mod.current_available_slot(_beaten)
            if code != current_slot:
                if code in _beaten:
                    await query.answer("Эта волна уже отбита.", show_alert=True)
                else:
                    await query.answer("Сначала победи предыдущую волну.", show_alert=True)
                return
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
            )
            return

        # ── Этаж 5: зачистка комнат ─────────────────────────────────────────
        if code in rc_mod.ROOM_CLEAR_ALL_SLOTS:
            if not rc_mod.is_room_clear_floor(floor):
                await query.answer("Этот сценарий только на 5-м этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            # Получаем cleared_slots из floor_progress
            from db.repository import floor_progress_repo as fpr
            _row = await fpr.ensure_floor_row(session, char.id, floor)
            _ex = dict(_row.extra or {})
            _beaten = frozenset(str(x) for x in (_ex.get("slots_cleared") or []))

            # Кнопка комнаты (rc_r0..rc_r4) → определяем следующего монстра
            _actual_slot = code
            _room_idx = rc_mod.room_index_for_button(code)
            if _room_idx is not None:
                if rc_mod.is_room_complete(_room_idx, _beaten):
                    await query.answer("Эта комната уже зачищена. ✅", show_alert=True)
                    return
                _next = rc_mod.next_slot_in_room(_room_idx, _beaten)
                if _next is None:
                    await query.answer("Нет доступных целей.", show_alert=True)
                    return
                _actual_slot = _next

            # Босс только после зачистки всех комнат
            if _actual_slot == rc_mod.SLOT_BOSS and not rc_mod.is_boss_unlocked(_beaten):
                rooms_left = rc_mod.TOTAL_ROOMS - rc_mod.rooms_cleared_count(_beaten)
                await query.answer(
                    f"Сначала зачисти все комнаты. Осталось: {rooms_left}.",
                    show_alert=True,
                )
                return

            # Уже побеждённый монстр (прямой слот из FSM)
            if _actual_slot in rc_mod.SLOT_ROOMS and _actual_slot in _beaten:
                await query.answer("Этот монстр уже побеждён.", show_alert=True)
                return

            spawn = rc_mod.spawn_by_slot(_actual_slot)
            if spawn is None:
                await query.answer("Цель не найдена.", show_alert=True)
                return
            # Монстры 2+ в одной комнате — стамина уже потрачена на вход
            _rc_mi = rc_mod.slot_room_and_monster_index(_actual_slot)
            _rc_free_stam = (_rc_mi is not None and _rc_mi[1] > 0)
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
                free_stamina=_rc_free_stam,
            )
            return

        # ── Этаж 10: тёмные катакомбы (зачистка комнат) ─────────────────────
        if code in rc10_mod.ROOM_CLEAR_10_ALL_SLOTS:
            if not rc10_mod.is_room_clear_floor_10(floor):
                await query.answer("Этот сценарий только на 10-м этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            from db.repository import floor_progress_repo as fpr
            _row = await fpr.ensure_floor_row(session, char.id, floor)
            _ex = dict(_row.extra or {})
            _beaten = frozenset(str(x) for x in (_ex.get("slots_cleared") or []))

            # Кнопка комнаты (r10_r0..r10_r4) → определяем следующего монстра
            _actual_slot = code
            _room_idx = rc10_mod.room_index_for_button(code)
            if _room_idx is not None:
                if rc10_mod.is_room_complete(_room_idx, _beaten):
                    await query.answer("Эта комната уже зачищена. ✅", show_alert=True)
                    return
                _next = rc10_mod.next_slot_in_room(_room_idx, _beaten)
                if _next is None:
                    await query.answer("Нет доступных целей.", show_alert=True)
                    return
                _actual_slot = _next

            # Босс только после зачистки всех комнат
            if _actual_slot == rc10_mod.SLOT_BOSS and not rc10_mod.is_boss_unlocked(_beaten):
                rooms_left = rc10_mod.TOTAL_ROOMS - rc10_mod.rooms_cleared_count(_beaten)
                await query.answer(
                    f"Сначала зачисти все комнаты. Осталось: {rooms_left}.",
                    show_alert=True,
                )
                return

            # Уже побеждённый монстр (прямой слот из FSM)
            if _actual_slot in rc10_mod.SLOT_ROOMS and _actual_slot in _beaten:
                await query.answer("Этот монстр уже побеждён.", show_alert=True)
                return

            spawn = rc10_mod.spawn_by_slot(_actual_slot)
            if spawn is None:
                await query.answer("Цель не найдена.", show_alert=True)
                return
            # Монстры 2+ в одной комнате — стамина уже потрачена на вход
            _r10_mi = rc10_mod.slot_room_and_monster_index(_actual_slot)
            _r10_free_stam = (_r10_mi is not None and _r10_mi[1] > 0)
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
                free_stamina=_r10_free_stam,
            )
            return

        # ── Этаж 10: волны вторжения (легаси) ────────────────────────────────
        if code in wv_mod.WAVE_FLOOR_ALL_SLOTS or code == "wv:locked":
            if code == "wv:locked":
                await query.answer("Сначала победи предыдущую волну.", show_alert=True)
                return
            if not wv_mod.is_wave_floor(floor):
                await query.answer("Этот сценарий только на 10-м этаже.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            from db.repository import floor_progress_repo as fpr
            _row = await fpr.ensure_floor_row(session, char.id, floor)
            _ex = dict(_row.extra or {})
            _beaten = frozenset(str(x) for x in (_ex.get("slots_cleared") or []))
            spawn = wv_mod.spawn_by_slot(code)
            if spawn is None:
                await query.answer("Цель не найдена.", show_alert=True)
                return
            # Проверяем последовательность волн
            current_slot = wv_mod.current_available_slot(_beaten)
            if code != current_slot:
                if code in _beaten:
                    await query.answer("Эта волна уже отбита.", show_alert=True)
                else:
                    await query.answer("Сначала победи предыдущую волну.", show_alert=True)
                return
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
            )
            return

        if code in ("lf_keys", "lf_npc", "lf_w1", "lf_w2", "lf_boss"):
            if floor != long_floor_mod.PILOT_FLOOR or not long_floor_mod.is_long_floor_active(char):
                await query.answer("Сценарий «длинного этажа» здесь недоступен.", show_alert=True)
                return
            if query.message is None:
                await query.answer()
                return
            if code == "lf_keys":
                if long_floor_mod.current_phase(char) != "keys":
                    await query.answer("Эта фаза уже пройдена.", show_alert=True)
                    return
                long_floor_mod.advance_from_keys(char)
                await session.flush()
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                    target_message=query.message,
                )
                await query.answer("Ключи найдены.")
                return
            if code == "lf_npc":
                if long_floor_mod.current_phase(char) != "npc":
                    await query.answer("Сначала пройди волны.", show_alert=True)
                    return
                long_floor_mod.advance_from_npc(char)
                await session.flush()
                await push_floor_screen_ui(
                    session,
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    character=char,
                    reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                    target_message=query.message,
                )
                await query.answer()
                return
            wave_map = {
                "lf_w1": ("wave1", long_floor_mod.SPAWN_W1),
                "lf_w2": ("wave2", long_floor_mod.SPAWN_W2),
                "lf_boss": ("boss", long_floor_mod.SPAWN_BOSS),
            }
            phase_need, spawn = wave_map[code]
            if long_floor_mod.current_phase(char) != phase_need:
                await query.answer("Сначала выполни предыдущий шаг сценария.", show_alert=True)
                return
            await combat_service.start_combat(
                query=query,
                session=session,
                state=state,
                character=char,
                spawn=spawn,
            )
            return

        # ── Этажи 4, 8 и 22: исследование ───────────────────────────────────
        _is_e4 = code in ("e4_explore", exp4_mod.SLOT_BOSS)
        _is_e8 = code in ("exp_explore", exp_mod.SLOT_BOSS)
        _is_e22 = code in ("e22_explore", exp22_mod.SLOT_BOSS)
        if _is_e4 or _is_e8 or _is_e22:
            # Выбираем модуль в зависимости от этажа
            if _is_e4:
                if not exp4_mod.is_explore_floor_4(floor):
                    await query.answer("Это действие доступно только на 4-м этаже.", show_alert=True)
                    return
                _emod = exp4_mod
                _explore_btn = "e4_explore"
                _boss_name_hint = "🌳 <b>Хранитель Рощи пробудился!</b> Кнопка появилась ниже."
            elif _is_e22:
                if not exp22_mod.is_explore_floor_22(floor):
                    await query.answer("Это действие доступно только на 22-м этаже.", show_alert=True)
                    return
                _emod = exp22_mod
                _explore_btn = "e22_explore"
                _boss_name_hint = "🕸️ <b>Ткач Теней пробудился!</b> Кнопка появилась ниже."
            else:
                if not exp_mod.is_explore_floor(floor):
                    await query.answer("Это действие доступно только на 8-м этаже.", show_alert=True)
                    return
                _emod = exp_mod
                _explore_btn = "exp_explore"
                _boss_name_hint = "🗿 <b>Хранитель пробудился!</b> Кнопка появилась ниже."

            if query.message is None:
                await query.answer()
                return
            from db.repository import floor_progress_repo as fpr
            _row = await fpr.ensure_floor_row(session, char.id, floor)
            _ex = dict(_row.extra or {})
            _ex = _emod.ensure_explore_started(_ex)

            # Кнопка босса
            if code == _emod.SLOT_BOSS:
                if not _emod.is_boss_available(_ex):
                    pct = _emod.progress_percent(
                        _emod.get_explore_count(_ex), _emod.get_explore_target(_ex)
                    )
                    await query.answer(
                        f"Сначала исследуй до 100% (сейчас {pct}%).", show_alert=True
                    )
                    return
                _beaten = frozenset(str(x) for x in (_ex.get("slots_cleared") or []))
                if _emod.SLOT_BOSS in _beaten:
                    await query.answer("Босс уже побеждён. ✅", show_alert=True)
                    return
                await combat_service.start_combat(
                    query=query,
                    session=session,
                    state=state,
                    character=char,
                    spawn=_emod.SPAWN_BOSS,
                )
                return

            # Кнопка «Исследовать» — бросаем событие
            event_type = _emod.roll_explore_event()

            if event_type == "monster":
                _spawn = _emod.make_encounter_spawn()
                await combat_service.start_combat(
                    query=query,
                    session=session,
                    state=state,
                    character=char,
                    spawn=_spawn,
                )
                return

            # Не-боевые события: инкрементируем счётчик вручную
            _ex = _emod.increment_explore_count(_ex)
            _row.extra = _ex
            await session.flush()
            await session.refresh(char)

            count_now = _emod.get_explore_count(_ex)
            target_now = _emod.get_explore_target(_ex)
            pct_now = _emod.progress_percent(count_now, target_now)
            boss_hint = f"\n{_boss_name_hint}" if _emod.is_boss_available(_ex) else ""

            from services import character_service as cs
            import html as _html

            if event_type == "gold":
                gold_amount = 20 + floor * 3 + random.randint(0, 20)
                cs.add_gold(char, gold_amount)
                await session.flush()
                event_html = (
                    f"💰 <b>Тайник с золотом!</b>\n"
                    f"Ты нашёл кожаный кошель за камнем — +{gold_amount} монет."
                )
            elif event_type == "merchant":
                _mp = dict(char.meta_progress or {})
                _mp["merchant_discount_charges"] = int(_mp.get("merchant_discount_charges") or 0) + 2
                char.meta_progress = _mp
                await session.flush()
                event_html = (
                    "🏪 <b>Бродячий торговец!</b>\n"
                    "В дальнем закутке расположился лавочник. Он даёт тебе скидку "
                    "на следующие <b>2 покупки</b> в лавке (−30%)."
                )
            elif event_type == "mystical":
                _myst_roll = random.randint(0, 2)
                if _myst_roll == 0:
                    # Упавшая звезда — XP бафф
                    _mp2 = dict(char.meta_progress or {})
                    _mp2["next_battle_xp_mult"] = max(float(_mp2.get("next_battle_xp_mult") or 1.0), 1.5)
                    char.meta_progress = _mp2
                    event_html = "⭐ <b>Упавшая звезда!</b>\nСледующий бой даст <b>+50%</b> опыта."
                elif _myst_roll == 1:
                    # Родник сил — восстановление HP/MP
                    char.hp_current = int(char.hp_max)
                    char.mp_current = int(char.mp_max)
                    event_html = "✨ <b>Родник сил!</b>\nHP и MP полностью восстановлены."
                else:
                    # Благословение странника — немного золота
                    _gold_myst = 8 + floor
                    cs.add_gold(char, _gold_myst)
                    event_html = f"🌟 <b>Благословение странника!</b>\nНайдено немного золота (+{_gold_myst}) среди костей путника."
                await session.flush()
            elif event_type == "crystal":
                # Светящийся кристалл — восстанавливает MP (уникально для этажа 22)
                _mp_gain = max(1, int(char.mp_max * random.uniform(0.40, 0.70)))
                char.mp_current = min(int(char.mp_max), int(char.mp_current) + _mp_gain)
                await session.flush()
                event_html = (
                    f"💎 <b>Светящийся кристалл!</b>\n"
                    f"Из стены пещеры торчит мерцающий кристалл. Прикоснувшись к нему, "
                    f"ты чувствуешь прилив магической энергии — "
                    f"<b>+{_mp_gain} MP</b> восстановлено."
                )
            elif event_type == "trap":
                # Ловушка — небольшой урон, утешительное золото
                _trap_dmg = max(1, int(char.hp_max * random.uniform(0.07, 0.13)))
                char.hp_current = max(1, int(char.hp_current) - _trap_dmg)
                _trap_gold = random.randint(5, 12) + floor
                cs.add_gold(char, _trap_gold)
                await session.flush()
                event_html = (
                    f"🪤 <b>Ловушка!</b>\n"
                    f"Ты задел натянутую струну — острые шипы царапают кожу. "
                    f"−{_trap_dmg} HP. Зато среди обломков нашёл +{_trap_gold} монет."
                )
            elif event_type == "ancient_inscription":
                # Древняя надпись — рандомный малый бонус
                _insc_roll = random.randint(0, 2)
                if _insc_roll == 0:
                    # +1 рунный камень
                    char.rune_stones = int(char.rune_stones or 0) + 1
                    event_html = (
                        "📜 <b>Древняя надпись!</b>\n"
                        "Руны на стене пульсируют и втягиваются в твою ладонь — "
                        "<b>+1 рунный камень</b>."
                    )
                elif _insc_roll == 1:
                    # +50% MP (не больше max)
                    _mp_gain = max(1, int(char.mp_max * 0.5))
                    char.mp_current = min(int(char.mp_max), int(char.mp_current) + _mp_gain)
                    event_html = (
                        f"📜 <b>Древняя надпись!</b>\n"
                        f"Манускрипт светится мистическим светом — "
                        f"<b>+{_mp_gain} MP</b> восстановлено."
                    )
                else:
                    # +25% HP (не больше max)
                    _hp_gain = max(1, int(char.hp_max * 0.25))
                    char.hp_current = min(int(char.hp_max), int(char.hp_current) + _hp_gain)
                    event_html = (
                        f"📜 <b>Древняя надпись!</b>\n"
                        f"Лечебное заклинание проходит сквозь камень и касается твоей кожи — "
                        f"<b>+{_hp_gain} HP</b> восстановлено."
                    )
                await session.flush()
            else:  # rare_item
                from game.items import loot as loot_tables
                from db.repository import inventory_repo
                from game.floors.monsters import FloorMonsterSpawn as _FMS
                import copy
                # Используем минибосс-спаун для хорошего дропа
                _mini_spawn = _FMS(
                    slot_code="exp_mini",
                    template=exp_mod.SPAWN_BOSS.template,
                    is_elite=False,
                    is_mini_boss=True,
                    is_major_boss=False,
                )
                _loot = loot_tables.roll_victory_item_payload(floor, _mini_spawn)
                _free = await inventory_repo.first_free_bag_slot(session, char.id)
                if _free is not None:
                    await inventory_repo.add_bag_item(
                        session, char.id, copy.deepcopy(_loot), bag_slot=_free
                    )
                    _iname = _html.escape(str(_loot.get("name", "Предмет")))
                    event_html = (
                        f"🌟 <b>Редкая находка!</b>\n"
                        f"Среди руин мерцает нечто ценное — "
                        f"<b>{_iname}</b> добавлен в сумку (ячейка {_free})."
                    )
                else:
                    cs.add_gold(char, 15 + floor * 2)
                    await session.flush()
                    event_html = (
                        "🌟 <b>Редкая находка!</b>\n"
                        "Сумка полна — вещь оказалась слишком громоздкой. "
                        f"Вместо неё +{15 + floor * 2} монет."
                    )

            # Показываем результат события с кнопкой «Продолжить»
            from bot.keyboards.floor_kb import (
                explore_event_keyboard,
                explore_floor_4_event_keyboard,
                explore_floor_22_event_keyboard,
            )
            if _is_e4:
                _kb = explore_floor_4_event_keyboard(floor, extra=_ex)
            elif _is_e22:
                _kb = explore_floor_22_event_keyboard(floor, extra=_ex)
            else:
                _kb = explore_event_keyboard(floor, extra=_ex)
            _progress_line = f"\n\n📍 Исследование: {count_now}/{target_now} ({pct_now}%){boss_hint}"
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=event_html + _progress_line,
                reply_markup=_kb,
                target_message=query.message,
            )
            await query.answer()
            return

        if code == "srch":
            if query.message is None:
                await query.answer()
                return
            outcome = await try_secret_search(session, char)
            if outcome.alert:
                await query.answer(outcome.alert, show_alert=True)
                return
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=outcome.body_html or "",
                reply_markup=secret_result_keyboard(char.floor_number),
                target_message=query.message,
            )
            await query.answer()
            return

        spawns = await get_spawns_for_character_session(session, char)
        chosen = next((s for s in spawns if s.slot_code == code), None)
        if chosen is None:
            await query.answer("Цель не найдена.", show_alert=True)
            return

        if query.message is None:
            await query.answer()
            return

        if (
            not long_floor_mod.is_long_floor_active(char)
            and fb.is_forest_beginnings_zone(int(char.floor_number))
            and fb.eligible_for_forest_tricks(chosen)
            and str(chosen.slot_code) != golden_goblin_service.SLOT_CODE
        ):
            kind = fb.roll_prefight_kind(char)
            if kind == "mushroom":
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=fb.mushroom_intro_html(),
                    reply_markup=forest_mushroom_keyboard(floor, code),
                    target_message=query.message,
                )
                await query.answer()
                return
            if kind == "spirit":
                correct = random.randint(0, 2)
                await state.update_data(
                    svc_forest_spirit={"correct": correct, "slot": chosen.slot_code, "floor": floor},
                )
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=query.message.chat.id,
                    text=fb.spirit_intro_html(),
                    reply_markup=forest_spirit_keyboard(floor, code),
                    target_message=query.message,
                )
                await query.answer()
                return

        await combat_service.start_combat(
            query=query,
            session=session,
            state=state,
            character=char,
            spawn=chosen,
        )
    except Exception:
        logger.exception("Ошибка в callback этажа")


# ── Обработчики заданий путников (wnpc:*) ─────────────────────────────────────

@router.callback_query(F.data.regexp(r"^wnpc:take:\d+$"))
async def wnpc_take_quest(query: CallbackQuery, session: AsyncSession) -> None:
    """Взять задание от путника."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor = int(query.data.split(":")[2])
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return

        from services import wandering_npc_quest_service as wnpc_qs
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        ok = wnpc_qs.take_quest(char, floor)
        if not ok:
            await query.answer("Задание уже взято или недоступно.", show_alert=True)
            return

        await session.flush()
        text = wnpc_qs.format_npc_quest_screen(char, floor)
        rows = [[InlineKeyboardButton(text="⬅ Назад на этаж", callback_data=f"fl:{floor}:back")]]
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        await query.answer("✅ Задание принято!")
    except Exception:
        logger.exception("wnpc:take")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^wnpc:claim:\d+$"))
async def wnpc_claim_quest(query: CallbackQuery, session: AsyncSession) -> None:
    """Получить награду за выполненное задание путника."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        floor = int(query.data.split(":")[2])
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return

        from services import wandering_npc_quest_service as wnpc_qs
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        ok, msg = await wnpc_qs.claim_quest_reward(session, char, floor)
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return

        await session.commit()
        rows = [[InlineKeyboardButton(text="⬅ Назад на этаж", callback_data=f"fl:{floor}:back")]]
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        await query.message.edit_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML)
        await query.answer("🎁 Награда получена!")
    except Exception:
        logger.exception("wnpc:claim")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("sq:npc:"))
async def story_npc_screen(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Показать диалог сюжетного NPC."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        npc_key = query.data.removeprefix("sq:npc:").strip()
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from game.quests.story_quests import (
            STORY_QUESTS_BY_NPC,
            get_quest_state,
            check_quest_completion,
        )

        sq = STORY_QUESTS_BY_NPC.get(npc_key)
        if sq is None:
            await query.answer("NPC не найден.", show_alert=True)
            return

        st = get_quest_state(char, sq.quest_id)
        rows: list[list[InlineKeyboardButton]] = []

        if st == "pending":
            text = sq.npc_intro
            rows.append([InlineKeyboardButton(
                text=f"📜 Принять задание: {sq.quest_title}",
                callback_data=f"sq:accept:{sq.quest_id}",
            )])
        elif st == "active":
            if check_quest_completion(char, sq):
                text = (
                    f"{sq.npc_in_progress}\n\n"
                    f"✅ <b>Задание выполнено!</b> Можно сдавать."
                )
                rows.append([InlineKeyboardButton(
                    text="🎁 Сдать задание",
                    callback_data=f"sq:claim:{sq.quest_id}",
                )])
            else:
                if sq.condition_type == "floor_reached":
                    current = int(getattr(char, sq.condition_key, 0) or 0)
                else:
                    mp = dict(char.meta_progress or {})
                    current = int(mp.get(sq.condition_key, 0) or 0)
                text = (
                    f"{sq.npc_in_progress}\n\n"
                    f"📊 Прогресс: <b>{current}/{sq.condition_target}</b>"
                )
        else:
            text = sq.npc_completed

        rows.append([InlineKeyboardButton(text="⬅ К списку NPC", callback_data="fl:1:story_npc")])
        rows.append([InlineKeyboardButton(text="⬅ На этаж", callback_data="fl:1:back")])
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await query.answer()
    except Exception:
        logger.exception("sq:npc")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("sq:accept:"))
async def story_quest_accept(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Принять сюжетный квест."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        quest_id = query.data.removeprefix("sq:accept:").strip()
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from game.quests.story_quests import STORY_QUESTS_BY_ID, accept_quest

        sq = STORY_QUESTS_BY_ID.get(quest_id)
        if sq is None:
            await query.answer("Квест не найден.", show_alert=True)
            return

        ok = accept_quest(char, quest_id)
        if not ok:
            await query.answer("Квест уже взят или выполнен.", show_alert=True)
            return
        await session.flush()

        rows = [
            [InlineKeyboardButton(text="⬅ К NPC", callback_data=f"sq:npc:{sq.npc_key}")],
            [InlineKeyboardButton(text="⬅ На этаж", callback_data="fl:1:back")],
        ]
        await query.message.edit_text(
            f"✅ <b>Задание принято!</b>\n\n<b>{sq.quest_title}</b>\n{sq.quest_desc}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await query.answer("Задание принято!")
    except Exception:
        logger.exception("sq:accept")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("sq:claim:"))
async def story_quest_claim(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Сдать сюжетный квест и получить награду."""
    try:
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        quest_id = query.data.removeprefix("sq:claim:").strip()
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from game.quests.story_quests import STORY_QUESTS_BY_ID, claim_quest_reward

        sq = STORY_QUESTS_BY_ID.get(quest_id)
        if sq is None:
            await query.answer("Квест не найден.", show_alert=True)
            return

        ok, result_text = claim_quest_reward(char, sq)
        if not ok:
            await query.answer(result_text[:180], show_alert=True)
            return
        await session.flush()

        rows = [
            [InlineKeyboardButton(text="⬅ К списку NPC", callback_data="fl:1:story_npc")],
            [InlineKeyboardButton(text="⬅ На этаж", callback_data="fl:1:back")],
        ]
        await query.message.edit_text(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await query.answer("🎁 Награда получена!")
    except Exception:
        logger.exception("sq:claim")
        await query.answer("Ошибка.", show_alert=True)
