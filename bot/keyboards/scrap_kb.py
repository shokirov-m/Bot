"""Клавиатура скупщика (этаж 3): продать предмет по id."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.inventory import InventoryItem
from db.models.character import Character
from game.items.equipment import gear_icon_for_item_data

SCRAP_BACK_META = "_scrap_ui_back_v1"
SCRAP_PAGE_SIZE = 18


def set_scrap_ui_back(character: Character, mode: str) -> None:
    mp = dict(character.meta_progress or {})
    mp[SCRAP_BACK_META] = mode if mode in ("floor", "mkt") else "floor"
    character.meta_progress = mp


def scrap_ui_back(character: Character) -> str:
    mp = dict(character.meta_progress or {})
    v = str(mp.get(SCRAP_BACK_META) or "floor")
    return v if v in ("floor", "mkt") else "floor"


def scrap_merchant_keyboard(
    items: list[InventoryItem],
    *,
    back: str = "floor",
    page: int = 1,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    sellable = []
    for it in items:
        d = dict(it.item_data or {})
        if str(d.get("kind") or "").lower().strip() == "craft_resource":
            continue
        sellable.append(it)

    total = len(sellable)
    total_pages = max(1, (total + SCRAP_PAGE_SIZE - 1) // SCRAP_PAGE_SIZE)
    p = max(1, min(int(page), total_pages))
    start = (p - 1) * SCRAP_PAGE_SIZE
    cut = sorted(sellable, key=lambda x: (x.bag_slot or 0))[start : start + SCRAP_PAGE_SIZE]

    for it in cut:
        d = dict(it.item_data or {})
        gi = gear_icon_for_item_data(d)
        nm = str(d.get("name", "Предмет"))
        if len(nm) > 18:
            nm = nm[:15] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{gi}💰 {nm}"[:64],
                    callback_data=f"scr:sell:{int(it.id)}:{p}",
                ),
            ],
        )

    if total_pages > 1:
        prev_p = max(1, p - 1)
        next_p = min(total_pages, p + 1)
        nav = [
            InlineKeyboardButton(
                text="⬅️" if p > 1 else " ",
                callback_data=f"scr:pg:{prev_p}" if p > 1 else "scr:pg:1",
            ),
            InlineKeyboardButton(text=f"{p}/{total_pages}", callback_data=f"scr:pg:{p}"),
            InlineKeyboardButton(
                text="➡️" if p < total_pages else " ",
                callback_data=f"scr:pg:{next_p}" if p < total_pages else f"scr:pg:{total_pages}",
            ),
        ]
        rows.append(nav)

    back_cd = "scr:backmkt" if back == "mkt" else "scr:back"
    back_lbl = "⬅️ На рынок" if back == "mkt" else "⬅️ К этажу"
    rows.append([InlineKeyboardButton(text=back_lbl, callback_data=back_cd)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
