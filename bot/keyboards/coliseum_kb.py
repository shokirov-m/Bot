"""Клавиатуры PvE Колизея (колбэк col:)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models.character import Character
from game.coliseum.coliseum_data import COLISEUM_FIGHTERS
from services import coliseum_service


def _batch_range(*, next_id: int | None) -> tuple[int, int]:
    """Показываем ровно 5 бойцов: группа по индексу следующего боя (или последняя пятёрка)."""
    if next_id is None:
        return 46, 50
    b = ((int(next_id) - 1) // 5) * 5 + 1
    return b, min(b + 4, 50)


def coliseum_main_keyboard(
    *,
    character: Character,
    next_id: int | None,
    can_fight: bool,
) -> InlineKeyboardMarkup:
    """Правила, 5 бойцов текущей «пятёрки», быстрый бой с доступным."""
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [InlineKeyboardButton(text="📜 Правила", callback_data="col:rules")],
    )
    defeated_set = set(coliseum_service.defeated_ids(character))
    start, end = _batch_range(next_id=next_id)
    for i in range(start, end + 1):
        f = COLISEUM_FIGHTERS[i - 1]
        short = f.name[:22] if len(f.name) <= 22 else f.name[:19] + "…"
        if i in defeated_set:
            prefix = "✅ "
        else:
            ok, _ = coliseum_service.can_start_fight(character, i)
            prefix = "" if ok else "🔒 "
        label = f"{prefix}{i:02d}. {short}"[:64]
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"col:info:{i}")],
        )
    if can_fight and next_id is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⚔️ Бой: #{next_id}",
                    callback_data=f"col:fight:{next_id}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅️ Локации", callback_data="mnu:loc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def coliseum_fight_confirm_keyboard(fighter_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ В бой", callback_data=f"col:go:{fighter_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="col:menu"),
            ],
        ],
    )
