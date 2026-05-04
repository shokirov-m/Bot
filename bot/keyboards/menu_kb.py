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

                InlineKeyboardButton(text=t(loc, "menu_coliseum"), callback_data="mnu:col"),

            ],

            [

                InlineKeyboardButton(text=t(loc, "menu_auction"), callback_data="mnu:auc"),

                InlineKeyboardButton(text=t(loc, "menu_settings"), callback_data="mnu:stg"),

            ],

            [

                InlineKeyboardButton(text="🏰 Клан", callback_data="mnu:clan"),

                InlineKeyboardButton(text=t(loc, "menu_home"), callback_data="hom:hub"),

            ],

            [

                InlineKeyboardButton(text=t(loc, "menu_workshop"), callback_data="mnu:wsp"),

            ],

        ],

    )


PORTAL_PAGE_SIZE = 8


def portal_screen_keyboard(
    *,
    locale: str = "ru",
    highest_floor_reached: int,
    page: int = 0,
    portal_admin_unlock: bool = False,
) -> InlineKeyboardMarkup:
    """Портал: быстрый переход на важные этажи (список в floor_data.PORTAL_DESTINATION_FLOORS).

    Доступные этажи (≤ highest_floor_reached) показываются по `PORTAL_PAGE_SIZE` за страницу.
    Заблокированные не показываем — их слишком много при увеличенном пуле.
    Админ: все точки портала видны и доступны для перехода из обработчика (блокировку снимает travel).
    """
    loc = locale if locale in ("ru", "en") else "ru"
    if portal_admin_unlock:
        available = list(PORTAL_DESTINATION_FLOORS)
    else:
        available = [fl for fl in PORTAL_DESTINATION_FLOORS if int(highest_floor_reached) >= int(fl)]
    total = len(available)
    if total == 0:
        rows: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text=t(loc, "portal_back_menu"), callback_data="mnu:hub")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=rows)
    pages = max(1, (total + PORTAL_PAGE_SIZE - 1) // PORTAL_PAGE_SIZE)
    p = max(0, min(int(page), pages - 1))
    start = p * PORTAL_PAGE_SIZE
    chunk = available[start:start + PORTAL_PAGE_SIZE]
    rows = []
    row: list[InlineKeyboardButton] = []
    for fl in chunk:
        row.append(
            InlineKeyboardButton(
                text=t(loc, "portal_btn_floor", n=fl),
                callback_data=f"mnu:prt:{fl}",
            ),
        )
        if len(row) >= 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if pages > 1:
        nav_row: list[InlineKeyboardButton] = []
        if p > 0:
            nav_row.append(
                InlineKeyboardButton(text="◀️", callback_data=f"mnu:prtpg:{p - 1}"),
            )
        nav_row.append(
            InlineKeyboardButton(text=f"{p + 1}/{pages}", callback_data="mnu:prtpg:nop"),
        )
        if p < pages - 1:
            nav_row.append(
                InlineKeyboardButton(text="▶️", callback_data=f"mnu:prtpg:{p + 1}"),
            )
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text=t(loc, "portal_back_menu"), callback_data="mnu:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_with_tutorial_hints(*, locale: str = "ru") -> InlineKeyboardMarkup:
    """Главное меню и две короткие подсказки — одним сообщением после регистрации."""
    mm = main_menu_keyboard(locale=locale)
    tut = tutorial_hints_keyboard()
    return InlineKeyboardMarkup(inline_keyboard=[*mm.inline_keyboard, *tut.inline_keyboard])


def menu_nav_button_row() -> list[InlineKeyboardButton]:

    """Одна кнопка возврата к главному меню (добавлять внизу других клавиатур)."""

    return [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")]


