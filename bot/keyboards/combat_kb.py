"""Клавиатура боя (ТЗ 1.4)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models.inventory import InventoryItem
from game.characters.skills import skills_for_class


def combat_main_keyboard(class_key: str) -> InlineKeyboardMarkup:
    """Четыре действия + три скилла вторым рядом (компактно: скиллы одной строкой нельзя — 2+1)."""
    sk = skills_for_class(class_key)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚔️ Атака", callback_data="cb:atk"),
                InlineKeyboardButton(text="🏃 Бежать", callback_data="cb:run"),
            ],
            [
                InlineKeyboardButton(text=f"🔮 {sk[0].name[:15]}", callback_data="cb:sk:0"),
                InlineKeyboardButton(text=f"🔮 {sk[1].name[:15]}", callback_data="cb:sk:1"),
            ],
            [
                InlineKeyboardButton(text=f"🔮 {sk[2].name[:15]}", callback_data="cb:sk:2"),
            ],
            [
                InlineKeyboardButton(text="🎒 Предмет", callback_data="cb:item"),
            ],
        ],
    )


def combat_item_picker_keyboard(bag_items: list[InventoryItem]) -> InlineKeyboardMarkup:
    """Список расходников для боя + отмена."""
    rows: list[list[InlineKeyboardButton]] = []
    for it in bag_items[:20]:
        data = it.item_data or {}
        name = str(data.get("name", "?"))[:22]
        rows.append(
            [InlineKeyboardButton(text=f"🧪 {name}", callback_data=f"cb:itm:{it.id}")],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ В бой", callback_data="cb:ret")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
