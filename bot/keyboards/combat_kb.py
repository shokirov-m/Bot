"""Клавиатура боя (ТЗ 1.4)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models.character import Character
from db.models.inventory import InventoryItem
from game.characters.player_skills import (
    battle_skills_tuple,
    ensure_skill_meta,
    skill_emoji,
)
from game.combat import consumables
from game.items.equipment import gear_icon_for_item_data
from utils.telegram.screen_style import truncate_button_label


def _skill_btn_label(sk) -> str:
    name = (sk.name or "").strip()
    return truncate_button_label(f"{skill_emoji(skill=sk)} {name}", 64)


def combat_boss_intro_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Напасть", callback_data="cb:boss_go")],
        ],
    )


def combat_coup_de_grace_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Добить", callback_data="cb:coup")],
        ],
    )


def combat_main_keyboard(character: Character) -> InlineKeyboardMarkup:
    """Четыре действия + три экипированных навыка + предмет."""
    ensure_skill_meta(character)
    sk = battle_skills_tuple(character)

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="⚔️ Атака", callback_data="cb:atk"),
            InlineKeyboardButton(text="🏃 Бежать", callback_data="cb:run"),
        ],
        [InlineKeyboardButton(text=_skill_btn_label(sk[0]), callback_data="cb:sk:0")],
        [InlineKeyboardButton(text=_skill_btn_label(sk[1]), callback_data="cb:sk:1")],
        [InlineKeyboardButton(text=_skill_btn_label(sk[2]), callback_data="cb:sk:2")],
        [
            InlineKeyboardButton(text="🎒 Предмет", callback_data="cb:item"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


def combat_flee_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение побега (не тратит ход до нажатия «Да»)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, сбежать", callback_data="cb:run:yes"),
                InlineKeyboardButton(text="⬅ Отмена", callback_data="cb:ret"),
            ],
        ],
    )


def _combat_item_button_label(data: dict) -> str:
    tag = consumables.normalize_combat_use_tag(data)
    try:
        v = int(data.get("use_value") or 0)
    except (TypeError, ValueError):
        v = 0
    if tag == "heal_hp_pct":
        return f"💚 {max(1, min(100, v))}%"
    if tag == "heal_mp_pct":
        return f"💙 {max(1, min(100, v))}%"
    if tag == "heal_hp_flat":
        return f"💚 +{max(1, v)}"
    if tag == "heal_mp_flat":
        return f"💙 +{max(1, v)}"
    if tag == "cure_poison":
        return "🧴 яд"
    return ""


def combat_item_picker_keyboard(bag_items: list[InventoryItem], *, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Список расходников для боя с пагинацией + отмена."""
    items = list(bag_items)
    total = len(items)
    per = max(5, min(15, int(per_page)))
    pages = max(1, (total + per - 1) // per)
    pg = max(0, min(int(page), pages - 1))
    start = pg * per
    chunk = items[start : start + per]

    rows: list[list[InlineKeyboardButton]] = []
    for it in chunk:
        data = it.item_data or {}
        gi = gear_icon_for_item_data(data)
        name = str(data.get("name", "?"))[:16]
        count = int(data.get("count", 1))
        count_str = f" ×{count}" if count > 1 else ""
        eff = _combat_item_button_label(data)
        eff_str = f" {eff}" if eff else ""
        rows.append(
            [InlineKeyboardButton(text=f"{gi}{eff_str} {name}{count_str}"[:64], callback_data=f"cb:itm:{it.id}")],
        )

    if pages > 1:
        prev_pg = (pg - 1) % pages
        next_pg = (pg + 1) % pages
        rows.append(
            [
                InlineKeyboardButton(text="⬅", callback_data=f"cb:itmp:{prev_pg}"),
                InlineKeyboardButton(text=f"{pg + 1}/{pages}", callback_data="cb:noop"),
                InlineKeyboardButton(text="➡", callback_data=f"cb:itmp:{next_pg}"),
            ],
        )

    rows.append([InlineKeyboardButton(text="⬅ В бой", callback_data="cb:ret")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
