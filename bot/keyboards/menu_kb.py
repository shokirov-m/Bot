"""

Клавиатуры главного меню и регистрации (выбор класса).

"""



from __future__ import annotations



from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



from bot.i18n import t
from bot.keyboards.tutorial_kb import tutorial_hints_keyboard
from game.characters.classes import all_classes_ordered
from game.floors.floor_data import PORTAL_DESTINATION_FLOORS





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

                InlineKeyboardButton(text=t(loc, "menu_portal"), callback_data="mnu:prt"),

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

            [

                InlineKeyboardButton(text="🏰 Клан", callback_data="mnu:clan"),

                InlineKeyboardButton(text=t(loc, "menu_home"), callback_data="hom:hub"),

            ],

        ],

    )


def portal_screen_keyboard(*, locale: str = "ru", highest_floor_reached: int) -> InlineKeyboardMarkup:
    """Портал: быстрый переход на важные этажи (список в floor_data.PORTAL_DESTINATION_FLOORS)."""
    loc = locale if locale in ("ru", "en") else "ru"
    row: list[InlineKeyboardButton] = []
    for fl in PORTAL_DESTINATION_FLOORS:
        locked = int(highest_floor_reached) < int(fl)
        key = "portal_btn_floor_locked" if locked else "portal_btn_floor"
        row.append(
            InlineKeyboardButton(
                text=t(loc, key, n=fl),
                callback_data=f"mnu:prt:{fl}",
            ),
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text=t(loc, "portal_back_menu"), callback_data="mnu:hub")],
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


