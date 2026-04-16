"""

Клавиатуры главного меню и регистрации (выбор класса).

"""



from __future__ import annotations



from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



from bot.i18n import t
from bot.keyboards.tutorial_kb import tutorial_hints_keyboard
from game.characters.classes import all_classes_ordered





def class_selection_keyboard() -> InlineKeyboardMarkup:

    """Две кнопки в ряд — десять классов."""

    rows: list[list[InlineKeyboardButton]] = []

    row: list[InlineKeyboardButton] = []

    for cls in all_classes_ordered():

        row.append(

            InlineKeyboardButton(

                text=f"{cls.emoji} {cls.name_ru}",

                callback_data=f"reg:class:{cls.key}",

            ),

        )

        if len(row) == 2:

            rows.append(row)

            row = []

    if row:

        rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=rows)





def main_menu_keyboard(*, locale: str = "ru") -> InlineKeyboardMarkup:

    """Главное меню без слэш-команд."""

    loc = locale if locale in ("ru", "en") else "ru"

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(text=t(loc, "menu_profile"), callback_data="mnu:prf"),

                InlineKeyboardButton(text=t(loc, "menu_floor"), callback_data="mnu:flr"),

            ],

            [

                InlineKeyboardButton(text=t(loc, "menu_inv"), callback_data="mnu:inv"),

                InlineKeyboardButton(text=t(loc, "menu_titles"), callback_data="mnu:ttl"),

            ],

            [

                InlineKeyboardButton(text=t(loc, "menu_top"), callback_data="mnu:top"),

                InlineKeyboardButton(text=t(loc, "menu_daily"), callback_data="mnu:dly"),

            ],

            [

                InlineKeyboardButton(text=t(loc, "menu_quests"), callback_data="mnu:qst"),

                InlineKeyboardButton(text=t(loc, "menu_arena"), callback_data="mnu:arn"),

            ],

            [

                InlineKeyboardButton(text=t(loc, "menu_auction"), callback_data="mnu:auc"),

                InlineKeyboardButton(text=t(loc, "menu_settings"), callback_data="mnu:stg"),

        ],

    ],

)


def main_menu_with_tutorial_hints(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Главное меню и две короткие подсказки — одним сообщением после регистрации."""
    mm = main_menu_keyboard(locale=locale)
    tut = tutorial_hints_keyboard()
    return InlineKeyboardMarkup(inline_keyboard=[*mm.inline_keyboard, *tut.inline_keyboard])


def menu_nav_button_row() -> list[InlineKeyboardButton]:

    """Одна кнопка возврата к главному меню (добавлять внизу других клавиатур)."""

    return [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")]


