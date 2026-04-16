"""Лавка торговца."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.economy.shop import shop_goods_for_floor


def shop_main_keyboard(floor_number: int, origin: str) -> InlineKeyboardMarkup:
    """origin: c — из города, f — с этажа (5,10,15…)."""
    back_cd = f"frg:city:{floor_number}" if origin == "c" else f"fl:{floor_number}:return"
    rows: list[list[InlineKeyboardButton]] = []
    for g in shop_goods_for_floor(floor_number):
        label = f"{g.emoji} {g.name} — {g.price}💰"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"shp:buy:{floor_number}:{g.key}:{origin}",
                ),
            ],
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="🥖 Съесть паёк (+2⚡)",
                callback_data=f"shp:eat:{floor_number}:{origin}",
            ),
        ],
    )
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cd)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
