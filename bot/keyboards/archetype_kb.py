"""
Keyboards for Archetype selection 2.0.
"""
from __future__ import annotations
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from game.archetypes.data import ARCHETYPES

def archetype_selection_keyboard() -> InlineKeyboardMarkup:
    """Buttons for Tier 1 archetypes."""
    rows: list[list[InlineKeyboardButton]] = []
    # Show Tier 1 archetypes
    tier1 = [a for a in ARCHETYPES.values() if a.tier == 1]
    for arch in tier1:
        rows.append([InlineKeyboardButton(
            text=f"{arch.emoji} {arch.name_ru}", 
            callback_data=f"arch:view:{arch.key}"
        )])
    
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prf:spec")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def archetype_confirm_keyboard(arch_key: str) -> InlineKeyboardMarkup:
    """Confirmation button for a specific archetype."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить выбор", callback_data=f"arch:confirm:{arch_key}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="prf:arch_pick"),
            ]
        ]
    )
