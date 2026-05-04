"""
Кланы: /clan и mnu:clan — команды и inline-кнопки cln:*.
"""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.clan_kb import (
    clan_browse_keyboard,
    clan_building_detail_keyboard,
    clan_buildings_keyboard,
    clan_capture_keyboard,
    clan_hub_keyboard,
    clan_info_keyboard,
    clan_member_actions_keyboard,
    clan_members_keyboard,
    clan_no_clan_keyboard,
    clan_no_hub_keyboard,
    clan_panel_keyboard,
    clan_panel_members_keyboard,
    clan_relics_keyboard,
    clan_salary_amount_keyboard,
    clan_salary_menu_keyboard,
    clan_settings_keyboard,
    clan_treasury_keyboard,
    clan_war_keyboard,
    confirm_leave_keyboard,
    confirm_levelup_keyboard,
)
from bot.states.clan_states import (
    ClanCreateStates,
    ClanDonateStates,
    ClanSalaryStates,
    ClanSettingsStates,
    ClanWarDeclareStates,
)
from bot.utils.game_art import menu_clan_photo_path
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, clan_repo, user_repo
from services import clan_service
from services.clan_service import (
    BUILDING_DEFS,
    RELIC_DEFS,
    _has_building,
    _payload,
    _war,
    check_and_complete_buildings,
    format_buildings_html,
    format_clan_browse_html,
    format_clan_card_html,
    format_clan_settings_html,
    format_members_list_html,
    format_relics_html,
    format_war_html,
    level_def,
    max_members_for_level,
    role_label,
    _mat,
    _treasury_gold,
    _treasury_limit,
    _relics,
)

router = Router(name="clans")


# ─────────────────────────── Helpers ────────────────────────────────────────

async def _get_char(session: AsyncSession, query: CallbackQuery):
    if query.from_user is None:
        await query.answer()
        return None, None
    user = await user_repo.get_by_telegram_id(session, query.from_user.id)
    if user is None or user.is_banned:
        await query.answer("Нет доступа.", show_alert=True)
        return None, None
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await query.answer("Создай героя через /start.", show_alert=True)
        return None, None
    return user, char


async def _edit(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    text: str,
    kb,
) -> None:
    if callback.message is None or callback.bot is None:
        return
    _, char = await _get_char(session, callback)
    await push_game_ui(
        state,
        callback.bot,
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=kb,
        target_message=callback.message,
        photo_path=menu_clan_photo_path(),
        character=char,
    )


async def _clan_hub_screen(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    _, char = await _get_char(session, callback)
    if char is None:
        return
    m = await clan_repo.get_membership(session, int(char.id))
    if m is None:
        await _edit(
            callback, state, session,
            "⚔️ <b>Кланы</b>\n\nТы не состоишь в клане.\n"
            "<i>Создай клан или найди существующий в списке.</i>",
            clan_no_hub_keyboard(),
        )
        await callback.answer()
        return
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        await _edit(
            callback, state, session,
            "⚔️ <b>Кланы</b>\n\nТы не состоишь в клане.",
            clan_no_hub_keyboard(),
        )
        await callback.answer()
        return
    payload = _payload(clan)
    war = _war(payload)
    war_status = war.get("status") if war else None
    tag_str = f" [{html.escape(clan.tag)}]" if clan.tag else ""
    n = await clan_repo.count_members(session, int(clan.id))
    max_m = max_members_for_level(int(clan.clan_level))
    if _has_building(payload, "barracks"):
        max_m += 5
    text = (
        f"⚔️ <b>{html.escape(clan.name)}</b>{tag_str}\n"
        f"Уровень: <b>{clan.clan_level}/10</b> · Участников: <b>{n}/{max_m}</b>\n"
        f"<i>Твоя роль: {role_label(m.role)}</i>"
    )
    await _edit(callback, state, session, text, clan_hub_keyboard(m.role, war_status))
    await callback.answer()


# ─────────────────────────── /clan команда ──────────────────────────────────

@router.message(Command("clan", "клан"))
async def cmd_clan(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Сначала /start.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Создай героя через /start.")
            return
        raw = (message.text or "").strip()
        parts = raw.split()
        tok = parts[1:] if len(parts) > 1 else []

        if not tok:
            body = await format_clan_card_html(session, char)
            membership = await clan_repo.get_membership(session, int(char.id))
            if membership is None:
                await message.answer(body, parse_mode=ParseMode.HTML, reply_markup=clan_no_hub_keyboard())
            else:
                await message.answer(body, parse_mode=ParseMode.HTML, reply_markup=clan_hub_keyboard(membership.role))
            return

        sub = tok[0].lower()
        if sub in ("create", "создать") and len(tok) >= 2:
            name = " ".join(tok[1:]).strip()
            ok, msg = await clan_service.try_create_clan(session, char, name)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        if sub in ("join", "вступить") and len(tok) >= 2:
            try:
                cid = int(tok[1])
            except ValueError:
                await message.answer("Укажи числовой ID клана: <code>/clan join 5</code>", parse_mode=ParseMode.HTML)
                return
            ok, msg = await clan_service.try_join_clan(session, char, cid)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        if sub in ("chat", "чат") and len(tok) >= 2:
            url = " ".join(tok[1:]).strip()
            ok, msg = await clan_service.try_set_clan_chat(session, char, url)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        if sub in ("leave", "выйти"):
            ok, msg = await clan_service.try_leave_clan(session, char)
            await message.answer(msg, parse_mode=ParseMode.HTML)
            return

        body = await format_clan_card_html(session, char)
        await message.answer(body, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("cmd_clan")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)


# ─────────────────────────── mnu:clan → хаб ────────────────────────────────

@router.callback_query(F.data == "mnu:clan")
async def cb_mnu_clan(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clan_hub_screen(callback, state, session)
    except Exception:
        logger.exception("mnu:clan")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:hub ────────────────────────────────────────

@router.callback_query(F.data == "cln:hub")
async def cb_clan_hub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _clan_hub_screen(callback, state, session)
    except Exception:
        logger.exception("cln:hub")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:info ───────────────────────────────────────

@router.callback_query(F.data == "cln:info")
async def cb_clan_info(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        text = await format_clan_card_html(session, char)
        await _edit(callback, state, session, text, clan_info_keyboard())
        await callback.answer()
    except Exception:
        logger.exception("cln:info")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:members ────────────────────────────────────

@router.callback_query(F.data == "cln:members")
async def cb_clan_members(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        rows = await clan_repo.get_members_with_characters(session, int(clan.id))
        text = format_members_list_html(rows, clan.name, m.role == "leader")
        await _edit(callback, state, session, text, clan_members_keyboard(m.role))
        await callback.answer()
    except Exception:
        logger.exception("cln:members")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:treasury ───────────────────────────────────

def _format_treasury_text(clan, char, payload: dict) -> tuple[str, int]:
    """Возвращает (text, pending_salary_for_self)."""
    check_and_complete_buildings(payload)
    tg = _treasury_gold(payload)
    tg_lim = _treasury_limit(payload)
    mats = _mat(payload)
    char_mats = clan_service.get_character_materials(char)
    lv = int(clan.clan_level)
    if lv < 10:
        nxt = level_def(lv + 1)
        cost_str = (
            f"Ур.{lv + 1}: {nxt['cost_gold']:,}💰 · {nxt['cost_wood']}🪵 · "
            f"{nxt['cost_stone']}🪨 · {nxt['cost_herbs']}🌿"
        )
    else:
        cost_str = "Максимальный уровень клана."
    pending_self = clan_service.pending_salary_for(char, payload)
    salary_line = ""
    if pending_self > 0:
        salary_line = f"\n💼 Тебе выделено ЗП: <b>{pending_self:,}</b> 💰 — нажми «Забрать ЗП».\n"
    text = (
        f"💰 <b>Казна клана</b>\n\n"
        f"Золото: <b>{tg:,}</b> / {tg_lim:,} 💰\n"
        f"Материалы казны: 🪵{mats['wood']} 🪨{mats['stone']} 🌿{mats['herbs']}\n"
        f"Твои материалы: 🪵{char_mats['wood']} 🪨{char_mats['stone']} 🌿{char_mats['herbs']}\n"
        f"{salary_line}\n"
        f"Уровень клана: <b>{lv}/10</b>\n"
        f"<i>Стоимость след. уровня:\n{cost_str}</i>"
    )
    return text, pending_self


@router.callback_query(F.data == "cln:treasury")
async def cb_clan_treasury(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        text, pending_self = _format_treasury_text(clan, char, payload)
        await _edit(
            callback,
            state,
            session,
            text,
            clan_treasury_keyboard(m.role, has_pending_salary=pending_self > 0),
        )
        await callback.answer()
    except Exception:
        logger.exception("cln:treasury")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:don:{amount} ────────────────────────────────

@router.callback_query(F.data.regexp(r"^cln:don:\d+$"))
async def cb_clan_donate(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        amount = int((callback.data or "").split(":")[-1])
        ok, msg = await clan_service.try_donate_gold(session, char, amount)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            # Обновить экран казны
            m = await clan_repo.get_membership(session, int(char.id))
            clan = await clan_repo.get_clan(session, int(m.clan_id)) if m else None
            if clan and m:
                payload = _payload(clan)
                text, pending_self = _format_treasury_text(clan, char, payload)
                await _edit(
                    callback,
                    state,
                    session,
                    text,
                    clan_treasury_keyboard(m.role, has_pending_salary=pending_self > 0),
                )
    except Exception:
        logger.exception("cln:don")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:don:custom (FSM) ────────────────────────────

@router.callback_query(F.data == "cln:don:custom")
async def cb_clan_donate_custom_start(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        await state.set_state(ClanDonateStates.waiting_amount)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "💰 Введи сумму для пожертвования в казну клана (число):",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:don:custom")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanDonateStates.waiting_amount)
async def msg_clan_donate_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw = (message.text or "").strip().replace(" ", "").replace(",", "")
        try:
            amount = int(raw)
        except ValueError:
            await message.answer("Введи целое число.", parse_mode=ParseMode.HTML)
            return
        ok, msg = await clan_service.try_donate_gold(session, char, amount)
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_clan_donate_amount")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# ─────────────────────────── cln:donate:mats ─────────────────────────────────

@router.callback_query(F.data == "cln:donate:mats")
async def cb_donate_materials(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        char_mats = clan_service.get_character_materials(char)
        if sum(char_mats.values()) == 0:
            await callback.answer(
                "У тебя нет материалов. Побеждай энтов, големов и болотных монстров!",
                show_alert=True,
            )
            return
        ok, msg = await clan_service.try_donate_materials(
            session, char,
            wood=char_mats["wood"],
            stone=char_mats["stone"],
            herbs=char_mats["herbs"],
        )
        await callback.answer(msg, show_alert=True)
    except Exception:
        logger.exception("cln:donate:mats")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:salary:* ────────────────────────────────────

@router.callback_query(F.data == "cln:salary:claim")
async def cb_salary_claim(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        ok, msg = await clan_service.claim_salary(session, char)
        await callback.answer(msg, show_alert=True)
        if ok:
            m = await clan_repo.get_membership(session, int(char.id))
            clan = await clan_repo.get_clan(session, int(m.clan_id)) if m else None
            if clan and m:
                payload = _payload(clan)
                text, pending_self = _format_treasury_text(clan, char, payload)
                await _edit(
                    callback,
                    state,
                    session,
                    text,
                    clan_treasury_keyboard(m.role, has_pending_salary=pending_self > 0),
                )
    except Exception:
        logger.exception("cln:salary:claim")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:salary:menu")
async def cb_salary_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        if not clan_service.can_manage(m.role):
            await callback.answer("Только лидер или офицер.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        tg = _treasury_gold(payload)
        members = await clan_repo.get_members_with_characters(session, int(clan.id))
        pending = {int(k): int(v or 0) for k, v in (payload.get("salary_pool") or {}).items()
                   if str(k).lstrip("-").isdigit()}
        # Сортируем: лидер → офицеры → ветераны → рядовые, исключаем самого actor.
        order = {"leader": 0, "officer": 1, "veteran": 2, "member": 3}
        rows: list[tuple[int, str, str, int]] = []
        for mbr, ch in members:
            if int(ch.id) == int(char.id):
                continue
            rows.append((
                int(ch.id),
                str(ch.display_name or "?"),
                str(mbr.role),
                pending.get(int(ch.id), 0),
            ))
        rows.sort(key=lambda r: (order.get(r[2], 99), -r[3], r[1].lower()))
        if not rows:
            await callback.answer("В клане нет других участников.", show_alert=True)
            return
        text = (
            f"💼 <b>Распределение ЗП</b>\n\n"
            f"В казне: <b>{tg:,}</b> 💰\n"
            f"Выберите участника, чтобы выделить ему ЗП.\n"
            f"<i>Сумма списывается из казны сразу; участник заберёт её сам кнопкой «Забрать ЗП».</i>"
        )
        await _edit(callback, state, session, text, clan_salary_menu_keyboard(rows))
        await callback.answer()
    except Exception:
        logger.exception("cln:salary:menu")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:salary:pick:\d+$"))
async def cb_salary_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or not clan_service.can_manage(m.role):
            await callback.answer("Нет прав.", show_alert=True)
            return
        target_id = int((callback.data or "").split(":")[-1])
        m_target = await clan_repo.get_membership(session, target_id)
        if m_target is None or int(m_target.clan_id) != int(m.clan_id):
            await callback.answer("Игрок не в твоём клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        target_char = await character_repo.get_by_id(session, target_id)
        if clan is None or target_char is None:
            await callback.answer("Не найдено.", show_alert=True)
            return
        payload = _payload(clan)
        tg = _treasury_gold(payload)
        pending = clan_service.pending_salary_for(target_char, payload)
        text = (
            f"💼 <b>ЗП: {html.escape(str(target_char.display_name))}</b>\n"
            f"Роль: {clan_service.role_label(m_target.role)}\n\n"
            f"В казне: <b>{tg:,}</b> 💰\n"
            f"Уже ждёт: <b>{pending:,}</b> 💰\n\n"
            f"Выберите сумму."
        )
        await _edit(callback, state, session, text, clan_salary_amount_keyboard(target_id))
        await callback.answer()
    except Exception:
        logger.exception("cln:salary:pick")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:salary:add:\d+:\d+$"))
async def cb_salary_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        parts = (callback.data or "").split(":")
        target_id = int(parts[-2])
        amount = int(parts[-1])
        ok, msg = await clan_service.allocate_salary(session, char, target_id, amount)
        await callback.answer(msg, show_alert=True)
        if ok:
            m = await clan_repo.get_membership(session, int(char.id))
            clan = await clan_repo.get_clan(session, int(m.clan_id)) if m else None
            target_char = await character_repo.get_by_id(session, target_id)
            if clan and target_char:
                payload = _payload(clan)
                tg = _treasury_gold(payload)
                pending = clan_service.pending_salary_for(target_char, payload)
                m_target = await clan_repo.get_membership(session, target_id)
                role_label_str = (
                    clan_service.role_label(m_target.role) if m_target else "—"
                )
                text = (
                    f"💼 <b>ЗП: {html.escape(str(target_char.display_name))}</b>\n"
                    f"Роль: {role_label_str}\n\n"
                    f"В казне: <b>{tg:,}</b> 💰\n"
                    f"Уже ждёт: <b>{pending:,}</b> 💰"
                )
                await _edit(callback, state, session, text, clan_salary_amount_keyboard(target_id))
    except Exception:
        logger.exception("cln:salary:add")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:salary:custom:\d+$"))
async def cb_salary_custom_start(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or not clan_service.can_manage(m.role):
            await callback.answer("Нет прав.", show_alert=True)
            return
        target_id = int((callback.data or "").split(":")[-1])
        await state.set_state(ClanSalaryStates.waiting_amount)
        await state.update_data(salary_target_id=target_id)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "💼 Введи сумму ЗП для участника (целое число):",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:salary:custom")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanSalaryStates.waiting_amount)
async def msg_salary_custom_amount(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        data = await state.get_data()
        target_id = int(data.get("salary_target_id") or 0)
        if target_id <= 0:
            await state.clear()
            return
        raw = (message.text or "").strip().replace(" ", "").replace(",", "")
        try:
            amount = int(raw)
        except ValueError:
            await message.answer("Введи целое число.", parse_mode=ParseMode.HTML)
            return
        ok, msg = await clan_service.allocate_salary(session, char, target_id, amount)
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_salary_custom_amount")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# ─────────────────────────── cln:lvlup ──────────────────────────────────────

@router.callback_query(F.data == "cln:lvlup")
async def cb_clan_levelup_confirm(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только лидер может повышать уровень.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        lv = int(clan.clan_level)
        if lv >= 10:
            await callback.answer("Клан уже максимального уровня!", show_alert=True)
            return
        nxt = lv + 1
        req = level_def(nxt)
        payload = _payload(clan)
        from services.clan_service import _mat as _m, _treasury_gold as _tg
        mats = _m(payload)
        tg = _tg(payload)
        text = (
            f"⬆️ <b>Повысить клан до уровня {nxt}?</b>\n\n"
            f"Стоимость:\n"
            f"💰 {req['cost_gold']:,} (в казне: {tg:,})\n"
            f"🪵 {req['cost_wood']} (в казне: {mats['wood']})\n"
            f"🪨 {req['cost_stone']} (в казне: {mats['stone']})\n"
            f"🌿 {req['cost_herbs']} (в казне: {mats['herbs']})\n\n"
            f"Новый лимит участников: <b>{req['max_members']}</b>"
        )
        await _edit(callback, state, session, text, confirm_levelup_keyboard(nxt))
        await callback.answer()
    except Exception:
        logger.exception("cln:lvlup")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:lvlup:yes")
async def cb_clan_levelup_do(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        ok, msg = await clan_service.try_level_up_clan(session, char)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            await _clan_hub_screen(callback, state, session)
    except Exception:
        logger.exception("cln:lvlup:yes")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:blds ───────────────────────────────────────

@router.callback_query(F.data == "cln:blds")
async def cb_clan_buildings(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        check_and_complete_buildings(payload)
        await clan_repo.update_payload(session, clan, payload)
        text = format_buildings_html(payload, int(clan.clan_level))
        await _edit(callback, state, session, text, clan_buildings_keyboard(payload, int(clan.clan_level), m.role))
        await callback.answer()
    except Exception:
        logger.exception("cln:blds")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:bld:[a-z_]+$"))
async def cb_clan_building_detail(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        key = (callback.data or "").split(":")[-1]
        if key not in BUILDING_DEFS:
            await callback.answer("Неизвестная постройка.", show_alert=True)
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        check_and_complete_buildings(payload)
        bdef = BUILDING_DEFS[key]
        bstate = (payload.get("buildings") or {}).get(key) or {}
        mats = _mat(payload)
        tg = _treasury_gold(payload)
        lv = int(clan.clan_level)
        from config import is_admin as _is_admin
        _is_adm = _is_admin(callback.from_user.id if callback.from_user else None)
        can_build = (
            not bstate.get("built")
            and not bstate.get("build_until")
            and (lv >= bdef["unlock_level"] or _is_adm)
            and (_is_adm or (
                tg >= bdef["cost_gold"]
                and mats["wood"] >= bdef["cost_wood"]
                and mats["stone"] >= bdef["cost_stone"]
                and mats["herbs"] >= bdef["cost_herbs"]
            ))
        )
        locked = lv < bdef["unlock_level"]
        text = (
            f"{bdef['name']}\n\n"
            f"<i>{bdef['desc']}</i>\n\n"
            f"Требует уровень клана: <b>{bdef['unlock_level']}</b>\n"
            f"Стоимость: {bdef['cost_gold']:,}💰 · {bdef['cost_wood']}🪵 · "
            f"{bdef['cost_stone']}🪨 · {bdef['cost_herbs']}🌿\n"
            f"Время постройки: <b>{bdef['build_hours']} ч.</b>\n\n"
        )
        if bstate.get("built"):
            text += "✅ Уже построено."
        elif bstate.get("build_until"):
            from services.clan_service import _fmt_ts
            text += f"🔨 Строится, готово: {_fmt_ts(bstate['build_until'])}"
        elif locked:
            text += f"🔒 Нужен уровень клана {bdef['unlock_level']} (сейчас {lv})."
        else:
            text += (
                f"В казне: {tg:,}💰 / {mats['wood']}🪵 / {mats['stone']}🪨 / {mats['herbs']}🌿\n"
                + ("✅ Ресурсов достаточно." if can_build else "❌ Не хватает ресурсов.")
            )
        await _edit(callback, state, session, text, clan_building_detail_keyboard(key, can_build, m.role))
        await callback.answer()
    except Exception:
        logger.exception("cln:bld:key")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:bld:[a-z_]+:build$"))
async def cb_clan_building_build(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        parts = (callback.data or "").split(":")
        key = parts[2] if len(parts) >= 4 else ""
        from config import is_admin as _is_admin
        _bypass = _is_admin(callback.from_user.id if callback.from_user else None)
        ok, msg = await clan_service.try_start_building(session, char, key, admin_bypass=_bypass)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            # Обновить экран построек
            m = await clan_repo.get_membership(session, int(char.id))
            clan = await clan_repo.get_clan(session, int(m.clan_id)) if m else None
            if clan:
                payload = _payload(clan)
                check_and_complete_buildings(payload)
                text = format_buildings_html(payload, int(clan.clan_level))
                await _edit(callback, state, session, text, clan_buildings_keyboard(payload, int(clan.clan_level), m.role))
    except Exception:
        logger.exception("cln:bld:build")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:relics ─────────────────────────────────────

@router.callback_query(F.data == "cln:relics")
async def cb_clan_relics(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        has_lab = _has_building(payload, "alchemy_lab")
        text = format_relics_html(payload, has_lab)
        await _edit(callback, state, session, text, clan_relics_keyboard(payload, m.role, has_lab))
        await callback.answer()
    except Exception:
        logger.exception("cln:relics")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:relic:craft:[a-z_]+$"))
async def cb_clan_relic_craft(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        rk = (callback.data or "").split(":")[-1]
        ok, msg = await clan_service.try_craft_relic(session, char, rk)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            # Обновить экран реликвий
            m = await clan_repo.get_membership(session, int(char.id))
            clan = await clan_repo.get_clan(session, int(m.clan_id)) if m else None
            if clan:
                payload = _payload(clan)
                has_lab = _has_building(payload, "alchemy_lab")
                text = format_relics_html(payload, has_lab)
                await _edit(callback, state, session, text, clan_relics_keyboard(payload, m.role, has_lab))
    except Exception:
        logger.exception("cln:relic:craft")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:cap ────────────────────────────────────────

_CAPTURE_PAGE_SIZE = 12


def _build_capture_screen(
    callback_data: str | None, page: int = 0
) -> int:
    """Извлечь номер страницы из callback_data вида cln:cap:pg:{n}."""
    if callback_data and callback_data.startswith("cln:cap:pg:"):
        try:
            return int(callback_data.split(":")[-1])
        except ValueError:
            pass
    return page


async def _show_capture_screen(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, page: int = 0
) -> None:
    from services.clan_service import (
        _captured_floors, _fmt_ts, CAPTURABLE_FLOORS,
        CAPTURE_INCOME_PER_HOUR, CAPTURE_LIMIT_PER_CLAN_LEVEL, _floor_capture_active,
    )
    from datetime import datetime, UTC
    _, char = await _get_char(session, callback)
    if char is None:
        return
    m = await clan_repo.get_membership(session, int(char.id))
    if m is None:
        await callback.answer("Ты не в клане.", show_alert=True)
        return
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        await callback.answer("Клан не найден.", show_alert=True)
        return
    payload = _payload(clan)
    caps = _captured_floors(payload)
    now = datetime.now(UTC)
    clan_lv = int(clan.clan_level)
    cap_limit = CAPTURE_LIMIT_PER_CLAN_LEVEL.get(clan_lv, 2)
    active_count = sum(1 for v in caps.values() if _floor_capture_active(v, now))

    # Текст: показываем только активно захваченные этажи
    lines = [f"🗺️ <b>Захват этажей</b>\n"]
    lines.append(
        f"📊 Захвачено: <b>{active_count}/{cap_limit}</b> (ур. клана {clan_lv})\n"
        f"Доход: <b>{CAPTURE_INCOME_PER_HOUR}💰/ч</b> с каждого этажа\n"
    )
    active_entries = [(fl, v) for fl, v in caps.items() if _floor_capture_active(v, now)]
    if active_entries:
        for fl_key, entry in sorted(active_entries, key=lambda x: int(x[0])):
            lines.append(f"✅ Этаж {fl_key} — до {_fmt_ts(entry['expires_at'])}")
    else:
        lines.append("<i>Нет захваченных этажей.</i>")
    lines.append(
        f"\n<i>Этажи для захвата: каждые 5 начиная с 13 (13, 18, 23…)\n"
        f"Нажми кнопку этажа, чтобы инициировать захват.</i>"
    )
    await _edit(
        callback, state, session, "\n".join(lines),
        clan_capture_keyboard(
            m.role, active_caps=caps, cap_limit=cap_limit,
            page=page, page_size=_CAPTURE_PAGE_SIZE,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "cln:cap")
async def cb_clan_capture(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await _show_capture_screen(callback, state, session, page=0)
    except Exception:
        logger.exception("cln:cap")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:cap:pg:\d+$"))
async def cb_clan_cap_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        page = int((callback.data or "cln:cap:pg:0").split(":")[-1])
        await _show_capture_screen(callback, state, session, page=page)
    except Exception:
        logger.exception("cln:cap:pg")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:cap:\d+$"))
async def cb_clan_cap_floor(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        fl = int((callback.data or "").split(":")[-1])
        ok, msg = await clan_service.try_capture_floor(session, char, fl)
        await callback.answer(msg, show_alert=True)
        if ok:
            await _show_capture_screen(callback, state, session, page=0)
    except Exception:
        logger.exception("cln:cap:fl")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:war ────────────────────────────────────────

@router.callback_query(F.data == "cln:war")
async def cb_clan_war(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        war = _war(payload)
        war_status = war.get("status") if war else None
        text = format_war_html(payload)
        await _edit(callback, state, session, text, clan_war_keyboard(m.role, war_status))
        await callback.answer()
    except Exception:
        logger.exception("cln:war")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:war:decl")
async def cb_clan_war_declare_start(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только лидер может объявить войну.", show_alert=True)
            return
        await state.set_state(ClanWarDeclareStates.waiting_target_id)
        await callback.answer()
        if callback.message:
            # Показать топ-5 кланов для выбора
            clan = await clan_repo.get_clan(session, int(m.clan_id))
            if clan:
                top_clans = await clan_repo.find_clans_for_war(session, int(clan.id))
                lines = ["⚔️ <b>Объявить войну</b>\n\nВведи ID клана-противника или выбери из списка:\n"]
                for c in top_clans:
                    lines.append(f"• <code>{c.id}</code> — <b>{html.escape(c.name)}</b> Ур.{c.clan_level}")
                lines.append("\n<i>Стоимость: 5 000 💰 из казны клана.</i>")
            else:
                lines = ["Введи ID клана-противника:"]
            await callback.message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("cln:war:decl")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanWarDeclareStates.waiting_target_id)
async def msg_war_target_id(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw = (message.text or "").strip()
        try:
            target_id = int(raw)
        except ValueError:
            await message.answer("Введи числовой ID клана.", parse_mode=ParseMode.HTML)
            return
        ok, msg = await clan_service.try_declare_war(session, char, target_id)
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_war_target_id")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


@router.callback_query(F.data == "cln:war:acc")
async def cb_clan_war_accept(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        ok, msg = await clan_service.try_accept_war(session, char)
        await callback.answer(msg, show_alert=True)
        if ok:
            await cb_clan_war(callback, session, state)
    except Exception:
        logger.exception("cln:war:acc")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:war:rej")
async def cb_clan_war_reject(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        ok, msg = await clan_service.try_reject_war(session, char)
        await callback.answer(msg, show_alert=True)
        if ok:
            await cb_clan_war(callback, session, state)
    except Exception:
        logger.exception("cln:war:rej")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:leave ──────────────────────────────────────

@router.callback_query(F.data == "cln:leave")
async def cb_clan_leave_confirm(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        await _edit(
            callback, state, session,
            "🚪 <b>Покинуть клан?</b>\n\n<i>Если ты лидер и единственный участник — клан будет распущен.</i>",
            confirm_leave_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("cln:leave")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:leave:yes")
async def cb_clan_leave_do(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        ok, msg = await clan_service.try_leave_clan(session, char)
        await callback.answer(msg, show_alert=True)
        if ok:
            await _edit(
                callback, state, session,
                "⚔️ <b>Кланы</b>\n\nТы покинул клан.",
                clan_no_hub_keyboard(),
            )
    except Exception:
        logger.exception("cln:leave:yes")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── cln:create (FSM) ────────────────────────────────

@router.callback_query(F.data == "cln:create")
async def cb_clan_create_start(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        if await clan_repo.get_membership(session, int(char.id)) is not None:
            await callback.answer("Ты уже в клане.", show_alert=True)
            return
        if int(char.gold) < clan_service.CLAN_CREATE_COST_GOLD:
            await callback.answer(
                f"Нужно {clan_service.CLAN_CREATE_COST_GOLD:,} 💰 для создания клана.",
                show_alert=True,
            )
            return
        await state.set_state(ClanCreateStates.waiting_name)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                f"⚔️ <b>Создание клана</b>\n\n"
                f"Стоимость: <b>{clan_service.CLAN_CREATE_COST_GOLD:,} 💰</b>\n\n"
                f"Введи название клана (2–40 символов):",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:create")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanCreateStates.waiting_name)
async def msg_clan_name(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        name = (message.text or "").strip()
        if not name:
            await message.answer("Введи название клана.", parse_mode=ParseMode.HTML)
            return
        await state.update_data(clan_name=name)
        await state.set_state(ClanCreateStates.waiting_tag)
        await message.answer(
            f"Название: <b>{html.escape(name)}</b>\n\n"
            f"Теперь введи тег клана (2–5 символов, напр. <code>WOLF</code>), "
            f"или отправь <code>-</code> чтобы пропустить:",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("msg_clan_name")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


@router.message(ClanCreateStates.waiting_tag)
async def msg_clan_tag(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw_tag = (message.text or "").strip()
        tag = None if raw_tag == "-" else raw_tag
        data = await state.get_data()
        name = data.get("clan_name", "")
        ok, msg = await clan_service.try_create_clan(session, char, name, tag)
        await state.clear()
        if ok:
            # Показываем результат с кнопкой перехода к клану
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Открыть клан", callback_data="cln:hub")],
                [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")],
            ])
            await message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await message.answer(msg, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("msg_clan_tag")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# ─────────────────────────── cln:join (FSM) ──────────────────────────────────

@router.callback_query(F.data == "cln:join")
async def cb_clan_join_legacy(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Обратная совместимость: старая кнопка 'cln:join' → перенаправляем в cln:nohub."""
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        await _edit(
            callback, state, session,
            "⚔️ <b>Кланы</b>\n\nТы не состоишь в клане.\n"
            "<i>Создай клан или найди существующий в списке.</i>",
            clan_no_hub_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("cln:join legacy")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:join:prompt")
async def cb_clan_join_by_id_prompt(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Вступить по ID вручную (FSM)."""
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        if await clan_repo.get_membership(session, int(char.id)) is not None:
            await callback.answer("Ты уже в клане.", show_alert=True)
            return
        await state.set_state(ClanSettingsStates.waiting_join_id)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "🔍 Введи числовой <b>ID клана</b> для вступления:",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:join:prompt")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanSettingsStates.waiting_join_id)
async def msg_join_by_id(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw = (message.text or "").strip()
        try:
            cid = int(raw)
        except ValueError:
            await message.answer("Введи числовой ID клана.", parse_mode=ParseMode.HTML)
            return
        ok, msg = await clan_service.try_join_clan(session, char, cid)
        await state.clear()
        if ok:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Открыть клан", callback_data="cln:hub")],
                [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")],
            ])
            await message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await message.answer(msg, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("msg_join_by_id")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# ─────────────────────────── cln:panel ──────────────────────────────────────

@router.callback_query(F.data == "cln:panel")
async def cb_clan_panel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только для лидера клана.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        log = list(payload.get("event_log") or [])[-5:]
        log_str = "\n".join(f"• {e['text']} <i>({e['ts'][:16].replace('T',' ')})</i>" for e in reversed(log)) or "<i>нет событий</i>"
        text = (
            f"👑 <b>Панель лидера — «{html.escape(clan.name)}»</b>\n\n"
            f"Последние события:\n{log_str}"
        )
        await _edit(callback, state, session, text, clan_panel_keyboard())
        await callback.answer()
    except Exception:
        logger.exception("cln:panel")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:panel:log")
async def cb_clan_panel_log(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только для лидера.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        payload = _payload(clan)
        log = list(payload.get("event_log") or [])
        lines = [f"📋 <b>Журнал событий клана</b>\n"]
        for e in reversed(log[-20:]):
            ts = e.get("ts", "")[:16].replace("T", " ")
            lines.append(f"• {e['text']} <i>({ts})</i>")
        if not log:
            lines.append("<i>Нет событий.</i>")
        await _edit(
            callback, state, session, "\n".join(lines),
            clan_panel_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("cln:panel:log")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "cln:panel:members")
async def cb_clan_panel_members(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только для лидера.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        rows = await clan_repo.get_members_with_characters(session, int(clan.id))
        text = format_members_list_html(rows, clan.name, True)
        await _edit(callback, state, session, text, clan_panel_members_keyboard(rows, int(char.id)))
        await callback.answer()
    except Exception:
        logger.exception("cln:panel:members")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:pm:\d+$"))
async def cb_clan_pm_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        target_id = int((callback.data or "").split(":")[-1])
        m_actor = await clan_repo.get_membership(session, int(char.id))
        if m_actor is None or m_actor.role != "leader":
            await callback.answer("Только для лидера.", show_alert=True)
            return
        m_target = await clan_repo.get_membership(session, target_id)
        if m_target is None or int(m_target.clan_id) != int(m_actor.clan_id):
            await callback.answer("Участник не найден в клане.", show_alert=True)
            return
        from db.models.character import Character as _Char
        from db.models.user import User as _User
        tgt_char = await session.get(_Char, target_id)
        tgt_user = None
        if tgt_char:
            tgt_user = await session.get(_User, int(tgt_char.user_id))
        username_str = f"@{tgt_user.username}" if tgt_user and tgt_user.username else "<i>нет</i>"
        from services.clan_service import _fmt_ts
        text = (
            f"👤 <b>{html.escape(tgt_char.display_name if tgt_char else str(target_id))}</b>\n"
            f"Роль: {role_label(m_target.role)}\n"
            f"Username: {username_str}\n"
            f"Game ID: <code>{tgt_char.game_id if tgt_char else '?'}</code>\n"
            f"Уровень: {tgt_char.level if tgt_char else '?'} · Этаж: {tgt_char.floor_number if tgt_char else '?'}\n"
            f"Вклад: <b>{int(m_target.contribution_points or 0):,}</b>\n"
            f"В клане с: {_fmt_ts(m_target.joined_at.isoformat() if m_target.joined_at else None)}\n"
            f"Последняя активность: {_fmt_ts(m_target.last_active_at.isoformat() if m_target.last_active_at else None)}"
        )
        await _edit(callback, state, session, text, clan_member_actions_keyboard(target_id, m_target.role))
        await callback.answer()
    except Exception:
        logger.exception("cln:pm")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:role:\d+:(officer|veteran|member)$"))
async def cb_clan_set_role(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        parts = (callback.data or "").split(":")
        target_id = int(parts[2])
        new_role = parts[3]
        ok, msg = await clan_service.try_change_role(session, char, target_id, new_role)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            await cb_clan_panel_members(callback, session, state)
    except Exception:
        logger.exception("cln:role")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:transfer:\d+$"))
async def cb_clan_transfer(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        target_id = int((callback.data or "").split(":")[-1])
        ok, msg = await clan_service.try_transfer_leadership(session, char, target_id)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            await _clan_hub_screen(callback, state, session)
    except Exception:
        logger.exception("cln:transfer")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:kick:\d+$"))
async def cb_clan_kick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        target_id = int((callback.data or "").split(":")[-1])
        ok, msg = await clan_service.try_kick_member(session, char, target_id)
        await callback.answer(msg, show_alert=not ok)
        if ok:
            await cb_clan_panel_members(callback, session, state)
    except Exception:
        logger.exception("cln:kick")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── Браузер кланов ─────────────────────────────────

_BROWSE_PAGE_SIZE = 8


@router.callback_query(F.data == "cln:nohub")
async def cb_clan_nohub(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Экран «ты не в клане»."""
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        await _edit(
            callback, state, session,
            "⚔️ <b>Кланы</b>\n\nТы не состоишь в клане.\n"
            "<i>Создай клан или найди существующий в списке.</i>",
            clan_no_hub_keyboard(),
        )
        await callback.answer()
    except Exception:
        logger.exception("cln:nohub")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:browse:\d+$"))
async def cb_clan_browse(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Список всех кланов постранично."""
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        page = int((callback.data or "cln:browse:0").split(":")[-1])
        in_clan = await clan_repo.get_membership(session, int(char.id)) is not None
        clans, total = await clan_service.browse_clans_page(session, page, _BROWSE_PAGE_SIZE)
        text = format_clan_browse_html(clans, page, total, _BROWSE_PAGE_SIZE)
        kb = clan_browse_keyboard(clans, page, total, _BROWSE_PAGE_SIZE, in_clan)
        await _edit(callback, state, session, text, kb)
        await callback.answer()
    except Exception:
        logger.exception("cln:browse")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:browse:view:\d+$"))
async def cb_clan_browse_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Просмотр карточки конкретного клана из списка."""
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        clan_id = int((callback.data or "").split(":")[-1])
        clan = await clan_repo.get_clan(session, clan_id)
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        from services.clan_service import _payload as _p, _mat, _treasury_gold, _treasury_limit, _has_building
        payload = _p(clan)
        n = await clan_repo.count_members(session, int(clan.id))
        max_m = max_members_for_level(int(clan.clan_level))
        if _has_building(payload, "barracks"):
            max_m += 5
        tag_str = f" [{html.escape(clan.tag)}]" if clan.tag else ""
        desc_str = f"\n\n📝 {html.escape(clan.description)}" if clan.description else ""
        chat_str = f'\n💬 <a href="{html.escape(clan.chat_url)}">Чат клана</a>' if clan.chat_url else ""
        in_clan = await clan_repo.get_membership(session, int(char.id)) is not None
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        btns: list[list[InlineKeyboardButton]] = []
        if not in_clan and n < max_m:
            btns.append([InlineKeyboardButton(text="➕ Вступить", callback_data=f"cln:join:{clan.id}")])
        btns.append([
            InlineKeyboardButton(text="◀️ К списку", callback_data="cln:browse:0"),
            InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub"),
        ])
        text = (
            f"⚔️ <b>{html.escape(clan.name)}</b>{tag_str} · ID <code>{clan.id}</code>\n"
            f"📊 Ур. <b>{clan.clan_level}/10</b> · 👥 {n}/{max_m}"
            f"{desc_str}"
            f"{chat_str}"
        )
        await _edit(callback, state, session, text, InlineKeyboardMarkup(inline_keyboard=btns))
        await callback.answer()
    except Exception:
        logger.exception("cln:browse:view")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^cln:join:\d+$"))
async def cb_clan_join_by_id(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Вступление в клан по ID (из браузера или карточки)."""
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        clan_id = int((callback.data or "").split(":")[-1])
        ok, msg = await clan_service.try_join_clan(session, char, clan_id)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        # При успехе — показываем хаб клана (он сам вызывает callback.answer)
        await _clan_hub_screen(callback, state, session)
    except Exception:
        logger.exception("cln:join:N")
        await callback.answer("Ошибка.", show_alert=True)


# ─────────────────────────── Настройки клана ────────────────────────────────

@router.callback_query(F.data == "cln:settings")
async def cb_clan_settings(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None:
            await callback.answer("Ты не в клане.", show_alert=True)
            return
        if m.role not in ("leader", "officer"):
            await callback.answer("Только лидер или офицер.", show_alert=True)
            return
        clan = await clan_repo.get_clan(session, int(m.clan_id))
        if clan is None:
            await callback.answer("Клан не найден.", show_alert=True)
            return
        text = format_clan_settings_html(clan)
        await _edit(callback, state, session, text, clan_settings_keyboard(m.role))
        await callback.answer()
    except Exception:
        logger.exception("cln:settings")
        await callback.answer("Ошибка.", show_alert=True)


# --- Изменить описание ---

@router.callback_query(F.data == "cln:set:desc")
async def cb_set_desc_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role not in ("leader", "officer"):
            await callback.answer("Нет доступа.", show_alert=True)
            return
        await state.set_state(ClanSettingsStates.waiting_description)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "📝 Введи новое описание клана (до 200 символов).\n"
                "Отправь <code>-</code> чтобы удалить описание.",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:set:desc")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanSettingsStates.waiting_description)
async def msg_set_desc(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw = (message.text or "").strip()
        text = "" if raw == "-" else raw
        ok, msg = await clan_service.try_set_description(session, char, text)
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_set_desc")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# --- Изменить тег ---

@router.callback_query(F.data == "cln:set:tag")
async def cb_set_tag_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только лидер.", show_alert=True)
            return
        await state.set_state(ClanSettingsStates.waiting_tag)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "🏷️ Введи новый тег клана (2–5 символов, напр. <code>WOLF</code>).\n"
                "Отправь <code>-</code> чтобы убрать тег.",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:set:tag")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanSettingsStates.waiting_tag)
async def msg_set_tag(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw = (message.text or "").strip()
        ok, msg = await clan_service.try_set_tag(session, char, raw)
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_set_tag")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# --- Переименование ---

@router.callback_query(F.data == "cln:set:name")
async def cb_set_name_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role != "leader":
            await callback.answer("Только лидер.", show_alert=True)
            return
        await state.set_state(ClanSettingsStates.waiting_name)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "📛 Введи новое название клана (2–40 символов).\n"
                "<i>Стоимость переименования: 5 000 💰.</i>",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:set:name")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanSettingsStates.waiting_name)
async def msg_set_name(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        # Проверяем, что мы не в процессе создания клана (у ClanCreateStates тоже waiting_name)
        raw = (message.text or "").strip()
        ok, msg = await clan_service.try_rename_clan(session, char, raw)
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_set_name (rename)")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()


# --- Ссылка на чат ---

@router.callback_query(F.data == "cln:set:chat")
async def cb_set_chat_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        _, char = await _get_char(session, callback)
        if char is None:
            return
        m = await clan_repo.get_membership(session, int(char.id))
        if m is None or m.role not in ("leader", "officer"):
            await callback.answer("Нет доступа.", show_alert=True)
            return
        await state.set_state(ClanSettingsStates.waiting_chat_url)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                "💬 Введи ссылку на чат клана (https://t.me/... или t.me/...).\n"
                "Отправь <code>-</code> чтобы убрать ссылку.",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("cln:set:chat")
        await callback.answer("Ошибка.", show_alert=True)


@router.message(ClanSettingsStates.waiting_chat_url)
async def msg_set_chat(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            return
        raw = (message.text or "").strip()
        if raw == "-":
            m = await clan_repo.get_membership(session, int(char.id))
            if m:
                clan = await clan_repo.get_clan(session, int(m.clan_id))
                if clan:
                    clan.chat_url = None
                    await session.flush()
            await message.answer("Ссылка на чат удалена.", parse_mode=ParseMode.HTML)
        else:
            ok, msg = await clan_service.try_set_clan_chat(session, char, raw)
            await message.answer(msg, parse_mode=ParseMode.HTML)
        await state.clear()
    except Exception:
        logger.exception("msg_set_chat")
        await message.answer("Ошибка.", parse_mode=ParseMode.HTML)
        await state.clear()
