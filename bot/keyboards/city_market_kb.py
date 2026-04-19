"""Рынок городского хаба на 3 этаже."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters.player_skills import (
    SKILL_BY_KEY,
    TEMPLE_SKILL_PRICES_GOLD,
    learned_skill_keys,
)


def city_floor3_market_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    f = int(floor_number)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏪 Лавка торговца", callback_data=f"shp:main:{f}:m")],
            [InlineKeyboardButton(text="💰 Скупщик", callback_data=f"cty:mkt:{f}:scrap")],
            [InlineKeyboardButton(text="🏦 Банк (сейф)", callback_data=f"ecy:sfv:{f}:mkt")],
            [InlineKeyboardButton(text="⛪ Храм призыва", callback_data=f"cty:mkt:{f}:temple")],
            [InlineKeyboardButton(text="📜 Школа навыков", callback_data=f"cty:mkt:{f}:skills")],
            [InlineKeyboardButton(text="⬅ В город", callback_data=f"cty:mkt:{f}:hub")],
            menu_nav_button_row(),
        ],
    )


def temple_floor3_keyboard(floor_number: int, *, can_reroll: bool) -> InlineKeyboardMarkup:
    f = int(floor_number)
    row2: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="✅ Принять дар", callback_data=f"cty:mkt:{f}:temple_acc"),
    ]
    if can_reroll:
        row2.append(InlineKeyboardButton(text="🔁 Переброс", callback_data=f"cty:mkt:{f}:temple_rer"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row2,
            [InlineKeyboardButton(text="⬅ На рынок", callback_data=f"cty:mkt:{f}:open")],
            menu_nav_button_row(),
        ],
    )


def temple_skills_shop_keyboard(floor_number: int, character: Character) -> InlineKeyboardMarkup:
    """Покупка навыков за золото (деревня, 3 этаж)."""
    f = int(floor_number)
    learned = learned_skill_keys(character)
    rows: list[list[InlineKeyboardButton]] = []
    for key in sorted(TEMPLE_SKILL_PRICES_GOLD.keys()):
        price = TEMPLE_SKILL_PRICES_GOLD[key]
        sk = SKILL_BY_KEY.get(key)
        if sk is None:
            continue
        name = str(sk.name)[:20]
        if key in learned:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"✓ {name}",
                        callback_data=f"cty:skillhave:{f}:{key}",
                    ),
                ],
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{name} · {price}💰",
                        callback_data=f"cty:skillbuy:{f}:{key}",
                    ),
                ],
            )
    rows.append([InlineKeyboardButton(text="⬅ На рынок", callback_data=f"cty:mkt:{f}:open")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_skills_pick_keyboard(*, slot: int, learned_keys: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for k in learned_keys:
        sk = SKILL_BY_KEY.get(k)
        if sk is None:
            continue
        row.append(
            InlineKeyboardButton(
                text=str(sk.name)[:18],
                callback_data=f"prf:sk_eq:{slot}:{k}",
            ),
        )
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="prf:skills")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_skills_main_keyboard(*, locale: str) -> InlineKeyboardMarkup:
    from bot.i18n import t

    loc = locale if locale in ("ru", "en") else "ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(loc, "skills_slot_btn", n=1), callback_data="prf:sk_slot:0"),
                InlineKeyboardButton(text=t(loc, "skills_slot_btn", n=2), callback_data="prf:sk_slot:1"),
                InlineKeyboardButton(text=t(loc, "skills_slot_btn", n=3), callback_data="prf:sk_slot:2"),
            ],
            [InlineKeyboardButton(text=t(loc, "profile_back_compact"), callback_data="prf:back")],
            menu_nav_button_row(),
        ],
    )
