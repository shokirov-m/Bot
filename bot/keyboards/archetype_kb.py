"""
Keyboards for Archetype selection 2.0.
"""
from __future__ import annotations
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from game.archetypes.data import ARCHETYPES

def archetype_selection_keyboard(*, tier: int = 1, allowed_keys: list[str] | None = None) -> InlineKeyboardMarkup:
    """Buttons for archetypes of the requested tier."""
    rows: list[list[InlineKeyboardButton]] = []
    allowed = set(allowed_keys or [])
    choices = [a for a in ARCHETYPES.values() if a.tier == int(tier)]
    if allowed:
        choices = [a for a in choices if a.key in allowed]
    for arch in choices:
        rows.append([InlineKeyboardButton(
            text=f"👁 {arch.emoji} {arch.name_ru}",
            callback_data=f"arch:view:{arch.key}"
        )])
    
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prf:spec")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def archetype_confirm_keyboard(arch_key: str) -> InlineKeyboardMarkup:
    """Confirmation button for a specific archetype."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выбрать этот путь", callback_data=f"arch:confirm:{arch_key}"),
                InlineKeyboardButton(text="⬅️ К списку", callback_data="prf:arch_pick"),
            ]
        ]
    )
