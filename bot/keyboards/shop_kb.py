"""Лавка торговца — обычный и VIP (Stars) разделы."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from game.economy.shop import VIP_STAR_GOODS, shop_goods_for_floor


def shop_main_keyboard(floor_number: int, origin: str) -> InlineKeyboardMarkup:
    """
    Обычный магазин — расходники за золото.
    origin: c — из города, f — с этажа, m — с рынка хаба, h — из дома, u — из меню.
    """
    if origin == "a":
        back_cd = "auc:hub"
    elif origin == "u":
        back_cd = "mnu:hub"
    elif origin == "h":
        back_cd = "hom:hub"
    elif origin == "m":
        back_cd = f"cty:mkt:{floor_number}:open"
    elif origin == "c":
        back_cd = f"frg:city:{floor_number}"
    else:
        back_cd = f"fl:{floor_number}:return"

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
                text="⭐ VIP-магазин (Telegram Stars)",
                callback_data=f"shp:vip:{floor_number}:{origin}",
            ),
        ],
    )
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cd)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shop_vip_keyboard(floor_number: int, origin: str) -> InlineKeyboardMarkup:
    """VIP-магазин — облики за Telegram Stars."""
    rows: list[list[InlineKeyboardButton]] = []
    for g in VIP_STAR_GOODS:
        label = f"{g.emoji} {g.name} — {g.stars_price} ⭐"
        if len(label) > 64:
            label = label[:61] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"auc:vpr:{floor_number}:{g.key}:{origin}",
                ),
            ],
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅ Обычный магазин",
                callback_data=f"shp:main:{floor_number}:{origin}",
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
