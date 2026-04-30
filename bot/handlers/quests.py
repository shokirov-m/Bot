"""Квесты: странник (qst:*), расширенные поручения (qtk:/qcl:), /quests."""

from __future__ import annotations

import asyncio
import html
import re
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.quest_kb import quest_back_keyboard, quest_dialog_keyboard
from bot.states.combat_states import CombatStates
from bot.utils.game_ui import push_game_ui
from db.repository import character_repo, quest_repo, user_repo
from game.floors import floor_data
from game.quests.floor_quests import npc_quest_template
from game.quests.npc_quests import QuestTemplate, template_by_key, templates_for_floor
from services import quest_service
from services import daily_quest_service as dqs
from services import fame_bonuses as fb
from services.floor_service import floor_keyboard_for_character, format_floor_message
from utils.ui import LINE_SEP

if TYPE_CHECKING:
    from db.models.character import Character
    from db.models.quest import QuestProgress

router = Router(name="quests")

_QST_CB = re.compile(r"^qst:(\d+):(view|acc|back)$")

QUEST_FLOOR_PAGE_SIZE = 1
QUEST_ACTIVE_PAGE_SIZE = 6


def _strip_html_alert(msg: str) -> str:
    return re.sub(r"<[^>]+>", "", msg).strip()


async def _count_all_active_quests(session: AsyncSession, character_id: int) -> int:
    a = await quest_repo.list_active_npc_extended_quests(session, character_id)
    b = await quest_repo.list_active_slain_quests(session, character_id)
    return len(a) + len(b)


async def _merged_active_quest_rows(session: AsyncSession, character_id: int) -> list[QuestProgress]:
    a = await quest_repo.list_active_npc_extended_quests(session, character_id)
    b = await quest_repo.list_active_slain_quests(session, character_id)
    merged = list(a) + list(b)
    merged.sort(key=lambda r: r.quest_key)
    return merged


def _active_quest_title(row: QuestProgress) -> str:
    qk = row.quest_key
    if qk.startswith("npcq_"):
        t = template_by_key(qk)
        return t.title if t is not None else qk
    if qk.startswith("tower_slain_"):
        tail = qk.removeprefix("tower_slain_")
        if tail.isdigit():
            tpl = npc_quest_template(int(tail))
            if tpl is not None:
                return tpl.title
    return qk


def _btn_take_label(title: str, max_len: int = 22) -> str:
    base = f"📋 Взять: {title}"
    return f"{base[: max_len - 1]}…" if len(base) > max_len else base


def _btn_claim_label(title: str, max_len: int = 20) -> str:
    base = f"🎁 Сдать: {title}"
    return f"{base[: max_len - 1]}…" if len(base) > max_len else base


async def _floor_quest_lines_and_buttons(
    session: AsyncSession,
    char: Character,
    tpl: QuestTemplate,
) -> tuple[list[str], list[list[InlineKeyboardButton]]]:
    lines: list[str] = []
    rows_btn: list[list[InlineKeyboardButton]] = []
    row = await quest_repo.get_by_key(session, char.id, tpl.key)
    if row is None:
        lines.append(f"○ <b>{html.escape(tpl.title)}</b> — можно взять.")
        rows_btn.append(
            [
                InlineKeyboardButton(
                    text=_btn_take_label(tpl.title),
                    callback_data=f"qtk:{tpl.key}",
                ),
            ],
        )
        return lines, rows_btn
    if row.status == "completed":
        lines.append(f"🏁 <b>{html.escape(tpl.title)}</b> — уже выполнено.")
        return lines, rows_btn
    if row.status != "active":
        return lines, rows_btn
    p = dict(row.progress or {})
    if p.get("pending_claim"):
        lines.append(f"✅ <b>{html.escape(tpl.title)}</b> — <b>готово</b>, забирай награду!")
        rows_btn.append(
            [
                InlineKeyboardButton(
                    text=_btn_claim_label(tpl.title),
                    callback_data=f"qcl:{tpl.key}",
                ),
            ],
        )
    else:
        cur = int(p.get("current", 0))
        need = int(p.get("target_count", 1))
        lines.append(f"⚔️ <b>{html.escape(tpl.title)}</b> — <b>{cur}/{need}</b>")
    return lines, rows_btn


async def render_quest_floor_hub(
    session: AsyncSession,
    char: Character,
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup]:
    """Экран «Задания» для текущего этажа (npcq_*), постранично по шаблонам этажа."""
    fl = int(char.floor_number)
    lines = [LINE_SEP, f"📋 <b>ЗАДАНИЯ — ЭТАЖ {fl}</b>", LINE_SEP, ""]
    rows_btn: list[list[InlineKeyboardButton]] = []
    active_elsewhere = await _count_all_active_quests(session, char.id)

    if fl % 3 != 0 or fl >= 100:
        lines.append("На этом этаже нет заказчика таких поручений.")
        lines.append("<i>NPC стоят на этажах 3, 6, 9 … 99.</i>")
        if active_elsewhere > 0:
            rows_btn.append(
                [
                    InlineKeyboardButton(
                        text=f"📑 Все активные ({active_elsewhere})",
                        callback_data="qhub:a:0",
                    ),
                ],
            )
        _dq = dqs.get_daily_quests(char)
        _dq_cl = sum(1 for q in _dq if dqs.can_claim(q))
        _dq_done = sum(1 for q in _dq if dqs.is_done(q))
        if _dq_cl > 0:
            _dlbl = f"📅 Ежедневные ({_dq_cl} к получению!)"
        elif _dq_done > 0:
            _dlbl = f"📅 Ежедневные ({_dq_done}/3 выполнено)"
        else:
            _dlbl = "📅 Ежедневные задания"
        rows_btn.append([InlineKeyboardButton(text=_dlbl, callback_data="qhub:d")])
        rows_btn.append([InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")])
        return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows_btn)

    tpls = templates_for_floor(fl)
    if not tpls:
        if active_elsewhere > 0:
            rows_btn.append(
                [
                    InlineKeyboardButton(
                        text=f"📑 Все активные ({active_elsewhere})",
                        callback_data="qhub:a:0",
                    ),
                ],
            )
        rows_btn.append([InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")])
        return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows_btn)

    npc_name = tpls[0].npc_name
    npc_emoji = tpls[0].npc_emoji
    lines.append(f"{npc_emoji} <b>{html.escape(npc_name)}</b> говорит:")
    lines.append("«Есть работа для того, кто не боится крови и пыли.»")
    lines.append("")

    n_tpl = len(tpls)
    pages = max(1, (n_tpl + QUEST_FLOOR_PAGE_SIZE - 1) // QUEST_FLOOR_PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    slice_tpls = tpls[page * QUEST_FLOOR_PAGE_SIZE : (page + 1) * QUEST_FLOOR_PAGE_SIZE]

    has_active = False
    has_claim = False
    for tpl in tpls:
        row = await quest_repo.get_by_key(session, char.id, tpl.key)
        if row is not None and row.status == "active":
            has_active = True
            p = dict(row.progress or {})
            if p.get("pending_claim"):
                has_claim = True

    for tpl in slice_tpls:
        bl, br = await _floor_quest_lines_and_buttons(session, char, tpl)
        lines.extend(bl)
        rows_btn.extend(br)

    if pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"qhub:p:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="qhub:noop"))
        if page < pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"qhub:p:{page + 1}"))
        rows_btn.append(nav)

    if active_elsewhere > 0:
        rows_btn.append(
            [
                InlineKeyboardButton(
                    text=f"📑 Все активные ({active_elsewhere})",
                    callback_data="qhub:a:0",
                ),
            ],
        )

    if has_active and not has_claim:
        lines.append("")
        lines.append("<i>Продолжай бой на башне.</i>")

    # Кнопка перехода на ежедневные задания
    _daily_q = dqs.get_daily_quests(char)
    _daily_claimable = sum(1 for q in _daily_q if dqs.can_claim(q))
    _daily_done = sum(1 for q in _daily_q if dqs.is_done(q))
    if _daily_claimable > 0:
        _daily_lbl = f"📅 Ежедневные ({_daily_claimable} к получению!)"
    elif _daily_done > 0:
        _daily_lbl = f"📅 Ежедневные ({_daily_done}/3 выполнено)"
    else:
        _daily_lbl = "📅 Ежедневные задания"
    rows_btn.append([InlineKeyboardButton(text=_daily_lbl, callback_data="qhub:d")])

    rows_btn.append([InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows_btn)


async def render_active_quests_overview(
    session: AsyncSession,
    char: Character,
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup]:
    """Все активные поручения (npcq_* и странник tower_slain_*), страницы из БД."""
    rows = await _merged_active_quest_rows(session, char.id)
    n = len(rows)
    per = QUEST_ACTIVE_PAGE_SIZE
    pages = max(1, (n + per - 1) // per) if n else 1
    page = max(0, min(page, pages - 1))
    chunk = rows[page * per : (page + 1) * per]

    lines = [
        LINE_SEP,
        "📑 <b>ВСЕ АКТИВНЫЕ ПОРУЧЕНИЯ</b>",
        LINE_SEP,
        "",
    ]
    rows_btn: list[list[InlineKeyboardButton]] = []

    if not rows:
        lines.append("<i>Сейчас нет активных заданий такого типа.</i>")
    else:
        for row in chunk:
            title = _active_quest_title(row)
            p = dict(row.progress or {})
            if row.quest_key.startswith("tower_slain_"):
                k = int(p.get("kills", 0))
                tail = row.quest_key.removeprefix("tower_slain_")
                need = 1
                if tail.isdigit():
                    tpl = npc_quest_template(int(tail))
                    if tpl is not None:
                        need = int(p.get("need", tpl.kills_needed))
                if p.get("pending_claim"):
                    lines.append(f"✅ <b>{html.escape(title)}</b> — <b>готово</b>, сдай страннику.")
                    rows_btn.append(
                        [
                            InlineKeyboardButton(
                                text=_btn_claim_label(title),
                                callback_data=f"qcl:{row.quest_key}",
                            ),
                        ],
                    )
                else:
                    lines.append(f"⚔️ <b>{html.escape(title)}</b> — побед: <b>{k}/{need}</b>")
            else:
                if p.get("pending_claim"):
                    lines.append(f"✅ <b>{html.escape(title)}</b> — <b>готово</b>, забирай награду!")
                    rows_btn.append(
                        [
                            InlineKeyboardButton(
                                text=_btn_claim_label(title),
                                callback_data=f"qcl:{row.quest_key}",
                            ),
                        ],
                    )
                else:
                    cur = int(p.get("current", 0))
                    need = int(p.get("target_count", 1))
                    lines.append(f"⚔️ <b>{html.escape(title)}</b> — <b>{cur}/{need}</b>")

        if pages > 1:
            nav2: list[InlineKeyboardButton] = []
            if page > 0:
                nav2.append(InlineKeyboardButton(text="◀️", callback_data=f"qhub:a:{page - 1}"))
            nav2.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="qhub:noop"))
            if page < pages - 1:
                nav2.append(InlineKeyboardButton(text="▶️", callback_data=f"qhub:a:{page + 1}"))
            rows_btn.append(nav2)

    rows_btn.append([InlineKeyboardButton(text="📅 Ежедневные задания", callback_data="qhub:d")])
    rows_btn.append([InlineKeyboardButton(text="📋 К этажу", callback_data="qhub:p:0")])
    rows_btn.append([InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows_btn)


async def render_daily_quests_hub(char: Character) -> tuple[str, InlineKeyboardMarkup]:
    """Экран ежедневных заданий."""
    text = dqs.format_daily_quests_html(char)
    rows: list[list[InlineKeyboardButton]] = []

    # Кнопки «Забрать» для выполненных заданий
    claim_rows = dqs.daily_quest_keyboard_rows(char, int(char.floor_number))
    rows.extend(claim_rows)

    if fb.wanderer_content_unlocked(char) and fb.wanderer_daily_tip_available(char):
        rows.append(
            [InlineKeyboardButton(text="🧙 Совет Странника (раз в сутки)", callback_data="qd:wand")],
        )
    if fb.can_show_legendary_2500_quest(char):
        rows.append(
            [InlineKeyboardButton(text="🌟 Легендарный завет (один раз)", callback_data="qd:leg")],
        )

    # Навигация
    rows.append([
        InlineKeyboardButton(text="📋 Задания этажа", callback_data="qhub:p:0"),
    ])
    rows.append([InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


async def render_quests_hub(session: AsyncSession, char: Character) -> tuple[str, InlineKeyboardMarkup]:
    """Совместимость: первый экран заданий этажа."""
    return await render_quest_floor_hub(session, char, 0)


@router.message(Command("quests", "задания"))
async def cmd_quests(message: Message, session: AsyncSession) -> None:
    try:
        if message.from_user is None:
            return
        user = await user_repo.get_by_telegram_id(session, message.from_user.id)
        if user is None or user.is_banned:
            await message.answer("Нет доступа.")
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await message.answer("Сначала /start.")
            return
        text, kb = await render_quest_floor_hub(session, char, 0)
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        logger.exception("cmd_quests")
        await message.answer("Ошибка.")


@router.callback_query(F.data == "qhub:noop")
async def quests_hub_noop(query: CallbackQuery) -> None:
    await query.answer()


@router.callback_query(F.data == "qhub:d")
async def quests_hub_daily(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Экран ежедневных заданий."""
    try:
        if query.message is None or query.from_user is None:
            await query.answer()
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        text, kb = await render_daily_quests_hub(char)
        await push_game_ui(
            state, query.bot,
            chat_id=query.message.chat.id,
            text=text, reply_markup=kb,
            target_message=query.message,
        )
        await query.answer()
    except Exception:
        logger.exception("qhub:d")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.regexp(r"^qdcl:\d+$"))
async def on_daily_quest_claim(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Получение награды за ежедневное задание."""
    try:
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        slot = int(query.data.split(":")[1])
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return

        ok, msg = await dqs.claim_quest(session, char, slot)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return

        # Сохранить награду до ответа Telegram: иначе при ошибке edit/длины текста
        # middleware откатит транзакцию — кнопка снова даст дублирующую награду.
        await session.commit()

        try:
            await query.answer("🎁 Награда получена!")
            text, kb = await render_daily_quests_hub(char)
            reward_block = f"{msg}\n\n{LINE_SEP}\n{text}"
            if len(reward_block) > 4000:
                reward_block = text
            await push_game_ui(
                state, query.bot,
                chat_id=query.message.chat.id,
                text=reward_block,
                reply_markup=kb,
                target_message=query.message,
            )
        except Exception:
            logger.exception("qdcl: ui after claim (награда уже в БД)")
            try:
                await query.answer("🎁 Награда зачислена. Обнови экран заданий.", show_alert=True)
            except Exception:
                pass
    except Exception:
        logger.exception("qdcl")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "qd:wand")
async def on_wanderer_tip(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if query.message is None or query.from_user is None:
            await query.answer()
            return
        u = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if u is None or u.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, u.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = fb.claim_wanderer_daily_tip(char)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        await session.commit()
        text, kb = await render_daily_quests_hub(char)
        block = f"{msg}\n\n{LINE_SEP}\n{text}"
        try:
            await query.answer("Готово.")
            await push_game_ui(
                state, query.bot,
                chat_id=query.message.chat.id,
                text=block,
                reply_markup=kb,
                target_message=query.message,
            )
        except Exception:
            logger.exception("qd:wand ui")
    except Exception:
        logger.exception("qd:wand")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "qd:leg")
async def on_legendary_2500(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if query.message is None or query.from_user is None:
            await query.answer()
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None:
            await query.answer()
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Нет персонажа.", show_alert=True)
            return
        ok, msg = await fb.complete_legendary_2500_quest(session, char)
        if not ok:
            await query.answer(msg[:200], show_alert=True)
            return
        await session.commit()
        text, kb = await render_daily_quests_hub(char)
        block = f"{msg}\n\n{LINE_SEP}\n{text}"
        try:
            await query.answer("🌟 Навсегда в летописи.")
            await push_game_ui(
                state, query.bot,
                chat_id=query.message.chat.id,
                text=block,
                reply_markup=kb,
                target_message=query.message,
            )
        except Exception:
            logger.exception("qd:leg ui")
    except Exception:
        logger.exception("qd:leg")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "qhub:")
@router.callback_query(F.data.regexp(r"^qhub:p:\d+$"))
@router.callback_query(F.data.regexp(r"^qhub:a:\d+$"))
@router.callback_query(F.data == "qhub:back")
async def quests_hub_callbacks(
    query: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        if query.message is None or query.from_user is None:
            await query.answer()
            return
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return

        data = query.data or ""
        if data == "qhub:":
            mode, pg = "p", 0
        elif data.startswith("qhub:p:"):
            mode, pg = "p", int(data.split(":")[2])
        elif data.startswith("qhub:a:"):
            mode, pg = "a", int(data.split(":")[2])
        else:
            await query.answer()
            return

        if mode == "p":
            text, kb = await render_quest_floor_hub(session, char, pg)
        else:
            text, kb = await render_active_quests_overview(session, char, pg)

        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=text,
            reply_markup=kb,
            target_message=query.message,
        )
        await query.answer()
    except Exception:
        logger.exception("qhub")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("qtk:"))
async def on_quest_take(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        key = query.data.split(":", 1)[1]
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return
        ok, msg = await quest_service.take_quest(session, char, key)
        if not ok:
            await query.answer(_strip_html_alert(msg)[:180], show_alert=True)
            return
        await query.answer("Поручение принято.")
        hub_text, kb = await render_quest_floor_hub(session, char, 0)
        combined = f"{msg.rstrip()}\n\n{hub_text}"
        if len(combined) > 3800:
            combined = hub_text
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=combined,
            reply_markup=kb,
            target_message=query.message,
        )
    except Exception:
        logger.exception("qtk")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("qcl:"))
async def on_quest_claim(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    try:
        if await state.get_state() == CombatStates.in_battle.state:
            await query.answer("Сначала заверши бой.", show_alert=True)
            return
        if query.data is None or query.from_user is None or query.message is None:
            await query.answer()
            return
        key = query.data.split(":", 1)[1]
        user = await user_repo.get_by_telegram_id(session, query.from_user.id)
        if user is None or user.is_banned:
            await query.answer("Нет доступа.", show_alert=True)
            return
        char = await character_repo.get_by_user_id(session, user.id)
        if char is None:
            await query.answer("Сначала /start.", show_alert=True)
            return

        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text="🎉 <b>Задание выполнено!</b>",
            reply_markup=None,
            target_message=query.message,
        )
        await asyncio.sleep(0.8)

        res = await quest_service.claim_quest_reward(session, char, key)
        if not res.get("ok"):
            await query.answer(str(res.get("error", "Нельзя")), show_alert=True)
            text, kb = await render_quest_floor_hub(session, char, 0)
            await push_game_ui(
                state,
                query.bot,
                chat_id=query.message.chat.id,
                text=text,
                reply_markup=kb,
                target_message=query.message,
            )
            return

        parts = [
            f"💰 +{res['gold']} золота",
            f"✨ +{res['exp']} опыта",
        ]
        if res.get("item"):
            parts.append("📦 Редкий предмет в сумку!")
        if int(res.get("rune_stones") or 0) > 0:
            parts.append(f"⚗️ +{res['rune_stones']} рунных камней")
        body = "🎁 " + "  ".join(parts) + str(res.get("level_up_html") or "")
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Задания", callback_data="qhub:p:0")],
                [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")],
            ],
        )
        await push_game_ui(
            state,
            query.bot,
            chat_id=query.message.chat.id,
            text=body,
            reply_markup=kb,
            target_message=query.message,
        )
        await query.answer("Награда получена.")
    except Exception:
        logger.exception("qcl")
        await query.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("qst:"))
async def on_quest_callback(
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

        m = _QST_CB.match(query.data)
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

        if floor != char.floor_number:
            await query.answer("Этаж устарел. Открой /floor.", show_alert=True)
            return

        if not floor_data.has_quest_npc(floor):
            await query.answer("Здесь нет странника.", show_alert=True)
            return

        chat_id = query.message.chat.id

        if code == "back":
            await push_game_ui(
                state,
                query.bot,
                chat_id=chat_id,
                text=format_floor_message(char),
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer()
            return

        if code == "view":
            tpl = npc_quest_template(floor)
            if tpl is None:
                await query.answer("Нет квеста.", show_alert=True)
                return
            row = await quest_repo.get_by_key(session, char.id, tpl.quest_key)
            if row is None:
                intro = quest_service.format_quest_intro_html(floor)
                if intro is None:
                    await query.answer("Нет квеста.", show_alert=True)
                    return
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=chat_id,
                    text=intro,
                    reply_markup=quest_dialog_keyboard(floor),
                    target_message=query.message,
                )
            elif row.status == "completed":
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=chat_id,
                    text=(
                        f"📜 <b>{html.escape(tpl.title)}</b>\n"
                        "Странник кивает: долг на этом этаже уже исполнен."
                    ),
                    reply_markup=quest_back_keyboard(floor),
                    target_message=query.message,
                )
            else:
                p = dict(row.progress or {})
                k = int(p.get("kills", 0))
                need = int(p.get("need", tpl.kills_needed))
                await push_game_ui(
                    state,
                    query.bot,
                    chat_id=chat_id,
                    text=(
                        f"📜 <b>{html.escape(tpl.title)}</b>\n"
                        f"Прогресс: побед — <b>{k}/{need}</b>.\n"
                        "Продолжай сражаться на башне."
                    ),
                    reply_markup=quest_back_keyboard(floor),
                    target_message=query.message,
                )
            await query.answer()
            return

        if code == "acc":
            ok, msg = await quest_service.try_accept_quest(session, char, floor)
            if not ok:
                await query.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
                return
            await push_game_ui(
                state,
                query.bot,
                chat_id=chat_id,
                text=msg,
                reply_markup=await floor_keyboard_for_character(session, char, telegram_user_id=query.from_user.id),
                target_message=query.message,
            )
            await query.answer("Квест обновлён.")
            return

        await query.answer()
    except Exception:
        logger.exception("Ошибка в callback квеста")
        await query.answer("Ошибка.", show_alert=True)
