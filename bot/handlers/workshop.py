"""
Мастерская (ремесло): wsp:* и городские заказы wso:* (хаб заказов — этаж города игроков).
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
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
from db.models.character import Character
from db.repository import character_repo, inventory_repo, user_repo
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
from game.items.craft_resources import RESOURCE_DEFS, total_craft_resource_in_bag
from services import workshop_order_service, workshop_service
from services.workshop_leaderboard_service import cached_leaderboard_html
from db.models.app_global import AppGlobal

from bot.utils.game_art import menu_workshop_orders_photo_path, menu_workshop_photo_path
from bot.utils.game_ui import push_game_ui

router = Router(name="workshop")


async def _workshop_ui(
    state: FSMContext,
    query: CallbackQuery,
    character: Character,
    text: str,
    reply_markup,
    *,
    city_orders: bool = False,
) -> None:
    if query.message is None or query.bot is None:
        return
    pp = menu_workshop_orders_photo_path() if city_orders else menu_workshop_photo_path()
    await push_game_ui(
        state,
        query.bot,
        chat_id=query.message.chat.id,
        text=text,
        reply_markup=reply_markup,
        target_message=query.message,
        photo_path=pp,
        character=character,
    )

PROF_TITLE_RU = {
    "blacksmith": "⚒️ Кузница",
    "alchemist": "⚗️ Лаборатория",
    "jeweler": "💎 Ювелирная",
}


def _recipes_unlocked_for_player(character: Character, prof: str) -> list[dict]:
    """Только рецепты с изученным чертежом (если требуется) или без требования чертежа."""
    known = known_blueprint_ids(character)
    out: list[dict] = []
    for r in recipes_for_profession(prof):
        if bool(r.get("requires_blueprint")):
            rid = str(r.get("id") or "")
            if rid not in known:
                continue
        out.append(r)
    out.sort(
        key=lambda r: (int(r.get("min_profession_level", 1)), str(r.get("name_ru", r.get("id", "")))),
    )
    return out


def _format_craft_resource_line(bag: list, craft_cost: dict[str, int]) -> str:
    if not craft_cost:
        return "<i>Ремесленных материалов не требуется.</i>"
    parts: list[str] = []
    for rid, need in sorted(craft_cost.items(), key=lambda x: str(x[0])):
        have = total_craft_resource_in_bag(bag, str(rid))
        ne = int(need)
        label = str((RESOURCE_DEFS.get(str(rid)) or {}).get("name_ru") or rid)
        ok = "✅" if have >= ne else "❌"
        parts.append(f"{ok} {html.escape(label)}: {have}/{ne}")
    return "\n".join(parts)


async def _recipe_preview_html(session: AsyncSession, char: Character, prof: str, recipe_id: str) -> str | None:
    r = get_recipe_by_id(str(recipe_id))
    if r is None or str(r.get("profession")) != prof:
        return None
    known = known_blueprint_ids(char)
    if bool(r.get("requires_blueprint")) and str(r.get("id") or "") not in known:
        return None
    bag = await inventory_repo.list_bag_items(session, char.id)
    craft_cost = {str(k): int(v) for k, v in (r.get("craft_cost") or {}).items()}
    secs = int(r.get("craft_seconds") or 300)
    mins = max(1, (secs + 59) // 60)
    ws = get_workshop_state(char)
    plv = int(ws["prof_levels"].get(prof, 1))
    st_lv = int(ws["stations"].get(prof, 1))
    need_prof = int(r.get("min_profession_level", 1))
    need_st = int(r.get("min_station_level", 1))
    need_ch = int(r.get("min_character_level", 1))
    res_block = _format_craft_resource_line(bag, craft_cost)
    name = html.escape(str(r.get("name_ru", recipe_id)))
    res_item = r.get("result") or {}
    res_name = html.escape(str(res_item.get("name", "—")))
    bp_note = "\n<i>Нужен изученный чертёж.</i>" if r.get("requires_blueprint") else ""
    return (
        f"📋 <b>{name}</b>\n"
        f"<i>Результат:</i> {res_name}{bp_note}\n\n"
        f"⏱ <b>Время создания:</b> {mins} мин ({secs} сек)\n"
        f"📊 <b>Требования:</b> проф. {need_prof}+ (у тебя {plv}), "
        f"станок {need_st}+ (у тебя {st_lv}), герой ур. {need_ch}+\n\n"
        f"<b>Материалы в сумке:</b>\n{res_block}"
    )


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


def _paginate(lst: list, page: int, per_page: int = 8) -> tuple[list, int]:
    p = max(0, int(page))
    start = p * per_page
    return lst[start : start + per_page], p


async def render_workshop_hub(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
    await _workshop_ui(state, query, char, "\n".join(lines), workshop_main_keyboard(loc))
    await query.answer()


@router.callback_query(F.data == "mnu:wsp")
async def menu_workshop_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        await render_workshop_hub(query, session, state)
    except Exception:
        logger.exception("mnu:wsp")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:hub")
async def workshop_hub(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await menu_workshop_open(query, session, state)


@router.callback_query(F.data.startswith("wsp:prof:"))
async def workshop_prof(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        prof = str(query.data.split(":")[2])
        title = PROF_TITLE_RU.get(prof, prof)
        recipes = _recipes_unlocked_for_player(char, prof)
        if not recipes:
            await _workshop_ui(
                state,
                query,
                char,
                f"{title}\n\n<i>Нет изученных рецептов: открой чертежи в гаче или с наград.</i>",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
                        menu_nav_button_row(),
                    ],
                ),
            )
            await query.answer()
            return
        recipe_rows = [(str(r.get("id")), str(r.get("name_ru", r.get("id", "")))) for r in recipes]
        chunk, page = _paginate(recipe_rows, 0)
        lines = [
            f"{title}",
            "<i>Нажми рецепт — откроется карточка: ресурсы, время, требования. «Создать» — в очередь.</i>",
            "<i>Только рецепты с открытым чертежом (где требуется). Сортировка: по требуемому уровню профессии.</i>",
            "",
        ]
        await _workshop_ui(
            state,
            query,
            char,
            "\n".join(lines),
            workshop_prof_keyboard(prof, page=page, recipe_rows=chunk, total_count=len(recipe_rows)),
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:prof")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:profpage:"))
async def workshop_prof_page(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        _, _, prof, p_s = query.data.split(":", 3)
        page = int(p_s)
        title = PROF_TITLE_RU.get(prof, prof)
        recipes = _recipes_unlocked_for_player(char, prof)
        if not recipes:
            await _workshop_ui(
                state,
                query,
                char,
                f"{title}\n\n<i>Нет изученных рецептов.</i>",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
                        menu_nav_button_row(),
                    ],
                ),
            )
            await query.answer()
            return
        recipe_rows = [(str(r.get("id")), str(r.get("name_ru", r.get("id", "")))) for r in recipes]
        chunk, page = _paginate(recipe_rows, page)
        lines = [f"{title}", ""]
        await _workshop_ui(
            state,
            query,
            char,
            "\n".join(lines),
            workshop_prof_keyboard(
                prof,
                page=page,
                recipe_rows=chunk,
                total_count=len(recipe_rows),
            ),
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:profpage")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:rcp:"))
async def workshop_recipe_card(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        try:
            _, _, prof, rid = query.data.split(":", 3)
        except ValueError:
            await query.answer()
            return
        body = await _recipe_preview_html(session, char, prof, rid)
        if body is None:
            await query.answer("Рецепт недоступен.", show_alert=True)
            return
        title = PROF_TITLE_RU.get(prof, prof)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔨 Создать", callback_data=f"wsp:start:{rid}")],
                [InlineKeyboardButton(text="⬅ К списку рецептов", callback_data=f"wsp:prof:{prof}")],
                menu_nav_button_row(),
            ],
        )
        await _workshop_ui(state, query, char, f"{title}\n\n{body}", kb)
        await query.answer()
    except Exception:
        logger.exception("wsp:rcp")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:start:"))
async def workshop_start(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await _workshop_ui(
            state,
            query,
            char,
            f"🔧 <b>Мастерская</b>\n\n{body}",
            workshop_main_keyboard(),
        )
        await query.answer("Запущено.")
    except Exception:
        logger.exception("wsp:start")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:queue")
async def workshop_queue(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        ws = get_workshop_state(char)
        crafts = list(ws.get("active_crafts") or [])
        now = datetime.now(UTC)
        entries: list[tuple[str, str, bool]] = []
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
            entries.append((sid, lab, ready))
        if not entries:
            text = "📜 <b>Очередь пуста.</b>"
            kb = workshop_main_keyboard()
        else:
            text = "📜 <b>Активные работы</b>\n\n<i>Готово — «Забрать». Остальное ждёт таймер.</i>"
            kb = workshop_queue_keyboard(entries)
        await _workshop_ui(state, query, char, text, kb)
        await query.answer()
    except Exception:
        logger.exception("wsp:queue")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:claim:"))
async def workshop_claim(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await _workshop_ui(
            state,
            query,
            char,
            "\n".join(lines),
            workshop_main_keyboard(),
        )
        await query.answer("Забрано.")
    except Exception:
        logger.exception("wsp:claim")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:acc:"))
async def workshop_acc_disabled(query: CallbackQuery) -> None:
    await query.answer("Ускорение рунным камнем отключено.", show_alert=True)


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
async def workshop_lb(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        row = await session.get(AppGlobal, 1)
        payload = dict(row.payload or {}) if row is not None else {}
        text = cached_leaderboard_html(payload)
        await _workshop_ui(
            state,
            query,
            char,
            f"🏆 <b>Рейтинг</b>\n\n{text}",
            workshop_main_keyboard(),
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:lb")
        await query.answer("Ошибка.", show_alert=True)


# ---- Городские заказы (этаж хаба) ----


@router.callback_query(F.data.startswith("wsp:cat:"))
async def workshop_catalog(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        tail = str(query.data).split(":", 2)[2] if ":" in str(query.data) else "menu"
        if tail == "menu":
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="⚒️ Кузница", callback_data="wsp:cat:blacksmith"),
                        InlineKeyboardButton(text="⚗️ Лаборатория", callback_data="wsp:cat:alchemist"),
                    ],
                    [InlineKeyboardButton(text="💎 Ювелирная", callback_data="wsp:cat:jeweler")],
                    [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
                    menu_nav_button_row(),
                ],
            )
            await _workshop_ui(
                state,
                query,
                char,
                "📖 <b>Справочник крафта</b>\n\n<i>По профессиям: что выходит и из каких материалов.</i>",
                kb,
            )
            await query.answer()
            return
        if tail in (PROF_BLACKSMITH, PROF_ALCHEMIST, PROF_JEWELER):
            body = catalog_text_for_profession(tail)
            if len(body) > 3800:
                cut = body.rfind("\n", 0, 3600)
                if cut < 500:
                    cut = 3600
                body = body[:cut] + "\n\n<i>… список обрезан (слишком длинный).</i>"
            await _workshop_ui(
                state,
                query,
                char,
                body,
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⬅ К профессиям", callback_data="wsp:cat:menu")],
                        [InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")],
                        menu_nav_button_row(),
                    ],
                ),
            )
            await query.answer()
            return
        await query.answer()
    except Exception:
        logger.exception("wsp:cat")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:open:"))
async def wso_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await _workshop_ui(
            state,
            query,
            char,
            f"📋 <b>Городская кузница — заказы</b>\n\n{html.escape(hint)}",
            city_workshop_orders_keyboard(floor_number=fl),
            city_orders=True,
        )
        await query.answer()
    except Exception:
        logger.exception("wso:open")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:list:"))
async def wso_list(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
        await _workshop_ui(
            state,
            query,
            char,
            "\n".join(lines),
            InlineKeyboardMarkup(inline_keyboard=kb_rows),
            city_orders=True,
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
async def wso_new(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
            await _workshop_ui(
                state,
                query,
                char,
                msg,
                city_workshop_orders_keyboard(floor_number=fl),
                city_orders=True,
            )
    except Exception:
        logger.exception("wso:new")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wso:done:"))
async def wso_done(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
            await _workshop_ui(
                state,
                query,
                char,
                msg,
                city_workshop_orders_keyboard(floor_number=fl),
                city_orders=True,
            )
        await query.answer(("Готово." if ok else msg)[:200], show_alert=not ok)
    except Exception:
        logger.exception("wso:done")
        await query.answer("Ошибка.", show_alert=True)

