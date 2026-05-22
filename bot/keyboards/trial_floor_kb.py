"""Клавиатура этажа с активным испытанием (угодья + босс)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.floor_kb import (
    _append_zone_masters_row,
    _append_tower_field_repair_row,
    _cb,
    _navigation_max_floor,
    _pet_rows,
    menu_nav_button_row,
    show_floor_secret_search_button,
)
from db.models.character import Character
from game.tower.progression import floor_data
from game.tower.progression.tower_ascent import tower_next_floor_pending
from game.tower.combat import boss_retry_cooldown as boss_retry_mod
from game.tower.trials.pack_config import get_trial_config
import game.tower.trials.floor_trial as floor_trial_mod


def trial_floor_screen_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots or frozenset()
    cfg = get_trial_config(floor_number)
    rows: list[list[InlineKeyboardButton]] = []
    rows.extend(_pet_rows(character, floor_number))

    _append_zone_masters_row(rows, character, floor_number)

    spawns = floor_trial_mod.build_trial_spawns(character)

    if floor_trial_mod.is_boss_chamber_trial(cfg):
        buffer: list[InlineKeyboardButton] = []
        for sp in spawns:
            if sp.slot_code.startswith(floor_trial_mod.SLOT_CHAMBER_PREFIX):
                label = sp.display_name
                if sp.slot_code in beaten:
                    label += " ✅"
                if len(label) > 18:
                    label = label[:15] + "…"
                buffer.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=_cb(floor_number, sp.slot_code),
                    ),
                )
        if buffer:
            rows.append(buffer)
        for sp in spawns:
            if sp.is_major_boss:
                label = sp.display_name
                if sp.slot_code in beaten:
                    cd_left = boss_retry_mod.retry_seconds_left(character, floor_number)
                    label += f" ⏳{cd_left // 60}м" if cd_left > 0 else " ✅"
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=label[:36],
                            callback_data=_cb(floor_number, sp.slot_code),
                        ),
                    ],
                )
    elif floor_trial_mod.is_defense_hub(cfg):
        for sp in spawns:
            if sp.slot_code == floor_trial_mod.SLOT_DEFENSE:
                label = sp.display_name
                if sp.slot_code in beaten:
                    label += " ✅"
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=label[:36],
                            callback_data=_cb(floor_number, sp.slot_code),
                        ),
                    ],
                )
                break
        buffer: list[InlineKeyboardButton] = []
        for sp in spawns:
            if sp.slot_code.startswith("ft_g"):
                label = sp.display_name
                if sp.slot_code in beaten:
                    label += " ✅"
                if len(label) > 18:
                    label = label[:15] + "…"
                buffer.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=_cb(floor_number, sp.slot_code),
                    ),
                )
        if buffer:
            rows.append(buffer)
        for sp in spawns:
            if sp.is_major_boss:
                label = sp.display_name
                if sp.slot_code in beaten:
                    label += " ✅"
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=label[:36],
                            callback_data=_cb(floor_number, sp.slot_code),
                        ),
                    ],
                )
    else:
        buffer: list[InlineKeyboardButton] = []

        def flush() -> None:
            nonlocal buffer
            if buffer:
                rows.append(buffer)
                buffer = []

        for sp in spawns:
            label = sp.display_name
            if sp.slot_code in beaten:
                suffix = " ✅"
                if len(label) > 33:
                    label = label[:30] + "…"
                label += suffix
            if len(label) > 36:
                label = label[:33] + "…"
            btn = InlineKeyboardButton(text=label, callback_data=_cb(floor_number, sp.slot_code))
            if sp.is_major_boss:
                flush()
                rows.append([btn])
            else:
                buffer.append(btn)
                if len(buffer) >= 2:
                    flush()
        flush()

    pend = tower_next_floor_pending(character)
    if pend is not None and floor_trial_mod.trial_ready_for_ascent(character, beaten):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⬆️ Этаж {pend}",
                    callback_data=_cb(floor_number, "ascend"),
                ),
            ],
        )

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    if nav:
        rows.append(nav)

    _append_tower_field_repair_row(rows, floor_number)
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
