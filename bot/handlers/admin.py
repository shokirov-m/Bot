"""
Админ-панель: инлайн-кнопки + текстовые команды (совместимость).
ADMIN_IDS в .env обязателен для доступа.
"""

from __future__ import annotations

import asyncio
import html
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from admin import panel
from bot.middlewares.admin_check import IsAdmin
from bot.keyboards.admin_kb import (
    ADMIN_PLAYERS_PAGE_SIZE,
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_panel_keyboard,
    admin_player_purchases_back_keyboard,
    admin_player_snapshot_keyboard,
    admin_players_browser_keyboard,
    admin_promo_keyboard,
    admin_spend_ledger_nav_keyboard,
    admin_title_grant_keyboard,
)
from bot.states.admin_states import AdminStates
from config import settings
from db.models.character import Character
from db.models.inventory import InventoryItem
from db.repository import admin_log_repo, character_repo, inventory_repo, user_repo
from db.repository import clan_repo, mercenary_repo
from game.items import equipment as equipment_mod
from game.characters.path_ranks import path_rank_name_ru
from services import anticheat_service, arena_service, character_service, title_service
from services.activity_service import activity_admin_lines, format_dt_utc, format_duration_ru
from services.admin_promo_service import handle_admin_promo, promo_help_html

router = Router(name="admin")

PANEL_HTML = (
    "🔧 <b>Админ-панель</b>\n"
    "Выбери действие кнопкой.\n"
    "📈 <b>Уровень игроку:</b> список «Все игроки» → строка героя → кнопки <b>+1 / +5 / +10</b> "
    "или цель <b>25 / 50 / 100</b> ур. (только <b>повышение</b>, до 9999).\n"
    "<i>Команды <code>/admin …</code>, <code>/admin_stats</code>, "
    "<code>/admin_ban</code> и т.д. тоже работают.</i>"
)

_PROMO_MENU_HTML = "🎁 <b>Промокоды</b>\nВыбери действие или вернись в панель."


async def _dashboard_stats(session: AsyncSession) -> dict[str, object]:
    m = await character_repo.admin_dashboard_metrics(session)
    alerts_n, crit_n = await admin_log_repo.count_alerts_since(session, hours=24)
    m["alerts_24h"] = alerts_n
    m["critical_24h"] = crit_n
    m["anticheat_enabled"] = settings.ANTICHEAT_ENABLED
    return m


async def _logs_html(session: AsyncSession, *, show_all: bool) -> str | None:
    if show_all:
        rows = await admin_log_repo.recent_all(session, limit=18)
        header = "📋 <b>Последние события</b> (все)\n"
    else:
        rows = await admin_log_repo.recent_high_severity(session, limit=12)
        header = "⚠️ <b>Алерты</b> (ALERT / CRITICAL)\n"
    if not rows:
        return None
    lines: list[str] = [header]
    for r in rows:
        msg = html.escape((r.message or "")[:120])
        actor = r.actor_telegram_id
        act = f" · от <code>{actor}</code>" if actor else ""
        lines.append(
            f"<code>{r.created_at:%Y-%m-%d %H:%M}</code> "
            f"[{html.escape(r.severity)}] <b>{html.escape(r.action)}</b>{act}\n{msg}",
        )
    return "\n\n".join(lines)


def _admin_equipped_lines_from_items(items: list[InventoryItem]) -> list[str]:
    """Короткие строки для админки: слот + редкость + имя."""
    lines: list[str] = []
    for it in items:
        d = it.item_data or {}
        name = html.escape(str(d.get("name", "—")))
        rar = str(d.get("rarity", "common"))
        emo = equipment_mod.RARITY_EMOJI.get(rar, "⚪")
        slot = str(it.equip_slot or "?")
        slot_lab = equipment_mod.slot_label_ru(slot)
        slot_html = html.escape(slot_lab)
        lines.append(f"{slot_html}: {emo} {name}")
    return lines


def _truncate_html(s: str, max_len: int = 3800) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 20] + "\n… <i>(обрезано)</i>"


async def _admin_player_snapshot_html(session: AsyncSession, character_id: int) -> tuple[str | None, Character | None]:
    """HTML карточки игрока для админки или (None, None) если нет данных."""
    ch = await character_repo.get_by_id(session, character_id)
    if ch is None:
        return None, None
    u = await user_repo.get_by_id(session, int(ch.user_id))
    if u is None:
        return None, None
    equipped = await inventory_repo.list_equipped_items(session, int(ch.id))
    lines = _admin_equipped_lines_from_items(equipped)
    act = activity_admin_lines(ch)
    est_play = format_duration_ru(act["play_sec"])
    last_iso = act["last_activity_iso"]
    if last_iso:
        try:
            dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
            last_activity_utc = format_dt_utc(dt)
        except ValueError:
            last_activity_utc = str(last_iso)
    else:
        last_activity_utc = format_dt_utc(ch.updated_at)

    clan_line = ""
    mem = await clan_repo.get_membership(session, int(ch.id))
    if mem is not None:
        cl = await clan_repo.get_clan(session, int(mem.clan_id))
        if cl is not None:
            tag = f" [{cl.tag}]" if cl.tag else ""
            clan_line = f"Клан: «{cl.name}»{tag} · роль: {mem.role}"

    arena_mmr_line = f"Арена MMR: {arena_service.arena_mmr(ch)}"
    pr = path_rank_name_ru(ch)
    path_rank_line = f"Звание (путь): {pr}" if pr else ""

    sec_raw = (ch.meta_progress or {}).get("active_title_secondary_name_ru")
    sec_s = str(sec_raw).strip() if sec_raw else ""
    t_parts = []
    if ch.active_title:
        t_parts.append(f"① {ch.active_title}")
    if sec_s:
        t_parts.append(f"② {sec_s}")
    titles_line = "Титулы: " + " · ".join(t_parts) if t_parts else ""

    merc_n = await mercenary_repo.count_for_character(session, int(ch.id))
    mercenaries_line = f"Наёмников в ростере: {merc_n}"

    body = panel.format_admin_player_snapshot_html(
        telegram_id=int(u.telegram_id),
        username=u.username,
        display_name=ch.display_name,
        level=int(ch.level),
        floor_number=int(ch.floor_number),
        class_key=str(ch.class_key),
        is_banned=bool(u.is_banned),
        hp_current=int(ch.hp_current),
        hp_max=int(ch.hp_max),
        mp_current=int(ch.mp_current),
        mp_max=int(ch.mp_max),
        gold=int(ch.gold),
        unspent_stat_points=int(ch.unspent_stat_points),
        equipped_lines=lines,
        account_created_at_utc=format_dt_utc(u.created_at),
        hero_created_at_utc=format_dt_utc(ch.created_at),
        estimated_playtime_ru=est_play,
        last_activity_utc=last_activity_utc,
        clan_line=clan_line,
        arena_mmr_line=arena_mmr_line,
        titles_line=titles_line,
        mercenaries_line=mercenaries_line,
        path_rank_line=path_rank_line,
    )
    return body, ch


async def _safe_edit_panel(
    message: Message,
    text: str,
    *,
    reply_markup,
) -> None:
    try:
        await message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest:
        logger.warning("admin: edit_text не удался")


async def _restore_hub(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _safe_edit_panel(message, PANEL_HTML, reply_markup=admin_panel_keyboard())


async def _run_broadcast(
    message: Message,
    session: AsyncSession,
    text: str,
    *,
    actor_telegram_id: int,
) -> tuple[int, int]:
    body = html.escape(text)
    ids = await user_repo.list_telegram_ids_for_broadcast(session)
    ok, fail = 0, 0
    bot = message.bot
    for tid in ids:
        try:
            await bot.send_message(
                tid,
                f"📢 <b>Сообщение от администрации</b>\n\n{body}",
                parse_mode=ParseMode.HTML,
            )
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.04)
    try:
        await anticheat_service.log_admin_action(
            session,
            actor_telegram_id=actor_telegram_id,
            target_user_id=None,
            action="admin_broadcast",
            message=text[:500],
            payload={
                "recipients": len(ids),
                "delivered_ok": ok,
                "delivered_fail": fail,
            },
        )
        await session.commit()
    except Exception:
        logger.exception("admin_broadcast log")
    return ok, fail


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message, session: AsyncSession, command: CommandObject, state: FSMContext) -> None:
    if message.from_user is None:
        return
    parts = (command.args or "").strip().split()
    if not parts:
        await state.clear()
        try:
            await message.answer(PANEL_HTML, parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())
        except Exception:
            logger.exception("cmd_admin panel")
            await message.answer("Ошибка.")
        return

    sub = parts[0].lower()
    if sub == "stats":
        try:
            stats = await _dashboard_stats(session)
            await message.answer(panel.format_dashboard_html(stats), parse_mode=ParseMode.HTML)
        except Exception:
            logger.exception("admin stats")
            await message.answer("Ошибка запроса к БД.")
        return

    if sub == "logs":
        try:
            show_all = len(parts) >= 2 and parts[1].lower() == "all"
            body = await _logs_html(session, show_all=show_all)
            if body is None:
                await message.answer(
                    "Записей пока нет." if show_all else "Записей ALERT/CRITICAL пока нет.",
                )
                return
            await message.answer(_truncate_html(body), parse_mode=ParseMode.HTML)
        except Exception:
            logger.exception("admin logs")
            await message.answer("Ошибка запроса к БД.")
        return

    if sub == "promo":
        try:
            await handle_admin_promo(
                message,
                session,
                parts,
                actor_telegram_id=message.from_user.id,
            )
        except Exception:
            logger.exception("admin promo")
            await message.answer("Ошибка.")
        return

    if sub == "user" and len(parts) >= 2 and parts[1].isdigit():
        await _answer_user_lookup(message, session, int(parts[1]))
        return

    if (
        sub == "give"
        and len(parts) >= 4
        and parts[1].lower() == "gold"
        and parts[2].isdigit()
        and parts[3].isdigit()
    ):
        await _do_give_gold(
            message,
            session,
            int(parts[2]),
            int(parts[3]),
            actor_telegram_id=message.from_user.id,
        )
        return

    if sub == "clear_inv" and len(parts) >= 2:
        await _do_wipe_inventory(
            message,
            session,
            parts[1],
            actor_telegram_id=message.from_user.id,
        )
        return

    await message.answer(
        "Неизвестная подкоманда. Отправь <code>/admin</code> без аргументов — откроется панель.",
        parse_mode=ParseMode.HTML,
    )


async def _answer_user_lookup(message: Message, session: AsyncSession, tid: int) -> None:
    try:
        u = await user_repo.get_by_telegram_id(session, tid)
        if u is None:
            await message.answer(f"Нет пользователя <code>{tid}</code>.", parse_mode=ParseMode.HTML)
            return
        ch = await character_repo.get_by_user_id(session, u.id)
        if ch is None:
            await message.answer(
                f"TG <code>{tid}</code> — без персонажа. Бан: <b>{u.is_banned}</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        bag_n = await character_repo.count_bag_items(session, ch.id)
        un = html.escape(u.username or "—")
        dn = html.escape(ch.display_name)
        await message.answer(
            f"👤 TG <code>{tid}</code> @{un}\n"
            f"user_id: <code>{u.id}</code> · бан: <b>{u.is_banned}</b>\n"
            f"Персонаж: <b>{dn}</b> ур. <b>{ch.level}</b>\n"
            f"Этаж: <b>{ch.floor_number}</b> · золото: <b>{ch.gold}</b>\n"
            f"Предметов в сумке: <b>{bag_n}</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("admin user")
        await message.answer("Ошибка запроса к БД.")


async def _do_give_gold(
    message: Message,
    session: AsyncSession,
    tid: int,
    amt: int,
    *,
    actor_telegram_id: int,
) -> None:
    if amt <= 0 or amt > 50_000_000:
        await message.answer("Сумма должна быть 1…50 000 000.")
        return
    try:
        u = await user_repo.get_by_telegram_id(session, tid)
        if u is None:
            await message.answer(f"Нет пользователя <code>{tid}</code>.", parse_mode=ParseMode.HTML)
            return
        ch = await character_repo.get_by_user_id(session, u.id)
        if ch is None:
            await message.answer("У пользователя нет персонажа.", parse_mode=ParseMode.HTML)
            return
        character_service.add_gold(ch, amt)
        await anticheat_service.log_admin_action(
            session,
            actor_telegram_id=actor_telegram_id,
            target_user_id=u.id,
            action="admin_give_gold",
            message=f"+{amt}",
            payload={"telegram_id": tid, "amount": amt, "character_id": ch.id},
        )
        await session.commit()
        await message.answer(
            f"Начислено <b>{amt}</b> золота персонажу <code>{html.escape(ch.display_name)}</code>.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("admin give")
        await message.answer("Ошибка запроса к БД.")


# ——— Колбэки панели ———


@router.callback_query(F.data == "adm:hub", IsAdmin())
async def cb_admin_hub(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _restore_hub(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "adm:cancel", IsAdmin())
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _restore_hub(callback.message, state)
    await callback.answer("Отменено.")


async def _admin_render_players_page(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    *,
    page: int,
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    page = max(0, int(page))
    total = await character_repo.count_characters(session)
    if total <= 0:
        await _safe_edit_panel(
            callback.message,
            "🧙 <b>Игроки</b>\nПерсонажей в базе пока нет.",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return
    max_page = (total - 1) // ADMIN_PLAYERS_PAGE_SIZE
    if page > max_page:
        page = max_page
    offset = page * ADMIN_PLAYERS_PAGE_SIZE
    rows_full = await character_repo.list_characters_admin_browser(
        session,
        offset=offset,
        limit=ADMIN_PLAYERS_PAGE_SIZE,
    )
    entries = [(cid, dn, lvl, banned) for cid, dn, lvl, _tid, banned, _ck in rows_full]
    total_pages = (total + ADMIN_PLAYERS_PAGE_SIZE - 1) // ADMIN_PLAYERS_PAGE_SIZE
    header = (
        f"🧙 <b>Список игроков</b> · стр. <b>{page + 1}</b>/<b>{total_pages}</b> "
        f"(всего героев: <b>{total}</b>)\n"
        "<i>Нажми строку — карточка героя, надетые вещи и кнопки выдачи уровня (+1/+5/+10, до 25/50/100).</i>"
    )
    kb = admin_players_browser_keyboard(
        entries,
        page=page,
        page_size=ADMIN_PLAYERS_PAGE_SIZE,
        total_entries=total,
    )
    await _safe_edit_panel(callback.message, header, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "adm:players", IsAdmin())
async def cb_admin_players_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await _admin_render_players_page(callback, session, state, page=0)


@router.callback_query(F.data.startswith("adm:pl:"), IsAdmin())
async def cb_admin_players_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer()
        return
    await _admin_render_players_page(callback, session, state, page=int(parts[2]))


@router.callback_query(F.data.startswith("adm:pv:"), IsAdmin())
async def cb_admin_player_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 3 or parts[0] != "adm" or parts[1] != "pv" or not parts[2].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    ret_page = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 0
    try:
        body, ch = await _admin_player_snapshot_html(session, cid)
        if body is None or ch is None:
            await callback.answer("Персонаж или пользователь не найден.", show_alert=True)
            return
        await _safe_edit_panel(
            callback.message,
            _truncate_html(body),
            reply_markup=admin_player_snapshot_keyboard(character_id=cid, return_page=ret_page),
        )
        await callback.answer()
    except Exception:
        logger.exception("adm:pv")
        await callback.answer("Ошибка БД.", show_alert=True)


@router.callback_query(F.data.startswith("adm:pur:"), IsAdmin())
async def cb_admin_player_purchases(callback: CallbackQuery, session: AsyncSession) -> None:
    """Журнал трат золота (meta_progress), для админа — с пагинацией."""
    if callback.message is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 5 or parts[0] != "adm" or parts[1] != "pur" or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer()
        return
    if not parts[4].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    ret_page = int(parts[3])
    page = int(parts[4])
    try:
        ch = await character_repo.get_by_id(session, cid)
        if ch is None:
            await callback.answer("Персонаж не найден.", show_alert=True)
            return
        text, cur_page, total_pages = character_service.format_spend_ledger_admin_html(ch, page=page)
        await _safe_edit_panel(
            callback.message,
            _truncate_html(text),
            reply_markup=admin_spend_ledger_nav_keyboard(
                character_id=cid,
                return_page=ret_page,
                page=cur_page,
                total_pages=total_pages,
            ),
        )
        await callback.answer()
    except Exception:
        logger.exception("adm:pur")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm:tish:"), IsAdmin())
async def cb_admin_title_grant_open(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    pg = int(parts[3])
    try:
        ch = await character_repo.get_by_id(session, cid)
        if ch is None:
            await callback.answer("Персонаж не найден.", show_alert=True)
            return
        await _safe_edit_panel(
            callback.message,
            "🏅 <b>Выдача титула</b>\n\n<i>Выбери строку — титул откроется в списке игрока (можно экипировать в профиле).</i>",
            reply_markup=admin_title_grant_keyboard(character_id=cid, return_page=pg, page_idx=0),
        )
        await callback.answer()
    except Exception:
        logger.exception("adm:tish")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm:tcst:"), IsAdmin())
async def cb_admin_custom_title_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Персональный титул: имя + бонусы текстом, объявление в канале гачи."""
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    pg = int(parts[3])
    ch = await character_repo.get_by_id(session, cid)
    if ch is None:
        await callback.answer("Персонаж не найден.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_input)
    await state.update_data(
        admin_kind="custom_title_name",
        custom_title_cid=cid,
        custom_title_pg=pg,
    )
    await callback.message.answer(
        "🌟 <b>Персональный титул</b>\n\n"
        f"Игрок: <b>{html.escape((ch.display_name or '?').strip() or '?')}</b> (id <code>{cid}</code>)\n\n"
        "Шаг <b>1/2</b>: одной строкой пришли <b>название</b> титула (1–48 символов, без HTML).\n\n"
        "Отмена: кнопка ниже.",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer("Жду название…")


@router.callback_query(F.data.startswith("adm:ttp:"), IsAdmin())
async def cb_admin_title_grant_page(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 5 or not parts[2].isdigit() or not parts[3].isdigit() or not parts[4].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    pg = int(parts[3])
    pidx = int(parts[4])
    try:
        ch = await character_repo.get_by_id(session, cid)
        if ch is None:
            await callback.answer("Персонаж не найден.", show_alert=True)
            return
        await _safe_edit_panel(
            callback.message,
            "🏅 <b>Выдача титула</b>\n\n<i>Выбери строку — титул откроется в списке игрока.</i>",
            reply_markup=admin_title_grant_keyboard(character_id=cid, return_page=pg, page_idx=pidx),
        )
        await callback.answer()
    except Exception:
        logger.exception("adm:ttp")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm:tti:"), IsAdmin())
async def cb_admin_title_grant_apply(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 5 or not parts[2].isdigit() or not parts[3].isdigit() or not parts[4].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    pg = int(parts[3])
    idx = int(parts[4])
    try:
        from game.characters.titles import ALL_TITLES

        if idx < 0 or idx >= len(ALL_TITLES):
            await callback.answer("Неверный индекс.", show_alert=True)
            return
        ch = await character_repo.get_by_id(session, cid)
        if ch is None:
            await callback.answer("Персонаж не найден.", show_alert=True)
            return
        key = ALL_TITLES[idx].key
        ok, msg = title_service.admin_ensure_title_unlocked(ch, key)
        if not ok:
            await callback.answer(msg, show_alert=True)
            return
        await anticheat_service.log_admin_action(
            session,
            actor_telegram_id=int(callback.from_user.id),
            target_user_id=int(ch.user_id),
            action="admin_grant_title",
            message=f"title:{key}",
            payload={"character_id": cid, "title_key": key},
        )
        await session.commit()
        body, ch2 = await _admin_player_snapshot_html(session, cid)
        if body is None or ch2 is None:
            await callback.answer("Сохранено.", show_alert=True)
            return
        await _safe_edit_panel(
            callback.message,
            _truncate_html(body),
            reply_markup=admin_player_snapshot_keyboard(character_id=cid, return_page=pg),
        )
        await callback.answer(f"Титул «{msg}» ✓")
    except Exception:
        logger.exception("adm:tti")
        await callback.answer("Ошибка БД.", show_alert=True)


async def _admin_apply_level_and_refresh(
    *,
    callback: CallbackQuery,
    session: AsyncSession,
    character_id: int,
    return_page: int,
    actor_telegram_id: int,
    delta: int | None = None,
    target_level: int | None = None,
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    ch = await character_repo.get_by_id(session, character_id)
    if ch is None:
        await callback.answer("Персонаж не найден.", show_alert=True)
        return
    u = await user_repo.get_by_id(session, int(ch.user_id))
    if u is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    old_lv = int(ch.level)
    gained, err = await character_service.admin_grant_character_levels(
        session,
        ch,
        delta=delta,
        target_level=target_level,
    )
    if err:
        await callback.answer(err, show_alert=True)
        return
    await anticheat_service.log_admin_action(
        session,
        actor_telegram_id=actor_telegram_id,
        target_user_id=int(u.id),
        action="admin_grant_levels",
        message=f"{old_lv}→{int(ch.level)} (+{gained})",
        payload={
            "character_id": int(ch.id),
            "telegram_id": int(u.telegram_id),
            "levels_added": gained,
            "level_before": old_lv,
            "level_after": int(ch.level),
        },
    )
    await session.commit()
    body, ch2 = await _admin_player_snapshot_html(session, character_id)
    if body is None or ch2 is None:
        await callback.answer("Готово, но карточку обновить не удалось.", show_alert=True)
        return
    await _safe_edit_panel(
        callback.message,
        _truncate_html(body),
        reply_markup=admin_player_snapshot_keyboard(
            character_id=character_id,
            return_page=return_page,
        ),
    )
    await callback.answer(f"+{gained} ур. → сейчас {int(ch2.level)} ✓")


@router.callback_query(F.data.startswith("adm:lvw:"), IsAdmin())
async def cb_admin_level_delta(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 5 or parts[1] != "lvw" or not parts[2].isdigit() or not parts[3].isdigit() or not parts[4].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    page = int(parts[3])
    d = int(parts[4])
    try:
        await _admin_apply_level_and_refresh(
            callback=callback,
            session=session,
            character_id=cid,
            return_page=page,
            actor_telegram_id=int(callback.from_user.id),
            delta=d,
            target_level=None,
        )
    except Exception:
        logger.exception("adm:lvw")
        await callback.answer("Ошибка БД.", show_alert=True)


@router.callback_query(F.data.startswith("adm:lvs:"), IsAdmin())
async def cb_admin_level_set(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None:
        await callback.answer()
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 5 or parts[1] != "lvs" or not parts[2].isdigit() or not parts[3].isdigit() or not parts[4].isdigit():
        await callback.answer()
        return
    cid = int(parts[2])
    page = int(parts[3])
    tgt = int(parts[4])
    try:
        await _admin_apply_level_and_refresh(
            callback=callback,
            session=session,
            character_id=cid,
            return_page=page,
            actor_telegram_id=int(callback.from_user.id),
            delta=None,
            target_level=tgt,
        )
    except Exception:
        logger.exception("adm:lvs")
        await callback.answer("Ошибка БД.", show_alert=True)


@router.callback_query(F.data == "adm:lv_id", IsAdmin())
async def cb_admin_level_by_id(callback: CallbackQuery, state: FSMContext) -> None:
    await _prompt_fsm(
        callback,
        state,
        kind="level_tid",
        html_text=(
            "📈 <b>Уровень по Telegram ID</b>\n"
            "Введи <b>только цифры</b> — ID пользователя в Telegram.\n"
            "Откроется та же карточка, что в списке игроков: кнопки <b>+1 / +5 / +10</b> "
            "и <b>до 25 / 50 / 100</b> ур. Снижать уровень этим способом нельзя."
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:referrals", IsAdmin())
async def cb_admin_referrals(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    try:
        limit = 80
        rows = await user_repo.referral_registrations_by_inviter(session, limit=limit)
        total = await user_repo.count_users_with_referrer(session)
        body = panel.format_referrals_admin_html(rows, total_with_referrer=total, limit_shown=limit)
        await _safe_edit_panel(callback.message, _truncate_html(body), reply_markup=admin_back_keyboard())
        await callback.answer()
    except Exception:
        logger.exception("adm:referrals")
        await callback.answer("Ошибка БД.", show_alert=True)


@router.callback_query(F.data == "adm:stats", IsAdmin())
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    try:
        stats = await _dashboard_stats(session)
        body = panel.format_dashboard_html(stats)
        await _safe_edit_panel(callback.message, body, reply_markup=admin_back_keyboard())
        await callback.answer()
    except Exception:
        logger.exception("adm:stats")
        await callback.answer("Ошибка БД.", show_alert=True)


@router.callback_query(F.data == "adm:logs", IsAdmin())
async def cb_admin_logs(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        body = await _logs_html(session, show_all=False)
        if body is None:
            await callback.answer("Записей нет.", show_alert=True)
            return
        await callback.message.answer(_truncate_html(body), parse_mode=ParseMode.HTML)
        await callback.answer("Логи отправлены в чат.")
    except Exception:
        logger.exception("adm:logs")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "adm:logs_all", IsAdmin())
async def cb_admin_logs_all(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        body = await _logs_html(session, show_all=True)
        if body is None:
            await callback.answer("Записей нет.", show_alert=True)
            return
        await callback.message.answer(_truncate_html(body), parse_mode=ParseMode.HTML)
        await callback.answer("Логи отправлены в чат.")
    except Exception:
        logger.exception("adm:logs_all")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "adm:promo", IsAdmin())
async def cb_admin_promo_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    await _safe_edit_panel(callback.message, _PROMO_MENU_HTML, reply_markup=admin_promo_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:promo_list", IsAdmin())
async def cb_admin_promo_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    try:
        await handle_admin_promo(
            callback.message,
            session,
            ["promo", "list"],
            actor_telegram_id=callback.from_user.id,
        )
        await callback.answer()
    except Exception:
        logger.exception("adm:promo_list")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "adm:promo_help", IsAdmin())
async def cb_admin_promo_help(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        await callback.message.answer(promo_help_html(), parse_mode=ParseMode.HTML)
        await callback.answer("Справка в чате.")
    except Exception:
        logger.exception("adm:promo_help")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "adm:promo_cmd", IsAdmin())
async def cb_admin_promo_cmd(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(AdminStates.waiting_input)
    await state.update_data(
        admin_kind="promo_cmd",
        panel_mid=callback.message.message_id,
        panel_cid=callback.message.chat.id,
    )
    await _safe_edit_panel(
        callback.message,
        "✏️ Отправь <b>одной строкой</b> команду, например:\n"
        "<code>/admin promo add КОД 500 100 1 50 0</code>\n"
        "или без префикса: <code>promo add КОД …</code>",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


async def _prompt_fsm(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    kind: str,
    html_text: str,
) -> None:
    if callback.message is None:
        return
    await state.set_state(AdminStates.waiting_input)
    await state.update_data(
        admin_kind=kind,
        panel_mid=callback.message.message_id,
        panel_cid=callback.message.chat.id,
    )
    await _safe_edit_panel(callback.message, html_text, reply_markup=admin_cancel_keyboard())


@router.callback_query(F.data == "adm:user", IsAdmin())
async def cb_admin_user(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="user",
        html_text="👤 Введи <b>Telegram ID</b> игрока (только цифры).",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:give", IsAdmin())
async def cb_admin_give(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="give",
        html_text="💰 Введи через пробел: <code>TELEGRAM_ID СУММА</code>\n"
        "Сумма 1…50 000 000.",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:give_runes", IsAdmin())
async def cb_admin_give_runes(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="give_runes",
        html_text="💎 Введи через пробел: <code>TELEGRAM_ID КОЛИЧЕСТВО_РУН</code>\nМаксимум 999 999.",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:heal", IsAdmin())
async def cb_admin_heal(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="heal",
        html_text="❤️ Введи <b>Telegram ID</b> игрока — полностью восстановить HP/MP.",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:stamina", IsAdmin())
async def cb_admin_stamina(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="stamina",
        html_text="⚡ Введи <b>Telegram ID</b> игрока — поставить стамину на максимум.",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:give_items", IsAdmin())
async def cb_admin_give_items(callback: CallbackQuery, session: AsyncSession) -> None:
    """Выдать себе все расходники + пополнить все ресурсы до 10 000."""
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    try:
        u = await user_repo.get_by_telegram_id(session, callback.from_user.id)
        ch = await character_repo.get_by_user_id(session, u.id) if u else None
        if ch is None:
            await callback.answer("Нет персонажа.", show_alert=True)
            return
        from services.admin_utils import ensure_admin_resources, give_admin_all_items
        await ensure_admin_resources(session, ch)
        added = await give_admin_all_items(session, ch)
        await session.commit()
        await callback.answer(
            f"✅ Ресурсы пополнены до 10 000. Добавлено позиций: {added}.",
            show_alert=True,
        )
    except Exception:
        logger.exception("adm:give_items")
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "adm:reset_tier2", IsAdmin())
async def cb_admin_reset_tier2(callback: CallbackQuery, state: FSMContext) -> None:
    """Запустить одноразовый сброс Тир-2 классов у игроков ниже 50 уровня."""
    if callback.message is None or callback.bot is None:
        await callback.answer()
        return
    try:
        await callback.answer("⏳ Запускаю сброс Тир-2 классов…", show_alert=False)
        await callback.message.answer("⏳ <b>Сброс Тир-2 классов запущен.</b> Ожидай результата…", parse_mode=ParseMode.HTML)
        from services.tier2_migration_service import run_tier2_reset
        await run_tier2_reset(callback.bot)
        await callback.message.answer(
            "✅ <b>Сброс завершён.</b>\n"
            "Все игроки с классом 2-го Тира ниже 50 уровня сброшены обратно на Тир-1 и уведомлены.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("adm:reset_tier2")
        await callback.message.answer("❌ Ошибка при сбросе. Смотри логи.", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "adm:ban", IsAdmin())
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="ban",
        html_text="🚫 Введи <code>TELEGRAM_ID</code> или <code>TELEGRAM_ID причина</code> (причина — всё после первого пробела).",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:unban", IsAdmin())
async def cb_admin_unban(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="unban",
        html_text="✅ Введи <b>Telegram ID</b> для разбана.",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:clear_inv", IsAdmin())
async def cb_admin_clear_inv(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="clear_inv",
        html_text=(
            "🗑 <b>Очистить инвентарь</b>\n\n"
            "Введи <b>Telegram ID</b> игрока — удалить всё только у него.\n"
            "Или напиши <code>all</code> — удалить предметы <b>у всех игроков</b>.\n\n"
            "⚠️ Это действие <b>необратимо</b>."
        ),
    )
    await callback.answer()


async def _do_wipe_inventory(
    message: Message,
    session: AsyncSession,
    text: str,
    *,
    actor_telegram_id: int,
) -> None:
    """Логика очистки инвентаря: одного игрока или всех."""
    if text.lower() == "all":
        count = await inventory_repo.wipe_all_inventories(session)
        await anticheat_service.log_admin_action(
            session,
            actor_telegram_id=actor_telegram_id,
            target_user_id=None,
            action="admin_wipe_all_inventories",
            message=f"Удалено предметов: {count}",
            payload={"deleted_count": count},
        )
        await session.commit()
        await message.answer(
            f"✅ Инвентари <b>всех игроков</b> очищены. Удалено записей: <b>{count}</b>.",
            parse_mode=ParseMode.HTML,
        )
        return

    if not text.isdigit():
        await message.answer(
            "Нужен числовой <b>Telegram ID</b> или слово <code>all</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    tid = int(text)
    u = await user_repo.get_by_telegram_id(session, tid)
    if u is None:
        await message.answer(f"Нет пользователя <code>{tid}</code>.", parse_mode=ParseMode.HTML)
        return
    ch = await character_repo.get_by_user_id(session, u.id)
    if ch is None:
        await message.answer("У пользователя нет персонажа.", parse_mode=ParseMode.HTML)
        return

    count = await inventory_repo.wipe_inventory(session, int(ch.id))
    await anticheat_service.log_admin_action(
        session,
        actor_telegram_id=actor_telegram_id,
        target_user_id=int(u.id),
        action="admin_wipe_inventory",
        message=f"Удалено предметов: {count}",
        payload={"telegram_id": tid, "character_id": int(ch.id), "deleted_count": count},
    )
    await session.commit()
    await message.answer(
        f"✅ Инвентарь <b>{html.escape(ch.display_name)}</b> (TG <code>{tid}</code>) очищен. "
        f"Удалено записей: <b>{count}</b>.",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "adm:broadcast", IsAdmin())
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _prompt_fsm(
        callback,
        state,
        kind="broadcast",
        html_text="📢 Отправь <b>текст рассылки</b> одним сообщением (поддерживается HTML как в Telegram).",
    )
    await callback.answer()


async def _try_restore_hub_from_state(
    bot,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    mid = data.get("panel_mid")
    cid = data.get("panel_cid")
    if mid is not None and cid is not None:
        try:
            await bot.edit_message_text(
                PANEL_HTML,
                chat_id=int(cid),
                message_id=int(mid),
                parse_mode=ParseMode.HTML,
                reply_markup=admin_panel_keyboard(),
            )
        except TelegramBadRequest:
            pass
    await state.clear()


@router.message(StateFilter(AdminStates.waiting_input), F.text, IsAdmin())
async def admin_fsm_text(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    kind = data.get("admin_kind")
    text = (message.text or "").strip()
    actor_id = message.from_user.id

    async def finish(msg: str, *, ok: bool = True) -> None:
        await _try_restore_hub_from_state(message.bot, state)
        await message.answer(msg, parse_mode=ParseMode.HTML if ok else None)

    try:
        if kind == "custom_title_name":
            nm = text.strip()
            if len(nm) < 1 or len(nm) > 48:
                await message.answer("Название: от 1 до 48 символов. Повтори.")
                return
            await state.update_data(
                admin_kind="custom_title_bonuses",
                custom_title_name=nm,
            )
            await message.answer(
                "Шаг <b>2/2</b>: семь целых чисел через пробел:\n"
                "<code>золото% опыт% СИЛ ЛОВ ИНТ ВЫН УДА</code>\n"
                "Пример: <code>5 0 2 0 0 0 0</code>\n\n"
                "Лимиты: золото% и опыт% — <b>0…30</b>, каждый стат — <b>0…25</b>.",
                parse_mode=ParseMode.HTML,
                reply_markup=admin_cancel_keyboard(),
            )
            return

        if kind == "custom_title_bonuses":
            parts = text.split()
            if len(parts) != 7:
                await message.answer("Нужно ровно <b>7</b> чисел через пробел.", parse_mode=ParseMode.HTML)
                return
            try:
                g, x, sstr, sdex, sint, svit, sluck = (int(p) for p in parts)
            except ValueError:
                await message.answer("Только целые числа.")
                return
            g = max(0, min(30, g))
            x = max(0, min(30, x))
            sstr = max(0, min(25, sstr))
            sdex = max(0, min(25, sdex))
            sint = max(0, min(25, sint))
            svit = max(0, min(25, svit))
            sluck = max(0, min(25, sluck))
            cid = int(data.get("custom_title_cid") or 0)
            pg = int(data.get("custom_title_pg") or 0)
            nm = str(data.get("custom_title_name") or "").strip()
            if not nm:
                await message.answer("Сессия сброшена. Начни снова с карточки игрока.")
                await _try_restore_hub_from_state(message.bot, state)
                return
            ch = await character_repo.get_by_id(session, cid)
            if ch is None:
                await message.answer("Персонаж не найден.")
                await _try_restore_hub_from_state(message.bot, state)
                return
            ok_grant, err_or_name, new_key = title_service.admin_grant_custom_title(
                ch,
                name_ru=nm,
                gold_bonus_pct=g,
                xp_bonus_pct=x,
                stat_str=sstr,
                stat_dex=sdex,
                stat_int=sint,
                stat_vit=svit,
                stat_luck=sluck,
            )
            if not ok_grant:
                await message.answer(err_or_name)
                return
            await anticheat_service.log_admin_action(
                session,
                actor_telegram_id=int(actor_id),
                target_user_id=int(ch.user_id),
                action="admin_grant_custom_title",
                message=f"{new_key}:{nm}",
                payload={
                    "character_id": cid,
                    "title_key": new_key,
                    "name_ru": nm,
                    "bonuses": {
                        "gold_pct": g,
                        "xp_pct": x,
                        "str": sstr,
                        "dex": sdex,
                        "int": sint,
                        "vit": svit,
                        "luck": sluck,
                    },
                },
            )
            await session.commit()
            from services import gacha_broadcast_service

            u = await user_repo.get_by_id(session, int(ch.user_id))
            uname = (u.username or "").strip() if u is not None else ""
            dn = html.escape((ch.display_name or "?").strip() or "?")
            tnh = html.escape(nm)
            announce = f"🏅 Ранкер <b>{dn}</b>"
            if uname:
                announce += f" (@{html.escape(uname)})"
            announce += f" награждён титулом <b>{tnh}</b> от башни за усердный труд!"
            await gacha_broadcast_service.send_tower_community_announcement(
                message.bot,
                session,
                character=ch,
                html_text=announce,
            )
            await state.clear()
            body, ch2 = await _admin_player_snapshot_html(session, cid)
            if body is not None and ch2 is not None:
                await message.answer(
                    _truncate_html(body),
                    parse_mode=ParseMode.HTML,
                    reply_markup=admin_player_snapshot_keyboard(character_id=cid, return_page=pg),
                )
            await message.answer(
                f"✅ Персональный титул выдан: <b>{html.escape(nm)}</b> (ключ <code>{html.escape(new_key)}</code>).",
                parse_mode=ParseMode.HTML,
            )
            return

        if kind == "user":
            if not text.isdigit():
                await message.answer("Нужен числовой Telegram ID.")
                return
            await _answer_user_lookup(message, session, int(text))
            await _try_restore_hub_from_state(message.bot, state)
            return

        if kind == "level_tid":
            if not text.isdigit():
                await message.answer("Нужен числовой Telegram ID.")
                return
            tid = int(text)
            u = await user_repo.get_by_telegram_id(session, tid)
            if u is None:
                await message.answer(f"Нет пользователя <code>{tid}</code>.", parse_mode=ParseMode.HTML)
                await _try_restore_hub_from_state(message.bot, state)
                return
            ch = await character_repo.get_by_user_id(session, u.id)
            if ch is None:
                await message.answer("У пользователя нет персонажа.", parse_mode=ParseMode.HTML)
                await _try_restore_hub_from_state(message.bot, state)
                return
            body, ch2 = await _admin_player_snapshot_html(session, int(ch.id))
            if body is None or ch2 is None:
                await message.answer("Не удалось собрать карточку.")
                await _try_restore_hub_from_state(message.bot, state)
                return
            await message.answer(
                _truncate_html(body),
                parse_mode=ParseMode.HTML,
                reply_markup=admin_player_snapshot_keyboard(character_id=int(ch.id), return_page=0),
            )
            await _try_restore_hub_from_state(message.bot, state)
            await message.answer(
                "Карточка выше: меняй уровень кнопками <b>+1 / +5 / +10</b> или <b>до 25 / 50 / 100</b>.",
                parse_mode=ParseMode.HTML,
            )
            return

        if kind == "give":
            parts = text.split()
            if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
                await message.answer("Формат: <code>ID СУММА</code>", parse_mode=ParseMode.HTML)
                return
            await _do_give_gold(message, session, int(parts[0]), int(parts[1]), actor_telegram_id=actor_id)
            await _try_restore_hub_from_state(message.bot, state)
            return

        if kind == "ban":
            parts = text.split(maxsplit=1)
            if not parts or not parts[0].isdigit():
                await message.answer("Сначала числовой Telegram ID.")
                return
            tid = int(parts[0])
            reason = parts[1].strip() if len(parts) > 1 else None
            u = await user_repo.get_by_telegram_id(session, tid)
            ok = await user_repo.set_ban_by_telegram_id(session, tid, banned=True, reason=reason)
            if ok and u is not None:
                await anticheat_service.log_admin_action(
                    session,
                    actor_telegram_id=actor_id,
                    target_user_id=u.id,
                    action="admin_ban",
                    message=reason,
                    payload={"telegram_id": tid},
                )
            await session.commit()
            await finish(
                f"Пользователь <code>{tid}</code> забанен." if ok else f"Не найден <code>{tid}</code>.",
            )
            return

        if kind == "unban":
            if not text.isdigit():
                await message.answer("Нужен числовой Telegram ID.")
                return
            tid = int(text)
            u = await user_repo.get_by_telegram_id(session, tid)
            ok = await user_repo.set_ban_by_telegram_id(session, tid, banned=False, reason=None)
            if ok and u is not None:
                await anticheat_service.log_admin_action(
                    session,
                    actor_telegram_id=actor_id,
                    target_user_id=u.id,
                    action="admin_unban",
                    message=None,
                    payload={"telegram_id": tid},
                )
            await session.commit()
            await finish(
                f"Пользователь <code>{tid}</code> разбанен." if ok else f"Не найден <code>{tid}</code>.",
            )
            return

        if kind == "broadcast":
            await message.answer(f"Рассылка запущена…")
            ok_n, fail_n = await _run_broadcast(message, session, text, actor_telegram_id=actor_id)
            await _try_restore_hub_from_state(message.bot, state)
            await message.answer(f"Готово: доставлено ~<b>{ok_n}</b>, ошибок <b>{fail_n}</b>.")
            return

        if kind == "give_runes":
            parts = text.split()
            if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
                await message.answer("Формат: <code>ID КОЛИЧЕСТВО</code>", parse_mode=ParseMode.HTML)
                return
            tid2, amt2 = int(parts[0]), int(parts[1])
            if amt2 <= 0 or amt2 > 999_999:
                await message.answer("Количество рун: 1…999 999.")
                return
            u2 = await user_repo.get_by_telegram_id(session, tid2)
            ch2 = await character_repo.get_by_user_id(session, u2.id) if u2 else None
            if ch2 is None:
                await finish(f"Персонаж <code>{tid2}</code> не найден.", ok=False)
                return
            ch2.rune_stones = int(ch2.rune_stones) + amt2
            await anticheat_service.log_admin_action(
                session, actor_telegram_id=actor_id, target_user_id=int(u2.id),
                action="admin_give_runes", message=f"+{amt2}",
                payload={"telegram_id": tid2, "amount": amt2},
            )
            await session.commit()
            await finish(f"Начислено <b>{amt2}</b> 💎 руней игроку <code>{html.escape(ch2.display_name)}</code>.")
            return

        if kind == "heal":
            if not text.isdigit():
                await message.answer("Нужен числовой Telegram ID.")
                return
            u3 = await user_repo.get_by_telegram_id(session, int(text))
            ch3 = await character_repo.get_by_user_id(session, u3.id) if u3 else None
            if ch3 is None:
                await finish(f"Персонаж <code>{text}</code> не найден.", ok=False)
                return
            ch3.hp_current = int(ch3.hp_max)
            ch3.mp_current = int(ch3.mp_max)
            await session.commit()
            await finish(f"HP/MP игрока <b>{html.escape(ch3.display_name)}</b> полностью восстановлены.")
            return

        if kind == "stamina":
            if not text.isdigit():
                await message.answer("Нужен числовой Telegram ID.")
                return
            from config import settings as _settings
            u4 = await user_repo.get_by_telegram_id(session, int(text))
            ch4 = await character_repo.get_by_user_id(session, u4.id) if u4 else None
            if ch4 is None:
                await finish(f"Персонаж <code>{text}</code> не найден.", ok=False)
                return
            ch4.stamina = _settings.MAX_STAMINA
            await session.commit()
            await finish(f"Стамина игрока <b>{html.escape(ch4.display_name)}</b> установлена на {_settings.MAX_STAMINA}.")
            return

        if kind == "clear_inv":
            await _do_wipe_inventory(message, session, text, actor_telegram_id=actor_id)
            await _try_restore_hub_from_state(message.bot, state)
            return

        if kind == "promo_cmd":
            raw = text
            if raw.startswith("/admin"):
                raw = raw[6:].strip()
            promo_parts = raw.split()
            if not promo_parts:
                await message.answer("Пусто. Пример: <code>promo list</code>", parse_mode=ParseMode.HTML)
                return
            if promo_parts[0].lower() != "promo":
                promo_parts = ["promo", *promo_parts]
            await handle_admin_promo(
                message,
                session,
                promo_parts,
                actor_telegram_id=actor_id,
            )
            await _try_restore_hub_from_state(message.bot, state)
            return

        await message.answer("Состояние панели сброшено. Отправь <code>/admin</code>.", parse_mode=ParseMode.HTML)
        await state.clear()

    except Exception:
        logger.exception("admin_fsm_text")
        await state.clear()
        await message.answer("Ошибка.")


# ——— Старые команды ———


@router.message(Command("admin_stats"), IsAdmin())
async def cmd_admin_stats(message: Message, session: AsyncSession) -> None:
    try:
        stats = await _dashboard_stats(session)
        await message.answer(panel.format_dashboard_html(stats), parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("admin_stats")
        await message.answer("Ошибка запроса к БД.")


@router.message(Command("admin_ban"), IsAdmin())
async def cmd_admin_ban(message: Message, session: AsyncSession, command: CommandObject) -> None:
    if message.from_user is None:
        return
    args = (command.args or "").split(maxsplit=1)
    if not args or not args[0].isdigit():
        await message.answer("Использование: <code>/admin_ban TELEGRAM_ID [причина]</code>")
        return
    tid = int(args[0])
    reason = args[1].strip() if len(args) > 1 else None
    try:
        u = await user_repo.get_by_telegram_id(session, tid)
        ok = await user_repo.set_ban_by_telegram_id(session, tid, banned=True, reason=reason)
        if ok and u is not None:
            await anticheat_service.log_admin_action(
                session,
                actor_telegram_id=message.from_user.id,
                target_user_id=u.id,
                action="admin_ban",
                message=reason,
                payload={"telegram_id": tid},
            )
        await session.commit()
        if ok:
            await message.answer(f"Пользователь <code>{tid}</code> забанен.")
        else:
            await message.answer(f"Не найден telegram_id <code>{tid}</code>.")
    except Exception:
        logger.exception("admin_ban")
        await message.answer("Ошибка БД.")


@router.message(Command("admin_unban"), IsAdmin())
async def cmd_admin_unban(message: Message, session: AsyncSession, command: CommandObject) -> None:
    if message.from_user is None:
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: <code>/admin_unban TELEGRAM_ID</code>")
        return
    tid = int(arg)
    try:
        u = await user_repo.get_by_telegram_id(session, tid)
        ok = await user_repo.set_ban_by_telegram_id(session, tid, banned=False, reason=None)
        if ok and u is not None:
            await anticheat_service.log_admin_action(
                session,
                actor_telegram_id=message.from_user.id,
                target_user_id=u.id,
                action="admin_unban",
                message=None,
                payload={"telegram_id": tid},
            )
        await session.commit()
        if ok:
            await message.answer(f"Пользователь <code>{tid}</code> разбанен.")
        else:
            await message.answer(f"Не найден telegram_id <code>{tid}</code>.")
    except Exception:
        logger.exception("admin_unban")
        await message.answer("Ошибка БД.")


@router.message(Command("admin_broadcast"), IsAdmin())
async def cmd_admin_broadcast(message: Message, session: AsyncSession, command: CommandObject) -> None:
    if message.from_user is None:
        return
    text = (command.args or "").strip()
    if not text:
        await message.answer("Использование: <code>/admin_broadcast текст сообщения</code>")
        return
    ids = await user_repo.list_telegram_ids_for_broadcast(session)
    await message.answer(f"Рассылка <b>{len(ids)}</b> получателям…")
    ok, fail = await _run_broadcast(message, session, text, actor_telegram_id=message.from_user.id)
    await message.answer(f"Готово: доставлено ~<b>{ok}</b>, ошибок <b>{fail}</b>.")


@router.message(F.text.startswith("/admin"), IsAdmin())
async def admin_help(message: Message) -> None:
    """Подсказка по опечаткам /admin_*."""
    first = (message.text or "").split(maxsplit=1)[0]
    if first in (
        "/admin_stats",
        "/admin_ban",
        "/admin_unban",
        "/admin_broadcast",
        "/admin",
        "/settings",
        "/настройки",
    ):
        return
    await message.answer(
        "🔧 <b>Админ</b>\n"
        "<code>/admin</code> — панель с кнопками\n"
        "<code>/admin_stats</code> — сводка\n"
        "<code>/admin_ban ID [причина]</code>\n"
        "<code>/admin_unban ID</code>\n"
        "<code>/admin_broadcast текст</code>",
        parse_mode=ParseMode.HTML,
    )
