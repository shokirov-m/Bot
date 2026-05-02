"""Город (хаб) и кузница: inline-кнопки."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.city_kb import city_hub_keyboard
from bot.keyboards.menu_kb import menu_nav_button_row

__all__ = [
    "city_hub_keyboard",
    "forge_actions_keyboard",
    "forge_dis_bag_keyboard",
    "forge_enchant_slots_keyboard",
    "forge_repair_keyboard",
    "forge_rune_bag_pick_keyboard",
    "forge_rune_menu_keyboard",
    "forge_rune_socket_pick_keyboard",
]


def forge_rune_menu_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Вставить руну", callback_data=f"frg:rsl:{floor_number}")],
            [InlineKeyboardButton(text="🔓 Извлечь руну", callback_data=f"frg:rrm:{floor_number}")],
            [
                InlineKeyboardButton(
                    text="⚗️ Две I → II (авто)",
                    callback_data=f"frg:rca:{floor_number}",
                ),
            ],
            [InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")],
            menu_nav_button_row(),
        ],
    )


def forge_rune_bag_pick_keyboard(
    floor_number: int,
    items: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item_id, label in items[:14]:
        short = label if len(label) <= 36 else label[:33] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=short,
                    callback_data=f"frg:rsi:{floor_number}:{item_id}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"frg:rnm:{floor_number}")],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_rune_socket_pick_keyboard(
    floor_number: int,
    labels: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, label in labels[:8]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:40],
                    callback_data=f"frg:rrx:{floor_number}:{idx}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"frg:rnm:{floor_number}")],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_enchant_slots_keyboard(
    floor_number: int,
    slots: list[tuple[str, str]],
    *,
    ward: bool = False,
) -> InlineKeyboardMarkup:
    prefix = "enchw" if ward else "ench"
    rows: list[list[InlineKeyboardButton]] = []
    for slot_code, label in slots[:12]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:64],
                    callback_data=f"frg:{prefix}:{floor_number}:{slot_code}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_craft_recipes_keyboard(
    floor_number: int,
    recipe_ids: list[tuple[str, str]],
) -> InlineKeyboardMarkup:
    """(recipe_id, short_label)"""
    rows: list[list[InlineKeyboardButton]] = []
    for rid, lab in recipe_ids[:10]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=lab[:58],
                    callback_data=f"frg:crf:{floor_number}:{rid}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_dis_bag_keyboard(
    floor_number: int,
    items: list[tuple[int, str]],
    *,
    rarity_filter: str | None = None,
    kind_filter: str | None = None,
) -> InlineKeyboardMarkup:
    """Список предметов для разбора (item_id, label) + фильтры и свип."""
    rows: list[list[InlineKeyboardButton]] = []
    rar_btns: list[InlineKeyboardButton] = []
    for code, lab in (
        ("all", "Все"),
        ("common", "common"),
        ("uncommon", "uncommon"),
        ("rare", "rare"),
        ("epic", "epic"),
    ):
        sel = "✅ " if (rarity_filter or "all") == code else ""
        rar_btns.append(
            InlineKeyboardButton(
                text=f"{sel}{lab}",
                callback_data=f"frg:disf:{floor_number}:{code}:{kind_filter or 'all'}",
            ),
        )
    rows.append(rar_btns[:3])
    rows.append(rar_btns[3:])
    knd_btns: list[InlineKeyboardButton] = []
    for code, lab in (
        ("all", "Все типы"),
        ("weapon", "🗡 weapon"),
        ("armor", "🧥 armor"),
        ("shield", "🛡 shield"),
        ("ring", "💍 ring"),
        ("amulet", "📿 amulet"),
    ):
        sel = "✅ " if (kind_filter or "all") == code else ""
        knd_btns.append(
            InlineKeyboardButton(
                text=f"{sel}{lab}",
                callback_data=f"frg:disf:{floor_number}:{rarity_filter or 'all'}:{code}",
            ),
        )
    rows.append(knd_btns[:3])
    rows.append(knd_btns[3:])
    for item_id, label in items[:12]:
        short = label if len(label) <= 38 else label[:35] + "…"
        rows.append(
            [InlineKeyboardButton(text=short, callback_data=f"frg:disx:{floor_number}:{item_id}")]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="🧹 Свип common",
                callback_data=f"frg:dsweep:{floor_number}:common",
            ),
            InlineKeyboardButton(
                text="🧹 Свип ≤uncommon",
                callback_data=f"frg:dsweep:{floor_number}:uncommon",
            ),
        ],
    )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_repair_keyboard(
    floor_number: int,
    slot_rows: list[tuple[str, str]],
) -> InlineKeyboardMarkup:
    rows_btn: list[list[InlineKeyboardButton]] = []
    if slot_rows:
        rows_btn.append(
            [
                InlineKeyboardButton(
                    text="🔧 Починить всё",
                    callback_data=f"frg:rpra:{floor_number}",
                ),
            ],
        )
    for slot, lab in slot_rows[:12]:
        rows_btn.append(
            [
                InlineKeyboardButton(
                    text=lab[:64],
                    callback_data=f"frg:rpr1:{floor_number}:{slot}",
                ),
            ],
        )
    rows_btn.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows_btn.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows_btn)


def forge_actions_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Заточить предмет", callback_data=f"frg:ench:{floor_number}")],
            [
                InlineKeyboardButton(
                    text="⚗️ Заточка + руна (без −1)",
                    callback_data=f"frg:enchw:{floor_number}",
                ),
            ],
            [InlineKeyboardButton(text="🔨 Починка экипировки", callback_data=f"frg:rpr:{floor_number}")],
            [InlineKeyboardButton(text="🔨 Разобрать предмет", callback_data=f"frg:dis:{floor_number}")],
            [InlineKeyboardButton(text="💎 Руны на оружии", callback_data=f"frg:rnm:{floor_number}")],
            [InlineKeyboardButton(text="🧪 Сварить настой (HP)", callback_data=f"frg:brew:{floor_number}")],
            [InlineKeyboardButton(text="⚒️ Крафт (рецепты)", callback_data=f"frg:craft:{floor_number}")],
            [InlineKeyboardButton(text="📜 Задание кузнеца", callback_data=f"frg:qst:{floor_number}")],
            [InlineKeyboardButton(text="⬅ В город", callback_data=f"frg:city:{floor_number}")],
            menu_nav_button_row(),
        ],
    )


def forge_quest_keyboard(floor_number: int, state: dict) -> InlineKeyboardMarkup:
    """Клавиатура экрана цепочки заданий кузнеца."""
    rows: list[list[InlineKeyboardButton]] = []

    if not state:
        rows.append([InlineKeyboardButton(
            text="⚒️ Начать цепочку заданий",
            callback_data=f"frg:qst:start:{floor_number}",
        )])
    else:
        final_claimed = state.get("final_claimed", False)
        if not final_claimed:
            for s in (1, 2, 3):
                if state.get(f"{s}_done") and not state.get(f"{s}_claimed"):
                    rows.append([InlineKeyboardButton(
                        text=f"✅ Сдать шаг {s}",
                        callback_data=f"frg:qst:claim:{floor_number}:{s}",
                    )])
                    break
            if all(state.get(f"{s}_claimed") for s in (1, 2, 3)) and not final_claimed:
                rows.append([InlineKeyboardButton(
                    text="🏆 Получить финальную награду",
                    callback_data=f"frg:qst:final:{floor_number}",
                )])

    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
