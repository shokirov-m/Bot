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
    workshop_dis_bag_keyboard,
    workshop_gacha_keyboard,
    workshop_main_keyboard,
    workshop_prof_hub_keyboard,
    workshop_prof_keyboard,
    workshop_queue_keyboard,
    workshop_rune_bag_pick_keyboard,
    workshop_rune_elements_keyboard,
    workshop_rune_socket_pick_keyboard,
    workshop_rune_tiers_keyboard,
    workshop_sharpen_slots_keyboard,
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
from game.items import item_categories as inv_cat
from game.items.craft_resources import RESOURCE_DEFS, total_craft_resource_in_bag
from game.items.runes import RuneData, ensure_rune_socket_list, extract_rune_from_item
from services import craft_gacha_service, forge_service, workshop_order_service, workshop_service
from services import unlock_service
from services.workshop_enchant_service import (
    USE_TAG_ALCHEMY_ENCHANT,
    list_compatible_targets,
    summarize_scroll,
    try_apply_alchemy_enchant,
)
from services.workshop_leaderboard_service import cached_leaderboard_html
from db.models.app_global import AppGlobal

from bot.utils.game_art import (
    craft_resource_photo_path,
    menu_workshop_orders_photo_path,
    menu_workshop_photo_path,
)
from bot.utils.game_ui import push_game_ui
from utils.ui import format_craft_result_effects_block_html

router = Router(name="workshop")


def _workshop_dis_norm_filter(v: str) -> str | None:
    if not v or v == "all":
        return None
    return str(v).lower()


async def _workshop_ui(
    state: FSMContext,
    query: CallbackQuery,
    character: Character,
    text: str,
    reply_markup,
    *,
    city_orders: bool = False,
    photo_path: str | None = None,
) -> None:
    if query.message is None or query.bot is None:
        return
    pp = photo_path
    if pp is None:
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
    """Только рецепты из списка изученных чертежей игрока (known_blueprints)."""
    known = known_blueprint_ids(character)
    out: list[dict] = []
    for r in recipes_for_profession(prof):
        rid = str(r.get("id") or "")
        if not rid or rid not in known:
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
    rid_key = str(r.get("id") or "")
    if not rid_key or rid_key not in known_blueprint_ids(char):
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
    effects = ""
    if isinstance(res_item, dict):
        eff_block = format_craft_result_effects_block_html(res_item)
        if eff_block.strip():
            effects = f"\n\n<b>Что даёт предмет:</b>\n{eff_block}"
    return (
        f"📋 <b>{name}</b>\n"
        f"<i>Результат:</i> {res_name}{effects}\n\n"
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


def _recipe_locked(character: Character, prof: str, recipe: dict) -> bool:
    ws = get_workshop_state(character)
    plv = int(ws["prof_levels"].get(prof, 1))
    st_lv = int(ws["stations"].get(prof, 1))
    if plv < int(recipe.get("min_profession_level", 1)):
        return True
    if st_lv < int(recipe.get("min_station_level", 1)):
        return True
    if int(character.level) < int(recipe.get("min_character_level", 1)):
        return True
    return False


def _recipe_button_label(character: Character, prof: str, recipe: dict) -> str:
    nm = str(recipe.get("name_ru", recipe.get("id", "")))
    if _recipe_locked(character, prof, recipe):
        return f"🔒 {nm}"
    return nm


def _sort_bag_inventory_order(items: list) -> list:
    """Тот же порядок секций, что у вкладок сумки (см. inventory._SECTION_INFER_ORDER)."""
    order = (
        inv_cat.INV_SEC_WEAPON,
        inv_cat.INV_SEC_ARMOR_BODY,
        inv_cat.INV_SEC_ACCESSORY,
        inv_cat.INV_SEC_HELMET,
        inv_cat.INV_SEC_PANTS,
        inv_cat.INV_SEC_OTHER_GEAR,
        inv_cat.INV_SEC_CONSUMABLE,
        inv_cat.INV_SEC_RESOURCE,
    )
    buckets: dict[str, list] = {s: [] for s in order}
    rest: list = []
    for it in items:
        d = dict(it.item_data or {})
        placed = False
        for sec in order:
            if inv_cat.item_data_matches_inv_section(d, sec):
                buckets[sec].append(it)
                placed = True
                break
        if not placed:
            rest.append(it)
    out: list = []
    for sec in order:
        buckets[sec].sort(key=lambda x: str((x.item_data or {}).get("name", "")))
        out.extend(buckets[sec])
    rest.sort(key=lambda x: str((x.item_data or {}).get("name", "")))
    out.extend(rest)
    return out


_ENCH_SCROLL_PER_PAGE = 8
_ENCH_TARGET_PER_PAGE = 8


def _enchant_scroll_button_label(it) -> str:
    """Подпись кнопки свитка: явный префикс 📜, если в имени ещё нет свитка."""
    raw = str((it.item_data or {}).get("name", f"#{it.id}"))[:36]
    s = raw.strip().lower()
    if "📜" in raw or "свиток" in s:
        return raw[:40]
    return f"📜 {raw}"[:40]


def _alchemy_scroll_items(bag_items: list) -> list:
    out: list = []
    for it in bag_items:
        d = dict(it.item_data or {})
        if str(d.get("use_tag") or "") == USE_TAG_ALCHEMY_ENCHANT:
            out.append(it)
    out.sort(key=lambda x: str((x.item_data or {}).get("name", "")))
    return out


def _paginate(lst: list, page: int, per_page: int = 8) -> tuple[list, int]:
    p = max(0, int(page))
    start = p * per_page
    return lst[start : start + per_page], p


async def render_workshop_hub(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Текст и клавиатура хаба мастерской (меню и дом)."""
    char = await _char(session, query)
    if char is None or query.message is None:
        return
    if not unlock_service.is_unlocked(char, "menu_workshop"):
        await query.answer("Откроется с 5 ур.", show_alert=True)
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
    await _workshop_ui(state, query, char, "\n".join(lines), workshop_main_keyboard(loc, character=char))
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


@router.callback_query(F.data == "wsp:gacha")
async def workshop_gacha_open(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        text = craft_gacha_service.format_gacha_intro_html(char)
        await _workshop_ui(state, query, char, text, workshop_gacha_keyboard())
        await query.answer()
    except Exception:
        logger.exception("wsp:gacha")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^wsp:gacha:pull(10)?:(blacksmith|alchemist|jeweler)$"))
async def workshop_gacha_pull(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if query.data is None or query.message is None or query.bot is None:
            await query.answer()
            return
        char = await _char(session, query)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        parts = query.data.split(":")
        times = 10 if parts[2] == "pull10" else 1
        prof = parts[-1].strip().lower()
        await character_repo.lock_character_row(session, char.id)
        ok, lines, pulled_ids = await craft_gacha_service.try_gacha_pull(
            session,
            char,
            prof,
            times=times,
            bot=query.bot,
        )
        await session.flush()
        base = craft_gacha_service.format_gacha_intro_html(char)
        if ok:
            body = base + "\n\n" + "\n".join(lines)
        else:
            body = base + "\n\n<i>" + "\n".join(lines) + "</i>"
        mat_photo = None
        if ok and pulled_ids:
            from game.items.craft_resources import RESOURCE_DEFS

            best_id = max(
                pulled_ids,
                key=lambda rid: int((RESOURCE_DEFS.get(str(rid)) or {}).get("stars") or 1),
            )
            mat_photo = craft_resource_photo_path(best_id)
        await _workshop_ui(state, query, char, body, workshop_gacha_keyboard(), photo_path=mat_photo)
        await query.answer("Приз!" if ok else (lines[0][:180] if lines else "Нет"))
    except Exception:
        logger.exception("wsp:gacha:pull")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:prof:"))
async def workshop_prof(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        prof = str(query.data.split(":")[2])
        title = PROF_TITLE_RU.get(prof, prof)
        lines = [
            f"{title}",
            "",
            "<i>Выбери раздел: крафт по изученным чертежам, заточка / зачарование / руны — под профессию.</i>",
        ]
        await _workshop_ui(
            state,
            query,
            char,
            "\n".join(lines),
            workshop_prof_hub_keyboard(prof),
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:prof")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:craft:"))
async def workshop_craft(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
                        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"wsp:prof:{prof}")],
                        menu_nav_button_row(),
                    ],
                ),
            )
            await query.answer()
            return
        recipe_rows = [(str(r.get("id")), _recipe_button_label(char, prof, r)) for r in recipes]
        chunk, page = _paginate(recipe_rows, 0)
        lines = [
            f"{title} — <b>крафт</b>",
            "<i>Нажми рецепт — карточка: ресурсы, время. 🔒 — чертеж есть, но не хватает уровня / станции / героя.</i>",
            "<i>Сортировка: по требуемому уровню профессии.</i>",
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
        logger.exception("wsp:craft")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:craftpage:"))
async def workshop_craft_page(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
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
                        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"wsp:prof:{prof}")],
                        menu_nav_button_row(),
                    ],
                ),
            )
            await query.answer()
            return
        recipe_rows = [(str(r.get("id")), _recipe_button_label(char, prof, r)) for r in recipes]
        chunk, page = _paginate(recipe_rows, page)
        lines = [f"{title} — <b>крафт</b>", ""]
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
        logger.exception("wsp:craftpage")
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
        r_def = get_recipe_by_id(rid)
        locked = bool(r_def and _recipe_locked(char, prof, r_def))
        if locked:
            body = "🔒 <i>Недостаточно уровня профессии, станции или героя для крафта.</i>\n\n" + body
        title = PROF_TITLE_RU.get(prof, prof)
        row_create = (
            [InlineKeyboardButton(text="🔨 Создать", callback_data=f"wsp:start:{rid}")]
            if not locked
            else [InlineKeyboardButton(text="🔒 Создать (заблокировано)", callback_data="wsp:craftlocked")]
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                row_create,
                [InlineKeyboardButton(text="⬅ К крафту", callback_data=f"wsp:craft:{prof}")],
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
            workshop_main_keyboard(character=char),
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
            loc = get_locale(char, query.from_user.language_code if query.from_user else None)
            kb = workshop_main_keyboard(loc, character=char)
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
            workshop_main_keyboard(character=char),
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


@router.callback_query(F.data == "wsp:craftlocked")
async def workshop_craft_locked(query: CallbackQuery) -> None:
    await query.answer("Чертёж изучен, но не хватает уровня профессии, станции или героя.", show_alert=True)


@router.callback_query(F.data == "wsp:sharp:menu")
async def workshop_sharpen_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        bonus = forge_service.workshop_blacksmith_sharpen_bonus(char)
        pct = int(round(bonus * 100))
        slots = await forge_service.list_enchant_slot_button_rows(session, char.id)
        lines = [
            "✨ <b>Заточка в мастерской</b>",
            "",
            f"Уровень кузнеца даёт до <b>+20%</b> к шансу успеха заточки; сейчас ≈ <b>+{pct}%</b> "
            "(дополнительно к бонусу верстака дома, если есть).",
            "<i>Выбери надетый предмет по слоту. Стоимость и материалы — как в городской кузнице.</i>",
        ]
        if not slots:
            lines.append("")
            lines.append("<i>Нет экипировки для заточки — надень предметы в /inv.</i>")
        kb = (
            workshop_sharpen_slots_keyboard(slots)
            if slots
            else InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ К кузнице", callback_data="wsp:prof:blacksmith")],
                    menu_nav_button_row(),
                ],
            )
        )
        await _workshop_ui(state, query, char, "\n".join(lines), kb)
        await query.answer()
    except Exception:
        logger.exception("wsp:sharp:menu")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:sharp:do:"))
async def workshop_sharpen_do(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.data is None or query.message is None:
            return
        slot = str(query.data.split(":")[3])
        extra = forge_service.workshop_blacksmith_sharpen_bonus(char)
        ok, lines = await forge_service.try_enchant_equipped_in_slot(
            session,
            char,
            slot,
            skip_forge_location_check=True,
            extra_success_bonus=extra,
            spend_label="Мастерская: заточка",
            spend_kind_tag="workshop",
        )
        await session.commit()
        if not ok:
            await query.answer((lines[0] if lines else "Нельзя.")[:200], show_alert=True)
            return
        body = "\n".join(lines)
        slots = await forge_service.list_enchant_slot_button_rows(session, char.id)
        kb = (
            workshop_sharpen_slots_keyboard(slots)
            if slots
            else InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ К кузнице", callback_data="wsp:prof:blacksmith")],
                    menu_nav_button_row(),
                ],
            )
        )
        pct = int(round(extra * 100))
        hdr = f"✨ Заточка (бонус кузнеца ≈ +{pct}%)\n\n"
        await _workshop_ui(state, query, char, hdr + body, kb)
        await query.answer("Готово.")
    except Exception:
        logger.exception("wsp:sharp:do")
        await query.answer("Ошибка.", show_alert=True)


def _workshop_enchant_scroll_kb(page: int, scrolls: list, total: int) -> InlineKeyboardMarkup:
    max_page = max(0, (max(0, total) - 1) // _ENCH_SCROLL_PER_PAGE)
    p = max(0, min(int(page), max_page))
    start = p * _ENCH_SCROLL_PER_PAGE
    chunk = scrolls[start : start + _ENCH_SCROLL_PER_PAGE]
    rows: list[list[InlineKeyboardButton]] = []
    for it in chunk:
        nm = _enchant_scroll_button_label(it)
        sid = int(it.id)
        rows.append([InlineKeyboardButton(text=nm, callback_data=f"wsp:ench:pick:{sid}")])
    nav: list[InlineKeyboardButton] = []
    if max_page > 0:
        if p > 0:
            nav.append(InlineKeyboardButton(text="◀", callback_data=f"wsp:ench:scrpage:{p - 1}"))
        nav.append(InlineKeyboardButton(text=f"{p + 1}/{max_page + 1}", callback_data="wsp:noop"))
        if p < max_page:
            nav.append(InlineKeyboardButton(text="▶", callback_data=f"wsp:ench:scrpage:{p + 1}"))
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅ Лаборатория", callback_data="wsp:prof:alchemist")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _workshop_enchant_targets_kb(scroll_id: int, page: int, targets: list) -> InlineKeyboardMarkup:
    total = len(targets)
    max_page = max(0, (max(0, total) - 1) // _ENCH_TARGET_PER_PAGE)
    p = max(0, min(int(page), max_page))
    start = p * _ENCH_TARGET_PER_PAGE
    chunk = targets[start : start + _ENCH_TARGET_PER_PAGE]
    rows: list[list[InlineKeyboardButton]] = []
    for t in chunk:
        nm = str((t.item_data or {}).get("name", f"#{t.id}"))[:44]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"➡ {nm}",
                    callback_data=f"wsp:ench:do:{scroll_id}:{int(t.id)}",
                ),
            ],
        )
    nav: list[InlineKeyboardButton] = []
    if max_page > 0:
        if p > 0:
            nav.append(
                InlineKeyboardButton(text="◀", callback_data=f"wsp:ench:tgtpage:{scroll_id}:{p - 1}"),
            )
        if p < max_page:
            nav.append(
                InlineKeyboardButton(text="▶", callback_data=f"wsp:ench:tgtpage:{scroll_id}:{p + 1}"),
            )
        if nav:
            rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅ К свиткам", callback_data="wsp:ench:menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query((F.data == "wsp:ench:menu") | F.data.startswith("wsp:ench:scrpage:"))
async def workshop_enchant_scroll_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        page = 0
        if query.data.startswith("wsp:ench:scrpage:"):
            page = int(query.data.split(":")[3])
        bag = await inventory_repo.list_bag_items(session, char.id)
        scrolls = _alchemy_scroll_items(bag)
        lines = [
            "📜 <b>Свитки зачарования</b>",
            "",
            "<i>Выбери свиток из сумки. Предмет для наложения — в порядке как в инвентаре.</i>",
        ]
        if not scrolls:
            lines.append("")
            lines.append("<i>Нет подходящих свитков в сумке.</i>")
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ Лаборатория", callback_data="wsp:prof:alchemist")],
                    menu_nav_button_row(),
                ],
            )
        else:
            kb = _workshop_enchant_scroll_kb(page, scrolls, len(scrolls))
        await _workshop_ui(state, query, char, "\n".join(lines), kb)
        await query.answer()
    except Exception:
        logger.exception("wsp:ench:menu")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:ench:pick:"))
async def workshop_enchant_pick_scroll(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        scroll_id = int(query.data.split(":")[3])
        scroll_it = await inventory_repo.get_item_for_character(session, char.id, scroll_id)
        if scroll_it is None:
            await query.answer("Свиток не найден.", show_alert=True)
            return
        sd = dict(scroll_it.item_data or {})
        if str(sd.get("use_tag") or "") != USE_TAG_ALCHEMY_ENCHANT:
            await query.answer("Это не зачарование.", show_alert=True)
            return
        raw_targets = await list_compatible_targets(session, char.id, sd)
        targets = _sort_bag_inventory_order(raw_targets)
        if not targets:
            await query.answer("Нет совместимых предметов в сумке.", show_alert=True)
            return
        summ = summarize_scroll(sd)
        lines = [
            "📜 <b>Свиток зачарования</b>",
            f"<i>{html.escape(summ)}</i>",
            "",
            "<i>Выбери предмет (порядок как в инвентаре).</i>",
        ]
        kb = _workshop_enchant_targets_kb(scroll_id, 0, targets)
        await _workshop_ui(state, query, char, "\n".join(lines), kb)
        await query.answer()
    except Exception:
        logger.exception("wsp:ench:pick")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:ench:tgtpage:"))
async def workshop_enchant_targets_page(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        _, _, _, sid_s, p_s = query.data.split(":", 4)
        scroll_id = int(sid_s)
        page = int(p_s)
        scroll_it = await inventory_repo.get_item_for_character(session, char.id, scroll_id)
        if scroll_it is None:
            await query.answer("Свиток не найден.", show_alert=True)
            return
        sd = dict(scroll_it.item_data or {})
        if str(sd.get("use_tag") or "") != USE_TAG_ALCHEMY_ENCHANT:
            await query.answer("Это не зачарование.", show_alert=True)
            return
        raw_targets = await list_compatible_targets(session, char.id, sd)
        targets = _sort_bag_inventory_order(raw_targets)
        if not targets:
            await query.answer("Нет целей.", show_alert=True)
            return
        summ = summarize_scroll(sd)
        lines = [
            "📜 <b>Свиток зачарования</b>",
            f"<i>{html.escape(summ)}</i>",
            "",
            "<i>Выбери предмет (порядок как в инвентаре).</i>",
        ]
        kb = _workshop_enchant_targets_kb(scroll_id, page, targets)
        await _workshop_ui(state, query, char, "\n".join(lines), kb)
        await query.answer()
    except Exception:
        logger.exception("wsp:ench:tgtpage")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:ench:do:"))
async def workshop_enchant_apply(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        parts = query.data.split(":")
        if len(parts) < 5:
            await query.answer()
            return
        scroll_id = int(parts[3])
        target_id = int(parts[4])
        ok, msg = await try_apply_alchemy_enchant(session, char, scroll_id, target_id)
        await session.commit()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        scrolls = _alchemy_scroll_items(bag)
        lines = [
            msg,
            "",
            "📜 <b>Свитки зачарования</b>",
            "<i>Можно выбрать другой свиток.</i>",
        ]
        kb = (
            _workshop_enchant_scroll_kb(0, scrolls, len(scrolls))
            if scrolls
            else InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ Лаборатория", callback_data="wsp:prof:alchemist")],
                    menu_nav_button_row(),
                ],
            )
        )
        await _workshop_ui(state, query, char, "\n".join(lines), kb)
        await query.answer("Готово.")
    except Exception:
        logger.exception("wsp:ench:do")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:rune:menu")
async def workshop_rune_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        text = (
            "💎 <b>Слияние рун</b>\n\n"
            "<i>3× ранг I → II, 4× II → III, 5× III → IV, 5× IV → V (одна стихия). "
            "Для ранга IV нужен <b>10 ур. ювелира</b>, для V — <b>18 ур.</b> "
            "Выбери целевой ранг, затем стихию.</i>"
        )
        await _workshop_ui(state, query, char, text, workshop_rune_tiers_keyboard())
        await query.answer()
    except Exception:
        logger.exception("wsp:rune:menu")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:rune:tier:"))
async def workshop_rune_tier(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        tr = int(query.data.split(":")[3])
        text = f"💎 <b>Стихия</b> (цель — ранг {tr})\n\n<i>Нажми на элемент.</i>"
        await _workshop_ui(state, query, char, text, workshop_rune_elements_keyboard(tr))
        await query.answer()
    except Exception:
        logger.exception("wsp:rune:tier")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:rune:do:"))
async def workshop_rune_do(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        parts = query.data.split(":")
        if len(parts) < 5:
            await query.answer()
            return
        target_rank = int(parts[3])
        element = str(parts[4])
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await forge_service.try_workshop_rune_merge(
            session,
            char,
            element=element,
            target_rank=target_rank,
        )
        await session.flush()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        text = f"{msg}\n\n💎 <b>Слияние рун</b>\n\n<i>Можно повторить.</i>"
        await _workshop_ui(state, query, char, text, workshop_rune_tiers_keyboard())
        await query.answer("Готово.")
    except Exception:
        logger.exception("wsp:rune:do")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:rsk")
async def workshop_rune_socket_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        bag = await inventory_repo.list_bag_items(session, char.id)
        rows: list[tuple[int, int, str, str]] = []
        for it in bag:
            rd = extract_rune_from_item(dict(it.item_data or {}))
            if rd is not None:
                # Sort by tier (rank) desc, then by element, then label.
                rows.append((int(it.id), int(rd.rank), str(rd.element), rd.display_name))
        if not rows:
            await query.answer("В сумке нет рун.", show_alert=True)
            return
        rows.sort(key=lambda x: (-int(x[1]), str(x[2]), str(x[3])))
        pairs: list[tuple[int, str]] = [(rid, lab) for rid, _, __, lab in rows]
        text = (
            "⚔ <b>Вставка руны в оружие</b>\n\n"
            "<i>Стоимость попытки <b>500 💰</b>. Шанс успеха <b>70–80%</b> "
            "(при провале золото списано, руна остаётся в сумке). Нужно надетое оружие со свободным гнездом.</i>"
        )
        await _workshop_ui(state, query, char, text, workshop_rune_bag_pick_keyboard(pairs))
        await query.answer()
    except Exception:
        logger.exception("wsp:rsk")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^wsp:rsk:\d+$"))
async def workshop_rune_socket_apply(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        rid = int(query.data.split(":")[2])
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await forge_service.try_workshop_socket_rune_paid(session, char, rune_bag_item_id=rid)
        await session.flush()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        text = f"{msg}\n\n⚔ <b>Вставка руны</b>\n\n<i>Можно выбрать другую руну.</i>"
        bag = await inventory_repo.list_bag_items(session, char.id)
        rows: list[tuple[int, int, str, str]] = []
        for it in bag:
            rd = extract_rune_from_item(dict(it.item_data or {}))
            if rd is not None:
                rows.append((int(it.id), int(rd.rank), str(rd.element), rd.display_name))
        rows.sort(key=lambda x: (-int(x[1]), str(x[2]), str(x[3])))
        pairs: list[tuple[int, str]] = [(rid, lab) for rid, _, __, lab in rows]
        kb = (
            workshop_rune_bag_pick_keyboard(pairs)
            if pairs
            else workshop_prof_hub_keyboard("jeweler")
        )
        await _workshop_ui(state, query, char, text, kb)
        await query.answer("Готово.")
    except Exception:
        logger.exception("wsp:rsk:apply")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:rrx")
async def workshop_rune_remove_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        weapon = await inventory_repo.get_equipped_weapon(session, char.id)
        if weapon is None:
            await query.answer("Нет надетого оружия.", show_alert=True)
            return
        wdata = dict(weapon.item_data or {})
        ensure_rune_socket_list(wdata)
        sockets = wdata.get("rune_sockets") or []
        labels: list[tuple[int, str]] = []
        for i, cell in enumerate(sockets):
            if isinstance(cell, dict) and cell.get("element"):
                try:
                    rd = RuneData.from_dict(cell)
                    labels.append((i, f"Гнездо {i + 1}: {rd.display_name}"))
                except (ValueError, TypeError, KeyError):
                    labels.append((i, f"Гнездо {i + 1}: ?"))
        if not labels:
            await query.answer("Нет вставленных рун.", show_alert=True)
            return
        text = (
            "🔓 <b>Извлечение руны</b>\n\n"
            "<i><b>500 💰</b> за попытку. Шанс вернуть руну в сумку <b>70–80%</b> "
            "(иначе руна уничтожается).</i>"
        )
        await _workshop_ui(state, query, char, text, workshop_rune_socket_pick_keyboard(labels))
        await query.answer()
    except Exception:
        logger.exception("wsp:rrx")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^wsp:rrx:\d+$"))
async def workshop_rune_remove_apply(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        idx = int(query.data.split(":")[2])
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await forge_service.try_workshop_remove_rune_paid(session, char, socket_index=idx)
        await session.flush()
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        text = f"{msg}\n\n🔓 <b>Извлечение руны</b>\n\n<i>Можно выбрать другое гнездо.</i>"
        weapon = await inventory_repo.get_equipped_weapon(session, char.id)
        labels: list[tuple[int, str]] = []
        if weapon is not None:
            wdata = dict(weapon.item_data or {})
            ensure_rune_socket_list(wdata)
            sockets = wdata.get("rune_sockets") or []
            for i, cell in enumerate(sockets):
                if isinstance(cell, dict) and cell.get("element"):
                    try:
                        rd = RuneData.from_dict(cell)
                        labels.append((i, f"Гнездо {i + 1}: {rd.display_name}"))
                    except (ValueError, TypeError, KeyError):
                        labels.append((i, f"Гнездо {i + 1}: ?"))
        kb = (
            workshop_rune_socket_pick_keyboard(labels)
            if labels
            else workshop_prof_hub_keyboard("jeweler")
        )
        await _workshop_ui(state, query, char, text, kb)
        await query.answer("Готово.")
    except Exception:
        logger.exception("wsp:rrx:apply")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "wsp:brk:menu")
async def workshop_disassemble_menu(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None:
            return
        pairs = await forge_service.list_disassemblable_items(session, char)
        if not pairs:
            await query.answer("В сумке нет предметов для разбора.", show_alert=True)
            return
        text = (
            "🔨 <b>Разбор предметов</b>\n\n"
            "<i>Как в кузнице города: экипировка из сумки → материалы заточки. Фильтры и свип ниже.</i>"
        )
        await _workshop_ui(state, query, char, text, workshop_dis_bag_keyboard(pairs))
        await query.answer()
    except Exception:
        logger.exception("wsp:brk:menu")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:brk:f:"))
async def workshop_disassemble_filter(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        parts = query.data.split(":")
        if len(parts) < 5:
            await query.answer()
            return
        rar_code = parts[3]
        knd_code = parts[4]
        rar = _workshop_dis_norm_filter(rar_code)
        knd = _workshop_dis_norm_filter(knd_code)
        pairs = await forge_service.list_disassemblable_items(
            session, char, rarity_filter=rar, kind_filter=knd,
        )
        title = "🔨 <b>Разбор предметов</b>"
        if rar or knd:
            title += f"\n<i>Фильтр:</i> {rar or 'все'} / {knd or 'все типы'}"
        if not pairs:
            title += "\n<i>Под фильтр ничего не попало.</i>"
        await _workshop_ui(
            state,
            query,
            char,
            title,
            workshop_dis_bag_keyboard(pairs, rarity_filter=rar_code, kind_filter=knd_code),
        )
        await query.answer()
    except Exception:
        logger.exception("wsp:brk:f")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:brk:x:"))
async def workshop_disassemble_apply(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        item_id = int(query.data.split(":")[3])
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await forge_service.try_workshop_disassemble_bag_item(session, char, item_id)
        await session.flush()
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        pairs = await forge_service.list_disassemblable_items(session, char)
        text = f"{msg}\n\n🔨 <b>Разбор предметов</b>"
        kb = (
            workshop_dis_bag_keyboard(pairs)
            if pairs
            else workshop_prof_hub_keyboard("blacksmith")
        )
        await _workshop_ui(state, query, char, text, kb)
        await query.answer("Разобрано.")
    except Exception:
        logger.exception("wsp:brk:x")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("wsp:brk:sw:"))
async def workshop_disassemble_sweep(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        char = await _char(session, query)
        if char is None or query.message is None or query.data is None:
            return
        max_rar = str(query.data.split(":")[3])
        await character_repo.lock_character_row(session, char.id)
        ok, msg = await forge_service.try_workshop_sweep_disassemble(session, char, max_rarity=max_rar)
        await session.flush()
        if not ok:
            await query.answer(msg[:180], show_alert=True)
            return
        pairs = await forge_service.list_disassemblable_items(session, char)
        text = f"{msg}\n\n🔨 <b>Разбор предметов</b>"
        kb = (
            workshop_dis_bag_keyboard(pairs)
            if pairs
            else workshop_prof_hub_keyboard("blacksmith")
        )
        await _workshop_ui(state, query, char, text, kb)
        await query.answer("Свип готов.")
    except Exception:
        logger.exception("wsp:brk:sw")
        await query.answer("Ошибка.", show_alert=True)


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
            workshop_main_keyboard(character=char),
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

