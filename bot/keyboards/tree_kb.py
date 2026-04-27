"""
Keyboards for the Skill Tree system 2.0.
"""
from __future__ import annotations
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from game.archetypes.models import SkillTreeNode
from game.archetypes import manager as arch_manager
from db.models.character import Character

def skill_tree_keyboard(character: Character, locale: str = "ru") -> InlineKeyboardMarkup:
    """Renders the skill tree as a list of buttons."""
    tree = arch_manager.get_character_tree(character)
    unlocked = arch_manager.get_unlocked_node_keys(character)
    sp = arch_manager.get_character_sp(character)
    
    rows: list[list[InlineKeyboardButton]] = []
    
    # Header showing SP
    rows.append([InlineKeyboardButton(text=f"✨ Очки навыков: {sp}", callback_data="inv:noop")])
    
    # Filter nodes into branches (optional, for now just list them)
    # We'll group them by their parent status to show a logical order
    
    # Sort nodes to keep them consistent
    sorted_keys = sorted(tree.keys())
    
    for key in sorted_keys:
        node = tree[key]
        is_unlocked = key in unlocked
        
        # Check if can be unlocked
        can_unlock = not is_unlocked and all(p in unlocked for p in node.parent_keys)
        
        prefix = "✅ " if is_unlocked else ("🌟 " if can_unlock else "🔒 ")
        
        btn_text = f"{prefix}{node.name_ru}"
        rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"tree:view:{key}")])
        
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prf:spec")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def node_action_keyboard(node_key: str, can_buy: bool, *, cost_sp: int = 1) -> InlineKeyboardMarkup:
    """Buttons for buying or going back from a node view."""
    buttons = []
    if can_buy:
        buttons.append(
            InlineKeyboardButton(
                text=f"💎 Изучить ({cost_sp} SP)",
                callback_data=f"tree:buy:{node_key}",
            ),
        )

    buttons.append(InlineKeyboardButton(text="⬅️ К древу", callback_data="prf:skills"))

    return InlineKeyboardMarkup(inline_keyboard=[buttons])
