"""Город (хаб) и кузница: inline-кнопки."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.city_kb import city_hub_keyboard
from bot.keyboards.menu_kb import menu_nav_button_row
from game.tower.progression import floor_data
from game.items.equipment import RARITY_NAME_RU, item_kind_label_ru
from game.locations import forge as forge_loc


def _dis_rarity_filter_label(code: str) -> str:
    if code == "all":
        return "Все"
    return RARITY_NAME_RU.get(code, code)

__all__ = [
    "city_hub_keyboard",
    "forge_actions_keyboard",
    "forge_set_shop_keyboard",
    "forge_dis_bag_keyboard",
    "forge_enchant_slots_keyboard",
    "forge_repair_keyboard",
    "forge_rune_bag_pick_keyboard",
    "forge_rune_menu_keyboard",
    "forge_rune_socket_pick_keyboard",
    "forge_star_merge_pick_keyboard",
]


def _forge_star_merge_row_visible(floor_number: int) -> bool:
    if not forge_loc.forge_available_on_floor(floor_number):
        return False
    c = floor_data.get_city_for_floor(int(floor_number))
    return c is not None and int(c.after_floor) >= 60


def forge_star_merge_pick_keyboard(floor_number: int, items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for iid, lab in items[:14]:
        short = lab if len(lab) <= 40 else lab[:37] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=short,
                    callback_data=f"frg:stx:{floor_number}:{iid}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    multi_mode: bool = False,
    selected_ids: set[int] | frozenset[int] | None = None,
    n_selected: int = 0,
) -> InlineKeyboardMarkup:
    """Список предметов для разбора (item_id, label) + фильтры и свип."""
    rows: list[list[InlineKeyboardButton]] = []
    rar_btns: list[InlineKeyboardButton] = []
    for code in ("all", "common", "uncommon", "rare", "epic"):
        lab = _dis_rarity_filter_label(code)
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
    for code, em in (
        ("all", ""),
        ("weapon", "🗡 "),
        ("armor", "🧥 "),
        ("shield", "🛡 "),
        ("ring", "💍 "),
        ("amulet", "📿 "),
    ):
        lab = "Все типы" if code == "all" else f"{em}{item_kind_label_ru(code)}"
        sel = "✅ " if (kind_filter or "all") == code else ""
        knd_btns.append(
            InlineKeyboardButton(
                text=f"{sel}{lab}",
                callback_data=f"frg:disf:{floor_number}:{rarity_filter or 'all'}:{code}",
            ),
        )
    rows.append(knd_btns[:3])
    rows.append(knd_btns[3:])
    sel = frozenset(selected_ids or ())
    for item_id, label in items[:12]:
        short = label if len(label) <= 34 else label[:31] + "…"
        if multi_mode:
            prefix = "✅ " if int(item_id) in sel else "☐ "
            cb = f"frg:dipk:{floor_number}:{item_id}"
        else:
            prefix = ""
            cb = f"frg:disx:{floor_number}:{item_id}"
        rows.append([InlineKeyboardButton(text=f"{prefix}{short}", callback_data=cb)])
    rows.append(
        [
            InlineKeyboardButton(
                text="✅ Мультивыбор" if multi_mode else "☐ Мультивыбор",
                callback_data=f"frg:dimul:{floor_number}",
            ),
        ],
    )
    if multi_mode and n_selected > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔥 Разобрать ({n_selected})",
                    callback_data=f"frg:dibat:{floor_number}",
                ),
            ],
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="🧹 Всё обычное",
                callback_data=f"frg:dsweep:{floor_number}:common",
            ),
            InlineKeyboardButton(
                text="🧹 До необыч. вкл.",
                callback_data=f"frg:dsweep:{floor_number}:uncommon",
            ),
        ],
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🧹 До редк. вкл.",
                callback_data=f"frg:dsweep:{floor_number}:rare",
            ),
        ],
    )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_repair_keyboard(
    floor_number: int,
    slot_rows: list[tuple[str, str]],
    *,
    return_to_floor: bool = False,
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
    if return_to_floor:
        rows_btn.append([InlineKeyboardButton(text="⬅ К этажу", callback_data="flnav:retfloor")])
    else:
        rows_btn.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows_btn.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows_btn)


def forge_actions_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="✨ Заточить предмет", callback_data=f"frg:ench:{floor_number}")],
        [
            InlineKeyboardButton(
                text="⚗️ Заточка + руна (без −1)",
                callback_data=f"frg:enchw:{floor_number}",
            ),
        ],
        [InlineKeyboardButton(text="🔨 Починка экипировки", callback_data=f"frg:rpr:{floor_number}")],
        [InlineKeyboardButton(text="♻️ Разбор экипировки", callback_data=f"frg:dis:{floor_number}")],
    ]
    if _forge_star_merge_row_visible(floor_number):
        rows.append(
            [InlineKeyboardButton(text="⭐ Слияние звёзд (5→+1)", callback_data=f"frg:stm:{floor_number}")],
        )
    rows.append([InlineKeyboardButton(text="🛒 Купить базовый сет", callback_data=f"frg:set:{floor_number}")])
    rows.append([InlineKeyboardButton(text="⬅ В город", callback_data=f"frg:city:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def forge_set_shop_keyboard(
    floor_number: int,
    items: list[tuple[str, str, int]],
) -> InlineKeyboardMarkup:
    """
    items: (key, label, price)
    """
    rows: list[list[InlineKeyboardButton]] = []
    for key, label, price in items[:12]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{label} — {int(price)}💰"[:64],
                    callback_data=f"frg:setbuy:{floor_number}:{key}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="⬅ Кузница", callback_data=f"frg:main:{floor_number}")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
