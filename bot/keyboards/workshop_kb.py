"""Мастерская: inline-кнопки."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def workshop_main_keyboard(locale: str = "ru") -> InlineKeyboardMarkup:
    _ = locale
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚒️ Кузница", callback_data="wsp:prof:blacksmith"),
                InlineKeyboardButton(text="⚗️ Лаборатория", callback_data="wsp:prof:alchemist"),
            ],
            [
                InlineKeyboardButton(text="💎 Ювелирная", callback_data="wsp:prof:jeweler"),
            ],
            [
                InlineKeyboardButton(text="📜 Очередь / забрать", callback_data="wsp:queue"),
            ],
            [
                InlineKeyboardButton(text="🏆 Рейтинг мастеров", callback_data="wsp:lb"),
            ],
            [
                InlineKeyboardButton(text="📖 Справочник крафта", callback_data="wsp:cat:menu"),
            ],
            menu_nav_button_row(),
        ],
    )


def workshop_prof_keyboard(
    profession: str,
    *,
    page: int,
    recipe_rows: list[tuple[str, str]],
    total_count: int,
    per_page: int = 8,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for rid, label in recipe_rows[:per_page]:
        short = label if len(label) <= 40 else label[:37] + "…"
        rows.append([InlineKeyboardButton(text=short, callback_data=f"wsp:rcp:{profession}:{rid}")])
    max_page = max(0, (max(0, total_count) - 1) // per_page)
    p = max(0, min(int(page), max_page))
    nav: list[InlineKeyboardButton] = []
    if max_page > 0:
        if p > 0:
            nav.append(
                InlineKeyboardButton(text="◀", callback_data=f"wsp:profpage:{profession}:{p - 1}"),
            )
        nav.append(InlineKeyboardButton(text=f"{p + 1}/{max_page + 1}", callback_data="wsp:noop"))
        if p < max_page:
            nav.append(
                InlineKeyboardButton(text="▶", callback_data=f"wsp:profpage:{profession}:{p + 1}"),
            )
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_queue_keyboard(
    entries: list[tuple[str, str, bool]],
) -> InlineKeyboardMarkup:
    """ (slot_id, label, ready) """
    rows: list[list[InlineKeyboardButton]] = []
    for sid, lab, ready in entries:
        if ready:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data=f"wsp:claim:{sid}",
                    ),
                ],
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data="wsp:noop",
                    ),
                ],
            )
    rows.append([InlineKeyboardButton(text="⬅ Мастерская", callback_data="wsp:hub")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshop_station_keyboard(profession: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔧 Улучшить станок",
                    callback_data=f"wsp:upg:{profession}",
                ),
            ],
            [InlineKeyboardButton(text="⬅ Назад", callback_data=f"wsp:prof:{profession}")],
            menu_nav_button_row(),
        ],
    )


def city_workshop_orders_keyboard(*, floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 Разместить заказ", callback_data=f"wso:new:{f}")],
            [InlineKeyboardButton(text="📋 Все заказы", callback_data=f"wso:list:{f}")],
            [InlineKeyboardButton(text="⬅ Город", callback_data=f"frg:city:{f}")],
            menu_nav_button_row(),
        ],
    )


def workshop_orders_list_keyboard(
    floor_number: int,
    rows: list[tuple[int, str, int]],
    *,
    crafter: bool,
) -> InlineKeyboardMarkup:
    """rows: (order_id, label, escrow)"""
    btns: list[list[InlineKeyboardButton]] = []
    for oid, lab, _ in rows[:10]:
        if crafter:
            btns.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data=f"wso:take:{floor_number}:{oid}",
                    ),
                ],
            )
        else:
            btns.append(
                [
                    InlineKeyboardButton(
                        text=lab[:58],
                        callback_data=f"wso:noop:{oid}",
                    ),
                ],
            )
    btns.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"wso:open:{floor_number}")])
    btns.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=btns)
