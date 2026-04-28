"""Клавиатура боя (ТЗ 1.4)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models.character import Character
from db.models.inventory import InventoryItem
from game.characters.player_skills import (
    battle_skills_tuple,
    ensure_skill_meta,
    equipped_passive_key,
    learned_passives,
    passive_emoji,
    skill_emoji,
)
from game.items.equipment import gear_icon_for_item_data


def combat_main_keyboard(character: Character) -> InlineKeyboardMarkup:
    """Четыре действия + три экипированных навыка + строка пассивки."""
    ensure_skill_meta(character)
    sk = battle_skills_tuple(character)

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="⚔️ Атака", callback_data="cb:atk"),
            InlineKeyboardButton(text="🏃 Бежать", callback_data="cb:run"),
        ],
        [
            InlineKeyboardButton(
                text=f"{skill_emoji(sk[0].kind)} {sk[0].name[:15]}",
                callback_data="cb:sk:0",
            ),
            InlineKeyboardButton(
                text=f"{skill_emoji(sk[1].kind)} {sk[1].name[:15]}",
                callback_data="cb:sk:1",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{skill_emoji(sk[2].kind)} {sk[2].name[:15]}",
                callback_data="cb:sk:2",
            ),
        ],
        [
            InlineKeyboardButton(text="🎒 Предмет", callback_data="cb:item"),
        ],
    ]

    # Показываем экипированную пассивку как информационную строку
    pas_key = equipped_passive_key(character)
    if pas_key:
        pas_map = {p.key: p for p in learned_passives(character)}
        p = pas_map.get(pas_key)
        if p:
            em = passive_emoji(p.modifiers)
            rows.append([InlineKeyboardButton(
                text=f"{em} {p.name_ru[:20]} (пассивка)",
                callback_data="cb:noop",
            )])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def combat_item_picker_keyboard(bag_items: list[InventoryItem]) -> InlineKeyboardMarkup:
    """Список расходников для боя + отмена."""
    rows: list[list[InlineKeyboardButton]] = []
    for it in bag_items[:20]:
        data = it.item_data or {}
        gi = gear_icon_for_item_data(data)
        name = str(data.get("name", "?"))[:16]
        rows.append(
            [InlineKeyboardButton(text=f"{gi} {name}"[:64], callback_data=f"cb:itm:{it.id}")],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ В бой", callback_data="cb:ret")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
