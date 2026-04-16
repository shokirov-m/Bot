"""
Inline-клавиатура действий на этаже: класс (17/57), монстры, вход в город, навигация по этажам.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters.class_arcs import (
    SUBCLASS_NAME_RU,
    needs_base_class_choice,
    needs_subclass_choice,
    offered_base_class_keys,
    subclass_keys_for_character,
)
from game.characters.classes import get_class_or_none
from game.characters import pets as pets_mod
from game.floors import floor_data
from game.floors import forest_beginnings as forest_beginnings_mod
from game.floors import long_floor as long_floor_mod
from game.floors.monsters import FloorMonsterSpawn
from game.floors.tower_ascent import tower_next_floor_pending
from services.tutorial_battle_service import tutorial_battle_pending


def _cb(floor_number: int, code: str) -> str:
    """Короткий callback: fl:<этаж>:<код слота>."""
    return f"fl:{floor_number}:{code}"


def _pet_rows(character: Character, floor_number: int) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    if floor_number in pets_mod.pet_gacha_floors_for_pet_switch():
        if len(pets_mod.owned_keys(character)) > 1:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🔄 Сменить питомца",
                        callback_data=_cb(floor_number, "petw"),
                    ),
                ],
            )
    return rows


def _class_arc_rows(character: Character) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    if needs_base_class_choice(character):
        row_buf: list[InlineKeyboardButton] = []
        for key in offered_base_class_keys(character):
            cls = get_class_or_none(key)
            if cls is None:
                continue
            label = f"{cls.emoji} {cls.name_ru}"
            if len(label) > 36:
                label = label[:33] + "…"
            row_buf.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"arc:b:{key}",
                ),
            )
            if len(row_buf) >= 2:
                rows.append(row_buf)
                row_buf = []
        if row_buf:
            rows.append(row_buf)
    if needs_subclass_choice(character):
        for sk in subclass_keys_for_character(character):
            name = SUBCLASS_NAME_RU.get(sk, sk)
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"⭐ {name} (×2 статов)",
                        callback_data=f"arc:s:{sk}",
                    ),
                ],
            )
    return rows


def floor_screen_keyboard(
    character: Character,
    spawns: list[FloorMonsterSpawn],
    *,
    defeated_slots: frozenset[str] | set[str] | None = None,
) -> InlineKeyboardMarkup:
    """Кнопки этажа: ветка класса, цели, город, навигация 1..max."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))

    if tutorial_battle_pending(character) and floor_number == 1:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎓 Учебный бой наставника",
                    callback_data=_cb(floor_number, "tutorial"),
                ),
            ],
        )

    if floor_number == 3 and not long_floor_mod.is_long_floor_active(character):
        rows.append(
            [
                InlineKeyboardButton(
                    text="💰 Скупщик",
                    callback_data=_cb(floor_number, "scrap"),
                ),
            ],
        )

    rows.extend(_pet_rows(character, floor_number))

    if forest_beginnings_mod.is_forest_beginnings_zone(floor_number) and not long_floor_mod.is_long_floor_active(
        character,
    ):
        camp_lbl = "🏕️ Привал (полн. HP, без ⚡)"
        if forest_beginnings_mod.camp_used(character):
            camp_lbl = "🏕️ Привал (использован)"
        rows.append(
            [
                InlineKeyboardButton(
                    text=camp_lbl,
                    callback_data=f"flf:camp:{floor_number}",
                ),
            ],
        )

    buffer: list[InlineKeyboardButton] = []

    def flush() -> None:
        nonlocal buffer
        if buffer:
            rows.append(buffer)
            buffer = []

    for sp in spawns:
        base = sp.display_name
        if sp.slot_code in beaten:
            suffix = " ✅"
            avail = 36 - len(suffix)
            if len(base) > avail:
                base = base[: avail - 1] + "…"
            label = base + suffix
        else:
            label = base
            if len(label) > 36:
                label = label[:33] + "…"
        btn = InlineKeyboardButton(
            text=label,
            callback_data=_cb(floor_number, sp.slot_code),
        )
        if sp.is_major_boss or sp.is_mini_boss or sp.is_elite:
            flush()
            rows.append([btn])
        else:
            buffer.append(btn)
            if len(buffer) >= 2:
                flush()

    flush()

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⬆️ Этаж {pend}",
                    callback_data=_cb(floor_number, "ascend"),
                ),
            ],
        )

    if floor_data.get_city_for_floor(floor_number):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🏙️ Город",
                    callback_data=_cb(floor_number, "city"),
                ),
            ],
        )

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    if nav:
        rows.append(nav)

    if floor_data.has_quest_npc(floor_number):
        rows.append(
            [
                InlineKeyboardButton(
                    text="📜 Странник",
                    callback_data=f"qst:{floor_number}:view",
                ),
            ],
        )

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def long_floor_screen_keyboard(character: Character) -> InlineKeyboardMarkup:
    """Клавиатура пилотного длинного этажа (этаж 15): фазы сценария + навигация как на обычном этаже."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    ph = long_floor_mod.current_phase(character)
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))

    if tutorial_battle_pending(character) and floor_number == 1:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎓 Учебный бой наставника",
                    callback_data=_cb(floor_number, "tutorial"),
                ),
            ],
        )

    rows.extend(_pet_rows(character, floor_number))

    if forest_beginnings_mod.is_forest_beginnings_zone(floor_number) and not long_floor_mod.is_long_floor_active(
        character,
    ):
        camp_lbl = "🏕️ Привал (полн. HP, без ⚡)"
        if forest_beginnings_mod.camp_used(character):
            camp_lbl = "🏕️ Привал (использован)"
        rows.append(
            [
                InlineKeyboardButton(
                    text=camp_lbl,
                    callback_data=f"flf:camp:{floor_number}",
                ),
            ],
        )

    if ph == "keys":
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔑 Обыскать зал ключей",
                    callback_data=_cb(floor_number, "lf_keys"),
                ),
            ],
        )
    elif ph == "wave1":
        rows.append(
            [
                InlineKeyboardButton(
                    text="⚔️ Волна 1",
                    callback_data=_cb(floor_number, "lf_w1"),
                ),
            ],
        )
    elif ph == "wave2":
        rows.append(
            [
                InlineKeyboardButton(
                    text="⚔️ Волна 2",
                    callback_data=_cb(floor_number, "lf_w2"),
                ),
            ],
        )
    elif ph == "npc":
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 Странник у печати",
                    callback_data=_cb(floor_number, "lf_npc"),
                ),
            ],
        )
    elif ph == "boss":
        rows.append(
            [
                InlineKeyboardButton(
                    text="👑 Владыка топи",
                    callback_data=_cb(floor_number, "lf_boss"),
                ),
            ],
        )

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⬆️ Этаж {pend}",
                    callback_data=_cb(floor_number, "ascend"),
                ),
            ],
        )

    if floor_data.get_city_for_floor(floor_number):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🏙️ Город",
                    callback_data=_cb(floor_number, "city"),
                ),
            ],
        )

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    if nav:
        rows.append(nav)

    if floor_data.has_quest_npc(floor_number):
        rows.append(
            [
                InlineKeyboardButton(
                    text="📜 Странник",
                    callback_data=f"qst:{floor_number}:view",
                ),
            ],
        )

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def secret_result_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    """После текста обыска — вернуться к списку целей."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗺️ К этажу",
                    callback_data=_cb(floor_number, "return"),
                ),
            ],
            menu_nav_button_row(),
        ],
    )
