"""Таверна: меню покупок."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.locations.tavern import TAVERN_MENU


def tavern_menu_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for o in TAVERN_MENU:
        label = f"{o.emoji} {o.name} — {o.price}💰"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"tvr:buy:{floor_number}:{o.key}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="🪙 Скупщик Орин", callback_data=f"tvr:buyer:{floor_number}")],
    )
    rows.append(
        [InlineKeyboardButton(text="⬅ В город", callback_data=f"frg:city:{floor_number}")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buyer_quest_keyboard(floor_number: int, state: dict) -> InlineKeyboardMarkup:
    """Клавиатура экрана скупщика."""
    rows: list[list[InlineKeyboardButton]] = []

    if not state:
        rows.append([InlineKeyboardButton(
            text="🪙 Взяться за поручения",
            callback_data=f"tvr:bq:start:{floor_number}",
        )])
    else:
        final_claimed = state.get("final_claimed", False)
        if not final_claimed:
            for s in (1, 2, 3):
                if state.get(f"{s}_done") and not state.get(f"{s}_claimed"):
                    rows.append([InlineKeyboardButton(
                        text=f"✅ Сдать шаг {s}",
                        callback_data=f"tvr:bq:claim:{floor_number}:{s}",
                    )])
                    break
            if all(state.get(f"{s}_claimed") for s in (1, 2, 3)) and not final_claimed:
                rows.append([InlineKeyboardButton(
                    text="🏆 Получить финальный товар",
                    callback_data=f"tvr:bq:final:{floor_number}",
                )])

    rows.append([InlineKeyboardButton(text="⬅ Таверна", callback_data=f"tvr:open:{floor_number}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
