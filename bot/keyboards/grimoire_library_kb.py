"""Клавиатуры библиотеки гримуаров (хаб-этаж 9001)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.archetypes.grimoires import SKILL_GRIMOIRES
from game.locations import grimoire_library as lib
from game.locations.hub_floors import LIBRARY_HUB_FLOOR, is_library_hub_floor
from game.necromancer.service import is_necromancer


def _floor() -> int:
    return LIBRARY_HUB_FLOOR


def _library_back_callback(floor_number: int) -> str:
    if is_library_hub_floor(int(floor_number)):
        return "hub:back:tower"
    return f"fl:{int(floor_number)}:return"


def library_hub_keyboard(character: Character, floor_number: int | None = None) -> InlineKeyboardMarkup:
    """Главный зал: базовые пути + отдельная кнопка высших гримуаров."""
    fl = int(floor_number if floor_number is not None else _floor())
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for arch in lib.library_base_archetype_keys():
        lbl = lib.archetype_label_ru(arch)[:28]
        pair.append(
            InlineKeyboardButton(
                text=lbl,
                callback_data=f"lib:cls:{arch}:{fl}",
            ),
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    if lib.library_prestige_visible(character):
        rows.append(
            [
                InlineKeyboardButton(
                    text="💀 Высшие гримуары",
                    callback_data=f"lib:prestige:{fl}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="🗼 В башню", callback_data=_library_back_callback(fl))],
    )
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_prestige_hub_keyboard(character: Character, floor_number: int | None = None) -> InlineKeyboardMarkup:
    """Подменю престиж-классов (некромант и др.)."""
    fl = int(floor_number if floor_number is not None else _floor())
    rows: list[list[InlineKeyboardButton]] = []
    for arch in lib.library_prestige_archetype_keys(character):
        lbl = lib.archetype_label_ru(arch)[:32]
        if arch == "necromancer" and not is_necromancer(character):
            lbl = f"{lbl} (нужен класс)"[:36]
        rows.append(
            [InlineKeyboardButton(text=lbl, callback_data=f"lib:cls:{arch}:{fl}")],
        )
    rows.append(
        [InlineKeyboardButton(text="◀️ Главный зал", callback_data=f"lib:open:{fl}")],
    )
    rows.append(
        [InlineKeyboardButton(text="🗼 В башню", callback_data=_library_back_callback(fl))],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_class_keyboard(
    character: Character,
    archetype_key: str,
    floor_number: int | None = None,
) -> InlineKeyboardMarkup:
    fl = int(floor_number if floor_number is not None else _floor())
    rows: list[list[InlineKeyboardButton]] = []
    arch = str(archetype_key).lower()
    is_prestige = arch in lib.LIBRARY_PRESTIGE_ARCHETYPES
    for offer in lib.offers_for_archetype(arch):
        g = SKILL_GRIMOIRES.get(offer.grimoire_key)
        if not g:
            continue
        st = lib.offer_status(character, offer.grimoire_key)
        if st == "изучен":
            suffix = " ✅"
        elif st:
            suffix = " 📖"
        else:
            suffix = f" {offer.gold_price // 1000}k"
        name = g.name_ru.replace("📖 ", "")[:22]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{name}{suffix}",
                    callback_data=f"lib:view:{offer.grimoire_key}:{fl}",
                ),
            ],
        )
    if is_prestige:
        rows.append(
            [InlineKeyboardButton(text="◀️ Высшие гримуары", callback_data=f"lib:prestige:{fl}")],
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="◀️ Главный зал", callback_data=f"lib:open:{fl}")],
        )
    rows.append(
        [InlineKeyboardButton(text="🗼 В башню", callback_data=_library_back_callback(fl))],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_offer_keyboard(
    character: Character,
    grimoire_key: str,
    floor_number: int | None = None,
) -> InlineKeyboardMarkup:
    fl = int(floor_number if floor_number is not None else _floor())
    g = SKILL_GRIMOIRES.get(grimoire_key)
    arch = g.archetype_key if g else "warrior"
    is_prestige = arch in lib.LIBRARY_PRESTIGE_ARCHETYPES
    rows: list[list[InlineKeyboardButton]] = []
    ok, _ = lib.can_purchase(character, grimoire_key)
    if ok:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💰 Купить книгу",
                    callback_data=f"lib:buy:{grimoire_key}:{fl}",
                ),
            ],
        )
    back_cls = f"lib:prestige:{fl}" if is_prestige else f"lib:cls:{arch}:{fl}"
    rows.append([InlineKeyboardButton(text="◀️ Каталог", callback_data=back_cls)])
    back_main = f"lib:prestige:{fl}" if is_prestige else f"lib:open:{fl}"
    rows.append([InlineKeyboardButton(text="📚 Главный зал", callback_data=back_main)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
