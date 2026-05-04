"""
Мастерская (ремесло): wsp:* и городские заказы wso:* (хаб заказов — этаж города игроков).
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.i18n import get_locale
from bot.keyboards.menu_kb import menu_nav_button_row
from bot.keyboards.workshop_kb import (
    city_workshop_orders_keyboard,
    workshop_main_keyboard,
    workshop_prof_keyboard,
    workshop_queue_keyboard,
)
from db.repository import character_repo, user_repo
from db.repository import workshop_order_repo
from game.crafting.craft_catalog import catalog_text_for_profession
from game.crafting.recipes_data import (
    PROF_ALCHEMIST,
    PROF_BLACKSMITH,
    PROF_JEWELER,
    get_recipe_by_id,
    recipes_for_profession,
)
from game.crafting.workshop_constants import WORKSHOP_ORDERS_HUB_FLOOR
from game.crafting.workshop_meta import get_workshop_state, known_blueprint_ids
from services import workshop_order_service, workshop_service
from services.workshop_leaderboard_service import cached_leaderboard_html
from db.models.app_global import AppGlobal

router = Router(name="workshop")


async def _char(session: AsyncSession, query: CallbackQuery):
    if query.from_user is None:
        return None
    user = await user_repo.get_by_telegram_id(session, query.from_user.id)
    if user is None or user.is_banned:
        await query.answer("Нет доступа.", show_alert=True)
        return None
    char = await character_repo.get_by_user_id(session, user.id)
    if char is None:
        await query.answer("Нет персонажа.", show_alert=True)
        return None
    return char


def _recipe_label(r: dict, known: set[str]) -> str:
    rid = str(r.get("id", ""))
    name = str(r.get("name_ru", rid))
    bp = bool(r.get("requires_blueprint"))
    lock = "🔒 " if bp and rid not in known else ""
    return f"{lock}{name}"


def _paginate(lst: list, page: int, per_page: int = 8) -> tuple[list, int]:
    p = max(0, int(page))
    start = p * per_page
    return lst[start : start + per_page], p


async def render_workshop_hub(query: CallbackQuery, session: AsyncSession) -> None:
    """Текст и клавиатура хаба мастерской (меню и дом)."""
    char = await _char(session, query)
    if char is None or query.message is None:
        return
    loc = get_locale(char, query.from_user.language_code if query.from_user else None)
    lines = [
        "🔧 <b>Мастерская</b>",
        "<i>Ремесленные профессии, очередь и станки. Дом — быт и шахта.</i>",
        "",
        *workshop_service.profession_summary_lines(char, loc),
        "",
        "Выбери профессию или очередь.",
    ]
    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=workshop_main_keyboard(loc),
        parse_mode=ParseMode.HTML,
    )
    await query.answer()


@router.callback_query(F.data == "mnu:wsp")
async def menu_workshop_open(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        await render_workshop_hub(query, session)
    except Exception:
        logger.exception("mnu:wsp")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:hub")
async def workshop_hub(query: CallbackQuery, session: AsyncSession) -> None:
    await menu_workshop_open(query, session)


@router.callback_query(F.data.startswith("wsp:prof:"))
async def workshop_prof(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        prof = str(query.data.split(":")[2])
        loc = get_locale(char, query.from_user.language_code if query.from_user else None)
        known = known_blueprint_ids(char)
        recipes = recipes_for_profession(prof)
        recipe_rows = [(str(r.get("id")), _recipe_label(r, known)) for r in recipes]
        chunk, page = _paginate(recipe_rows, 0)
        title = {"blacksmith": "⚒️ Кузнец", "alchemist": "⚗️ Алхимик", "jeweler": "💎 Ювелир"}.get(
            prof,
            prof,
        )
        lines = [
            f"{title}",
            "<i>🔒 — нужен чертёж. Рецепты с таймером — только здесь (не в городской кузне).</i>",
            "",
        ]
        await query.message.edit_text(
            "\n".join(lines),
            reply_markup=workshop_prof_keyboard(prof, page=page, recipe_rows=chunk),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:prof")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:profpage:"))
async def workshop_prof_page(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        _, _, prof, p_s = query.data.split(":", 3)
        page = int(p_s)
        known = known_blueprint_ids(char)
        recipes = recipes_for_profession(prof)
        recipe_rows = [(str(r.get("id")), _recipe_label(r, known)) for r in recipes]
        chunk, page = _paginate(recipe_rows, page)
        title = {"blacksmith": "⚒️ Кузнец", "alchemist": "⚗️ Алхимик", "jeweler": "💎 Ювелир"}.get(
            prof,
            prof,
        )
        lines = [f"{title}", ""]
        await query.message.edit_text(
            "\n".join(lines),
            reply_markup=workshop_prof_keyboard(prof, page=page, recipe_rows=chunk),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:profpage")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:start:"))
async def workshop_start(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        rid = str(query.data.split(":")[2])
        ok, lines = await workshop_service.try_start_craft(session, char, rid, qty=1)
        await session.commit()
        if not ok:
            await query.answer((lines[0] if lines else "Нельзя.")[:200], show_alert=True)
            return
        body = "\n".join(lines)
        await query.message.edit_text(
            f"🔧 <b>Мастерская</b>\n\n{body}",
            reply_markup=workshop_main_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await query.answer("Запущено.")
    except Exception:
        logger.exception("wsp:start")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:queue")
async def workshop_queue(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        ws = get_workshop_state(char)
        crafts = list(ws.get("active_crafts") or [])
        now = datetime.now(UTC)
        entries: list[tuple[str, str, bool, bool]] = []
        for c in crafts:
            sid = str(c.get("slot_id"))
            rid = str(c.get("recipe_id"))
            r = get_recipe_by_id(rid)
            nm = str(r.get("name_ru", rid)) if r else rid
            raw_ready = str(c.get("ready_at") or "")
            try:
                rdt = datetime.fromisoformat(raw_ready.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                rdt = now
            ready = rdt <= now
            lab = f"✅ Забрать: {nm}" if ready else f"⏳ {nm} до {rdt.strftime('%H:%M')} UTC"
            entries.append((sid, lab, ready, True))
        if not entries:
            text = "📜 <b>Очередь пуста.</b>"
            kb = workshop_main_keyboard()
        else:
            text = "📜 <b>Активные работы</b>\n\n<i>Готово — «Забрать». Не готово — ускорение рунным камнем.</i>"
            kb = workshop_queue_keyboard(entries)
        await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        await query.answer()
    except Exception:
        logger.exception("wsp:queue")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:claim:"))
async def workshop_claim(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        sid = str(query.data.split(":")[2])
        ok, lines = await workshop_service.try_claim_craft(session, char, sid)
        await session.commit()
        if not ok:
            await query.answer((lines[0] if lines else "Нельзя.")[:200], show_alert=True)
            return
        await query.message.edit_text(
            "\n".join(lines),
            reply_markup=workshop_main_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await query.answer("Забрано.")
    except Exception:
        logger.exception("wsp:claim")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:acc:"))
async def workshop_acc(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        sid = str(query.data.split(":")[2])
        ok, lines = await workshop_service.try_accelerate(session, char, sid)
        await session.commit()
        await query.answer((lines[0] if lines else "Ок.")[:200], show_alert=not ok)
        if ok:
            await workshop_queue(query, session)
    except Exception:
        logger.exception("wsp:acc")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:upg:"))
async def workshop_upg(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        prof = str(query.data.split(":")[2])
        ok, lines = await workshop_service.try_upgrade_station(session, char, prof)
        await session.commit()
        await query.answer((lines[0] if lines else "Готово.")[:200], show_alert=True)
    except Exception:
        logger.exception("wsp:upg")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:wait:"))
async def workshop_wait(query: CallbackQuery) -> None:
    await query.answer("Ещё не готово.", show_alert=True)


@router.callback_query(F.data == "wsp:noop")
async def workshop_noop(query: CallbackQuery) -> None:
    await query.answer()


@router.callback_query(F.data == "wsp:lb")
async def workshop_lb(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        row = await session.get(AppGlobal, 1)
        payload = dict(row.payload or {}) if row is not None else {}
        text = cached_leaderboard_html(payload)
        await query.message.edit_text(
            f"🏆 <b>Рейтинг</b>\n\n{text}",
            reply_markup=workshop_main_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:lb")
        await query.answer("Ошибка.", show_alert=True)


# ---- Городские заказы (этаж хаба) ----


@router.callback_query(F.data.startswith("wsp:cat:"))
async def workshop_catalog(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        tail = str(query.data).split(":", 2)[2] if ":" in str(query.data) else "menu"
        if tail == "menu":
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="⚒️ Кузнец", callback_data="wsp:cat:blacksmith"),
                        InlineKeyboardButton(text="⚗️ Алхимик", callback_data="wsp:cat:alchemist"),
                    ],
                    [InlineKeyboardButton(text="💎 Ювелир", callback_data="wsp:cat:jeweler")],
                    [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
                    menu_nav_button_row(),
                ],
            )
            await query.message.edit_text(
                "📖 <b>Справочник крафта</b>\n\n<i>По профессиям: что выходит и из каких материалов.</i>",
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            await query.answer()
            return
        if tail in (PROF_BLACKSMITH, PROF_ALCHEMIST, PROF_JEWELER):
            body = catalog_text_for_profession(tail)
            await query.message.edit_text(
                body[:3900],
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⬅ К профессиям", callback_data="wsp:cat:menu")],
                        [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
                        menu_nav_button_row(),
                    ],
                ),
                parse_mode=ParseMode.HTML,
            )
            await query.answer()
            return
        await query.answer()
    except Exception:
        logger.exception("wsp:cat")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:open:"))
async def wso_open(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        fl = int(query.data.split(":")[2])
        if int(char.floor_number) != fl:
            await query.answer("Ты не в этом городе.", show_alert=True)
            return
        crafter = workshop_order_service.can_use_city_workshop_orders(char)
        hint = (
            "Ты можешь принимать заказы как кузнец (≥10)."
            if crafter
            else "Кузнец ≥10 на этом этаже может брать заказы."
        )
        await query.message.edit_text(
            f"📋 <b>Городская кузница — заказы</b>\n\n{html.escape(hint)}",
            reply_markup=city_workshop_orders_keyboard(floor_number=fl),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("wso:open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:list:"))
async def wso_list(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        fl = int(query.data.split(":")[2])
        rows_db = await workshop_order_repo.list_posted(session, limit=12)
        crafter = workshop_order_service.can_use_city_workshop_orders(char)
        lines = ["📋 <b>Открытые заказы</b>"]
        if not rows_db:
            lines.append("<i>Нет открытых заказов.</i>")
        else:
            for o in rows_db:
                rid = str(o.get("recipe_id"))
                r = get_recipe_by_id(rid)
                nm = html.escape(str(r.get("name_ru", rid)) if r else rid)
                escrow = int(o.get("escrow_gold") or 0)
                oid = int(o.get("id") or 0)
                lines.append(f"· #{oid} {nm} — {escrow}💰")
        my_jobs = await workshop_order_repo.list_for_crafter(session, int(char.id))
        if my_jobs:
            lines.append("")
            lines.append("<b>Твои заказы в работе:</b>")
            for o in my_jobs:
                rid = str(o.get("recipe_id"))
                r = get_recipe_by_id(rid)
                nm = html.escape(str(r.get("name_ru", rid)) if r else rid)
                oid = int(o.get("id") or 0)
                lines.append(f"· #{oid} {nm} — <i>сдать результат</i>")
        kb_rows: list[list[InlineKeyboardButton]] = []
        if crafter:
            for o in rows_db:
                oid = int(o.get("id") or 0)
                kb_rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"✋ Принять #{oid}",
                            callback_data=f"wso:take:{fl}:{oid}",
                        ),
                    ],
                )
        for o in my_jobs:
            oid = int(o.get("id") or 0)
            kb_rows.append(
                [
                    InlineKeyboardButton(
                        text=f"✅ Сдать заказ #{oid}",
                        callback_data=f"wso:done:{fl}:{oid}",
                    ),
                ],
            )
        kb_rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"wso:open:{fl}")])
        kb_rows.append(menu_nav_button_row())
        await query.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
            parse_mode=ParseMode.HTML,
        )
        await query.answer()
    except Exception:
        logger.exception("wso:list")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:take:"))
async def wso_take(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        _, _, fl_s, oid_s = query.data.split(":", 3)
        int(fl_s)
        oid = int(oid_s)
        ok, msg = await workshop_order_service.try_accept_order(session, char, oid)
        await session.commit()
        await query.answer(("Заказ принят." if ok else msg)[:200], show_alert=True)
    except Exception:
        logger.exception("wso:take")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:new:"))
async def wso_new(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        fl = int(query.data.split(":")[2])
        if not workshop_order_service.can_post_order(char):
            await query.answer(
                f"Заказы только в городе на {WORKSHOP_ORDERS_HUB_FLOOR} этаже.",
                show_alert=True,
            )
            return
        rid = "weak_blade_blank"
        sug = workshop_order_service.suggested_escrow_gold(char, rid)
        ok, msg = await workshop_order_service.try_create_order(session, char, rid, sug)
        await session.commit()
        await query.answer(("Размещено." if ok else msg)[:200], show_alert=True)
        if ok:
            await query.message.edit_text(
                msg,
                reply_markup=city_workshop_orders_keyboard(floor_number=fl),
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception("wso:new")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:done:"))
async def wso_done(query: CallbackQuery, session: AsyncSession) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        _, _, fl_s, oid_s = query.data.split(":", 3)
        fl = int(fl_s)
        oid = int(oid_s)
        if int(char.floor_number) != fl:
            await query.answer("Ты не на этом этаже.", show_alert=True)
            return
        ok, msg = await workshop_order_service.try_complete_order(session, char, oid)
        await session.commit()
        if ok:
            await query.message.edit_text(
                msg,
                reply_markup=city_workshop_orders_keyboard(floor_number=fl),
                parse_mode=ParseMode.HTML,
            )
        await query.answer(("Готово." if ok else msg)[:200], show_alert=not ok)
    except Exception:
        logger.exception("wso:done")
        await query.answer("Ошибка.", show_alert=True)

