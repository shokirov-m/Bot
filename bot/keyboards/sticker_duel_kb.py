"""Клавиатуры карточной арены (меню «Локации»)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t
from config import settings
from game.tower_cards import monster_cards as tc
from services import sticker_duel_service


def sticker_hub_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:
    loc = "ru"
    cost = int(settings.STICKER_GACHA_GOLD_PULL)
    stars = int(getattr(settings, "STICKER_GACHA_STARS_PULL", 0) or 0)
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t(loc, "sticker_kb_free"), callback_data="stk:sp:f")],
        [
            InlineKeyboardButton(
                text=t(loc, "sticker_kb_gold", gold=cost),
                callback_data="stk:sp:p",
            ),
        ],
    ]
    if stars > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(loc, "sticker_kb_stars", stars=stars),
                    callback_data="stk:sp:s",
                ),
            ],
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(text=t(loc, "sticker_kb_album"), callback_data="stk:alb"),
                InlineKeyboardButton(text=t(loc, "sticker_kb_top"), callback_data="stk:top"),
            ],
            [
                InlineKeyboardButton(text=t(loc, "sticker_kb_preview"), callback_data="stk:tc"),
                InlineKeyboardButton(text=t(loc, "sticker_kb_preview_info"), callback_data="stk:tc:i"),
            ],
            [InlineKeyboardButton(text=t(loc, "sticker_kb_duel"), callback_data="stk:duel")],
            [InlineKeyboardButton(text=t(loc, "sticker_kb_back_loc"), callback_data="mnu:loc")],
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sticker_pick_keyboard(
    *,
    character,
    defender_code: str | None = None,
    locale: str = "ru",
) -> InlineKeyboardMarkup | None:
    """defender_code задан → callback stk:ac:CODE:sid (ответ на вызов)."""
    loc = "ru"
    coll = sticker_duel_service.collection_map(character)
    if not coll:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    dc = defender_code.strip().upper()[:16] if defender_code else None
    for sid in sorted(coll.keys()):
        row_d = coll[sid]
        nm = str(row_d.get("name_ru", sid))
        label = (nm[:14] + "…") if len(nm) > 15 else nm
        stars = tc.RARITY_STARS_RU.get(str(row_d.get("rarity", "common")), "")
        if dc:
            cd = f"stk:ac:{dc}:{sid}"[:64]
        else:
            cd = f"stk:at:{sid}"[:64]
        row.append(InlineKeyboardButton(text=f"{stars} {label}"[:28], callback_data=cd))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(loc, "sticker_kb_cancel"), callback_data="mnu:stk")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def defender_pick_keyboard(code: str, character, *, locale: str = "ru") -> InlineKeyboardMarkup | None:
    return sticker_pick_keyboard(character=character, defender_code=code, locale=locale)
