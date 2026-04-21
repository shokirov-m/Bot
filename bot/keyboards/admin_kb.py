"""Инлайн-клавиатура админ-панели."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Сколько имён на одной странице списка (лимит кнопок и длины сообщения).
ADMIN_PLAYERS_PAGE_SIZE = 8


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Сводка", callback_data="adm:stats"),
                InlineKeyboardButton(text="👤 Игрок", callback_data="adm:user"),
            ],
            [
                InlineKeyboardButton(text="💰 Выдать золото", callback_data="adm:give"),
                InlineKeyboardButton(text="📜 Логи", callback_data="adm:logs"),
            ],
            [
                InlineKeyboardButton(text="📋 Логи (все)", callback_data="adm:logs_all"),
                InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm:promo"),
            ],
            [
                InlineKeyboardButton(text="🚫 Бан", callback_data="adm:ban"),
                InlineKeyboardButton(text="✅ Разбан", callback_data="adm:unban"),
            ],
            [
                InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast"),
            ],
            [
                InlineKeyboardButton(text="👥 Рефералы (по кого сколько)", callback_data="adm:referrals"),
            ],
            [
                InlineKeyboardButton(text="🧙 Все игроки", callback_data="adm:players"),
            ],
            [
                InlineKeyboardButton(text="📈 Уровень по Telegram ID", callback_data="adm:lv_id"),
            ],
            [
                InlineKeyboardButton(text="🗑 Очистить инвентарь", callback_data="adm:clear_inv"),
            ],
        ],
    )


def admin_players_browser_keyboard(
    entries: list[tuple[int, str, int, bool]],
    *,
    page: int,
    page_size: int,
    total_entries: int,
) -> InlineKeyboardMarkup:
    """
    entries: (character_id, display_name, level, is_banned).
    callback на игрока: adm:pv:<char_id>:<page> (чтобы вернуться на ту же страницу).
    """
    rows: list[list[InlineKeyboardButton]] = []
    for cid, dname, lvl, banned in entries:
        prefix = "🚫 " if banned else ""
        raw = f"{prefix}Lv{lvl} {dname}"
        if len(raw) > 58:
            raw = raw[:55] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=raw,
                    callback_data=f"adm:pv:{cid}:{page}",
                ),
            ],
        )
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Стр.", callback_data=f"adm:pl:{page - 1}"))
    if (page + 1) * page_size < total_entries:
        nav.append(InlineKeyboardButton(text="Стр. ▶️", callback_data=f"adm:pl:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ В панель", callback_data="adm:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_player_snapshot_keyboard(*, character_id: int, return_page: int) -> InlineKeyboardMarkup:
    """
    Карточка игрока: возврат + выдача уровня короткими callback (лимит 64 байта).
    adm:lvw:<id>:<page>:<delta> — добавить delta уровней (1, 5, 10).
    adm:lvs:<id>:<page>:<lvl> — поднять до уровня lvl (не ниже текущего).
    """
    cid = int(character_id)
    pg = int(return_page)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ +1 ур.", callback_data=f"adm:lvw:{cid}:{pg}:1"),
                InlineKeyboardButton(text="➕ +5 ур.", callback_data=f"adm:lvw:{cid}:{pg}:5"),
                InlineKeyboardButton(text="➕ +10 ур.", callback_data=f"adm:lvw:{cid}:{pg}:10"),
            ],
            [
                InlineKeyboardButton(text="🎯 До 25 ур.", callback_data=f"adm:lvs:{cid}:{pg}:25"),
                InlineKeyboardButton(text="🎯 До 50 ур.", callback_data=f"adm:lvs:{cid}:{pg}:50"),
                InlineKeyboardButton(text="🎯 До 100 ур.", callback_data=f"adm:lvs:{cid}:{pg}:100"),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К списку игроков",
                    callback_data=f"adm:pl:{pg}",
                ),
            ],
            [
                InlineKeyboardButton(text="⬅️ В панель", callback_data="adm:hub"),
            ],
        ],
    )


def admin_promo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📃 Список", callback_data="adm:promo_list"),
                InlineKeyboardButton(text="❓ Справка add", callback_data="adm:promo_help"),
            ],
            [
                InlineKeyboardButton(text="✏️ Ввод команды promo", callback_data="adm:promo_cmd"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В панель", callback_data="adm:hub"),
            ],
        ],
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✖️ Отмена", callback_data="adm:cancel"),
            ],
        ],
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ В панель", callback_data="adm:hub"),
            ],
        ],
    )
