"""Клавиатуры некроманта: меню, ритуал, ковчег, души, покои."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.locations.hub_floors import LIBRARY_HUB_FLOOR
from game.necromancer.service import (
    MAX_SKELETONS_IN_BATTLE,
    NECROMANCER_COST_GOLD,
    SKELETON_ROLES,
    can_purchase_necromancer,
    get_party_skeleton_keys,
    is_necromancer,
    unlocked_skeleton_keys,
)
from game.necromancer.souls import (
    MAX_SKEL_UPGRADE_LEVEL,
    SOUL_SHOP,
    get_souls,
    skeleton_upgrade_cost,
    skeleton_upgrade_levels,
    soul_shop_item_cost,
    soul_shop_level,
)


def necromancer_menu_keyboard(character: Character) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if is_necromancer(character):
        rows.append(
            [InlineKeyboardButton(text="⚰️ Ковчег костей", callback_data="prf:necro:coffin")],
        )
        rows.append(
            [InlineKeyboardButton(text="🦴 Покои нежити", callback_data="prf:necro:quarters")],
        )
        rows.append(
            [InlineKeyboardButton(text="👻 Лавка душ", callback_data="prf:necro:shop")],
        )
        from game.locations import grimoire_library as lib

        if lib.library_unlocked(character):
            rows.append(
                [
                    InlineKeyboardButton(
                        text="📖 Высшие гримуары",
                        callback_data=f"lib:prestige:{LIBRARY_HUB_FLOOR}",
                    ),
                ],
            )
    else:
        can_ok, _ = can_purchase_necromancer(character)
        if can_ok or int(character.level) >= 60:
            rows.append(
                [InlineKeyboardButton(text="💀 Ритуал класса", callback_data="prf:necro:ritual")],
            )
    rows.append([InlineKeyboardButton(text="◀️ Специализация", callback_data="prf:spec")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_ritual_keyboard(*, can_buy: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_buy:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💀 Ритуал ({NECROMANCER_COST_GOLD // 1000}k 💰)",
                    callback_data="prf:necro:buy",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="◀️ Некромант", callback_data="prf:necro:menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_coffin_keyboard(character: Character) -> InlineKeyboardMarkup:
    party = set(get_party_skeleton_keys(character))
    unlocked = unlocked_skeleton_keys(character)
    rows: list[list[InlineKeyboardButton]] = []
    for key, rd in SKELETON_ROLES.items():
        if key not in unlocked:
            continue
        mark = "✅" if key in party else "⬜"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {rd.emoji} {rd.name_ru}",
                    callback_data=f"prf:necro:tog:{key}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="🦴 Покои", callback_data="prf:necro:quarters")])
    rows.append([InlineKeyboardButton(text="◀️ Некромант", callback_data="prf:necro:menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_quarters_keyboard(character: Character, *, back_home: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key in sorted(unlocked_skeleton_keys(character)):
        rd = SKELETON_ROLES[key]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{rd.emoji} {rd.name_ru[:24]}",
                    callback_data=f"prf:necro:skdet:{key}",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text="👻 Лавка душ", callback_data="prf:necro:shop")])
    if back_home:
        rows.append([InlineKeyboardButton(text="⬅ В дом", callback_data="hom:hub")])
    else:
        rows.append([InlineKeyboardButton(text="◀️ Некромант", callback_data="prf:necro:menu")])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_skeleton_detail_keyboard(
    character: Character,
    role_key: str,
    *,
    back_home: bool = False,
) -> InlineKeyboardMarkup:
    atk_lv, hp_lv = skeleton_upgrade_levels(character, role_key)
    rows: list[list[InlineKeyboardButton]] = []
    if atk_lv < MAX_SKEL_UPGRADE_LEVEL:
        cost = skeleton_upgrade_cost(atk_lv)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⚔️ Урон +1 ({cost} 👻)",
                    callback_data=f"prf:necro:skupg:{role_key}:atk",
                ),
            ],
        )
    if hp_lv < MAX_SKEL_UPGRADE_LEVEL:
        cost = skeleton_upgrade_cost(hp_lv)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🛡 HP +1 ({cost} 👻)",
                    callback_data=f"prf:necro:skupg:{role_key}:hp",
                ),
            ],
        )
    back_cb = "prf:necro:quarters" if not back_home else "hom:skel_q"
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=back_cb)])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_soul_shop_keyboard(character: Character) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in SOUL_SHOP.values():
        lv = soul_shop_level(character, item.key)
        if lv >= item.max_level:
            label = f"✅ {item.name_ru[:20]} MAX"
            cb = f"prf:necro:shop:nop"
        else:
            cost = soul_shop_item_cost(item, lv)
            label = f"{item.name_ru[:18]} — {cost}👻"
            cb = f"prf:necro:shopbuy:{item.key}"
        rows.append([InlineKeyboardButton(text=label[:64], callback_data=cb)])
    rows.append(
        [
            InlineKeyboardButton(text="🦴 Покои", callback_data="prf:necro:quarters"),
            InlineKeyboardButton(text="◀️ Меню", callback_data="prf:necro:menu"),
        ],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def necromancer_spec_extra_row(character: Character) -> list[InlineKeyboardButton] | None:
    if int(character.level) < 60:
        return None
    if is_necromancer(character):
        return [
            InlineKeyboardButton(
                text=f"💀 Некромант · {get_souls(character)}👻",
                callback_data="prf:necro:menu",
            ),
        ]
    return [
        InlineKeyboardButton(text="💀 Некромант", callback_data="prf:necro:menu"),
    ]
