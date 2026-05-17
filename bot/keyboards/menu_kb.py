"""

Клавиатуры главного меню и регистрации (выбор класса).

"""



from __future__ import annotations



from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



from bot.i18n import t
from bot.keyboards.tutorial_kb import tutorial_hints_keyboard
from db.models.character import Character
from game.characters.classes import all_classes_ordered
from game.tower.progression.floor_data import PORTAL_DESTINATION_FLOORS
import services.progression.unlock_service as unlock_service





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





def main_menu_keyboard(*, locale: str = "ru", character: Character | None = None) -> InlineKeyboardMarkup:

    """Главное меню без слэш-команд."""

    loc = "ru"

    allow = (
        unlock_service.available_main_menu_keys(character)
        if character is not None
        else {
            "menu_profile",
            "menu_floor",
            "menu_inv",
            "menu_portal",
            "menu_quests",
            "menu_locations",
            "menu_home",
            "menu_top",
            "menu_settings",
        }
    )

    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [
            InlineKeyboardButton(text=t(loc, "menu_profile"), callback_data="mnu:prf"),
            InlineKeyboardButton(text=t(loc, "menu_floor"), callback_data="mnu:flr"),
        ],
    )
    inv_row: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text=t(loc, "menu_inv"), callback_data="mnu:inv"),
    ]
    if "menu_portal" in allow:
        inv_row.append(InlineKeyboardButton(text=t(loc, "menu_portal"), callback_data="mnu:prt"))
    rows.append(inv_row)
    if "menu_quests" in allow:
        rows.append([InlineKeyboardButton(text=t(loc, "menu_quests"), callback_data="mnu:qst")])
    if "menu_locations" in allow:
        rows.append([InlineKeyboardButton(text=t(loc, "menu_locations"), callback_data="mnu:loc")])
    if "menu_home" in allow:
        rows.append([InlineKeyboardButton(text=t(loc, "menu_home"), callback_data="hom:hub")])
    last_row: list[InlineKeyboardButton] = []
    if "menu_top" in allow:
        last_row.append(InlineKeyboardButton(text=t(loc, "menu_top"), callback_data="mnu:top"))
    if "menu_settings" in allow:
        last_row.append(InlineKeyboardButton(text=t(loc, "menu_settings"), callback_data="mnu:stg"))
    if last_row:
        rows.append(last_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def locations_hub_keyboard(*, locale: str = "ru", character: Character | None = None) -> InlineKeyboardMarkup:
    """Арена, Колизей, Мастерская, Магазин, Клан."""
    loc = "ru"
    if character is not None and not unlock_service.is_unlocked(character, "menu_locations"):
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t(loc, "portal_back_menu"), callback_data="mnu:hub")]],
        )
    allow = unlock_service.available_locations_menu_keys(character) if character is not None else None
    allow = allow or {"menu_arena", "menu_coliseum", "menu_workshop", "menu_auction", "menu_clan"}
    rows: list[list[InlineKeyboardButton]] = []
    row1: list[InlineKeyboardButton] = []
    if "menu_arena" in allow:
        row1.append(InlineKeyboardButton(text=t(loc, "menu_arena"), callback_data="mnu:arn"))
    if "menu_coliseum" in allow:
        row1.append(InlineKeyboardButton(text=t(loc, "menu_coliseum"), callback_data="mnu:col"))
    if row1:
        rows.append(row1)
    row2: list[InlineKeyboardButton] = []
    if "menu_workshop" in allow:
        row2.append(InlineKeyboardButton(text=t(loc, "menu_workshop"), callback_data="mnu:wsp"))
    if "menu_auction" in allow:
        row2.append(InlineKeyboardButton(text=t(loc, "menu_auction"), callback_data="mnu:auc"))
    if row2:
        rows.append(row2)
    if "menu_clan" in allow:
        rows.append([InlineKeyboardButton(text="🏰 Клан", callback_data="mnu:clan")])
    if "menu_sticker" in allow:
        rows.append([InlineKeyboardButton(text=t(loc, "menu_sticker_btn"), callback_data="mnu:stk")])
    rows.append([InlineKeyboardButton(text=t(loc, "portal_back_menu"), callback_data="mnu:hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    loc = "ru"
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


def main_menu_with_tutorial_hints(*, locale: str = "ru", character: Character | None = None) -> InlineKeyboardMarkup:
    """Главное меню и две короткие подсказки — одним сообщением после регистрации."""
    mm = main_menu_keyboard(locale=locale, character=character)
    tut = tutorial_hints_keyboard()
    return InlineKeyboardMarkup(inline_keyboard=[*mm.inline_keyboard, *tut.inline_keyboard])


def menu_nav_button_row() -> list[InlineKeyboardButton]:

    """Одна кнопка возврата к главному меню (добавлять внизу других клавиатур)."""

    return [InlineKeyboardButton(text="📋 Меню", callback_data="mnu:hub")]


