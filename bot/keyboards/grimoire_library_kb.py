"""Клавиатуры библиотеки гримуаров (18↔19)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models.character import Character
from game.archetypes.grimoires import SKILL_GRIMOIRES
from game.locations import grimoire_library as lib
from game.locations.hub_floors import is_library_hub_floor


def _library_back_callback(floor_number: int) -> str:
    if is_library_hub_floor(int(floor_number)):
        return "hub:back:tower"
    return f"fl:{int(floor_number)}:return"


def library_hub_keyboard(character: Character, floor_number: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pair = []
    for arch in lib.library_archetype_keys_for(character):
        lbl = lib.archetype_label_ru(arch)[:28]
        pair.append(
            InlineKeyboardButton(
                text=lbl,
                callback_data=f"lib:cls:{arch}:{floor_number}",
            ),
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append(
        [InlineKeyboardButton(text="🗺️ В башню", callback_data=_library_back_callback(floor_number))],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_class_keyboard(
    character: Character,
    archetype_key: str,
    floor_number: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for offer in lib.offers_for_archetype(archetype_key):
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
                    callback_data=f"lib:view:{offer.grimoire_key}:{floor_number}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="◀️ Классы", callback_data=f"lib:open:{floor_number}")],
    )
    rows.append(
        [InlineKeyboardButton(text="🗺️ В башню", callback_data=_library_back_callback(floor_number))],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def library_offer_keyboard(
    character: Character,
    grimoire_key: str,
    floor_number: int,
) -> InlineKeyboardMarkup:
    g = SKILL_GRIMOIRES.get(grimoire_key)
    arch = g.archetype_key if g else "warrior"
    rows: list[list[InlineKeyboardButton]] = []
    ok, _ = lib.can_purchase(character, grimoire_key)
    if ok:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💰 Купить книгу",
                    callback_data=f"lib:buy:{grimoire_key}:{floor_number}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text="◀️ Каталог", callback_data=f"lib:cls:{arch}:{floor_number}")],
    )
    rows.append(
        [InlineKeyboardButton(text="📚 Классы", callback_data=f"lib:open:{floor_number}")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
