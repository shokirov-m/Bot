"""Золотые sinks в городском хабе (колбэки ecy:*)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row


def economy_hub_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🎰 Лотерея", callback_data=f"ecy:lot:{f}")],
        [
            InlineKeyboardButton(text="💰 Займ", callback_data=f"ecy:mlb:{f}"),
            InlineKeyboardButton(text="📉 Платёж", callback_data=f"ecy:mlr:{f}"),
        ],
        [InlineKeyboardButton(text="🏦 Сейф банка", callback_data=f"ecy:sfv:{f}")],
        [InlineKeyboardButton(text="🛒 Магазин игроков", callback_data="auc:hub")],
        [InlineKeyboardButton(text="⬅ В город", callback_data=f"ecy:back:{f}")],
        menu_nav_button_row(),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bank_safe_keyboard(
    floor_number: int,
    *,
    bank_back: str = "hub",
    has_term: bool = False,
    has_pending_interest: bool = False,
    seal_active: bool = False,
) -> InlineKeyboardMarkup:
    f = int(floor_number)
    back_cd = f"cty:mkt:{f}:open" if bank_back == "mkt" else f"ecy:hub:{f}"
    back_txt = "⬅ Рынок" if bank_back == "mkt" else "⬅ Экономика"
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="➕ 100", callback_data=f"ecy:sfd:{f}:100"),
            InlineKeyboardButton(text="➕ 500", callback_data=f"ecy:sfd:{f}:500"),
        ],
        [
            InlineKeyboardButton(text="➖ 100", callback_data=f"ecy:sfw:{f}:100"),
            InlineKeyboardButton(text="➖ 500", callback_data=f"ecy:sfw:{f}:500"),
        ],
        [InlineKeyboardButton(text="➕ Всё влезет", callback_data=f"ecy:sfd:{f}:0")],
        [InlineKeyboardButton(text="➖ Снять всё", callback_data=f"ecy:sfw:{f}:0")],
        [InlineKeyboardButton(text="⬆️ Улучшить хранилище", callback_data=f"ecy:sfu:{f}")],
    ]
    if has_pending_interest:
        rows.append([InlineKeyboardButton(text="💰 Забрать проценты", callback_data=f"ecy:sfi:{f}")])
    if not seal_active:
        rows.append([InlineKeyboardButton(text="📜 Купить «Банковскую печать»", callback_data=f"ecy:sfs:{f}")])
    if has_term:
        rows.append(
            [
                InlineKeyboardButton(text="🏁 Забрать вклад + проценты", callback_data=f"ecy:tcl:{f}:0"),
            ],
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="⛔ Разорвать досрочно (без процентов)",
                    callback_data=f"ecy:tcl:{f}:1",
                ),
            ],
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(text="⏳ Вклад 24ч (1%) — половина сейфа", callback_data=f"ecy:topn:{f}:24"),
                InlineKeyboardButton(text="⏳ 72ч (4%)", callback_data=f"ecy:topn:{f}:72"),
            ],
        )
        rows.append(
            [
                InlineKeyboardButton(text="⏳ 7 дней (12%)", callback_data=f"ecy:topn:{f}:168"),
            ],
        )
    rows.append([InlineKeyboardButton(text=back_txt, callback_data=back_cd)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
