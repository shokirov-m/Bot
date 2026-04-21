"""
Inline-клавиатура действий на этаже: класс (11 яр. / 57), монстры, вход в город, навигация по этажам.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters import pets as pets_mod
from game.floors import floor_data
from game.floors import forest_beginnings as forest_beginnings_mod
from game.floors import long_floor as long_floor_mod
from game.floors import room_clear_floor as rc_mod
from game.floors import rotten_swamps as rotten_swamps_mod
from game.floors import wave_floor as wv_mod
from game.floors import wandering_npcs as wandering_npcs_mod
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
    """Классовая ветка наставника снята — профессии в статусе / меню."""
    return []


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

    rows.extend(_pet_rows(character, floor_number))

    if (
        forest_beginnings_mod.is_forest_beginnings_zone(floor_number)
        and floor_number != 3
        and not long_floor_mod.is_long_floor_active(character)
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

    if rotten_swamps_mod.is_rotten_swamps_zone(floor_number) and not long_floor_mod.is_long_floor_active(
        character,
    ):
        sc_lbl = "🏚️ Заброшенный лагерь"
        if rotten_swamps_mod.abandoned_camp_used(character):
            sc_lbl = "🏚️ Лагерь (обыскан)"
        rows.append(
            [
                InlineKeyboardButton(
                    text=sc_lbl,
                    callback_data=f"flf:swcamp:{floor_number}",
                ),
            ],
        )

    wnpc = None if floor_number == 3 else wandering_npcs_mod.wandering_npc_for_floor(
        int(character.id),
        floor_number,
    )
    if wnpc is not None:
        btxt = str(wnpc["button"])
        if len(btxt) > 18:
            btxt = btxt[:15] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🎭 {btxt}",
                    callback_data=_cb(floor_number, "wnpc"),
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
        if (
            rotten_swamps_mod.is_rotten_swamps_zone(floor_number)
            and not long_floor_mod.is_long_floor_active(character)
            and rotten_swamps_mod.dense_fog_hides_spawn_on_map(sp)
            and sp.slot_code not in beaten
        ):
            base = rotten_swamps_mod.mystery_spawn_label()
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
    if floor_number != 3:
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    if nav:
        rows.append(nav)

    if floor_data.has_quest_npc(floor_number) and floor_number != 3:
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

    if (
        forest_beginnings_mod.is_forest_beginnings_zone(floor_number)
        and floor_number != 3
        and not long_floor_mod.is_long_floor_active(character)
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

    if rotten_swamps_mod.is_rotten_swamps_zone(floor_number) and not long_floor_mod.is_long_floor_active(
        character,
    ):
        sc_lbl = "🏚️ Заброшенный лагерь"
        if rotten_swamps_mod.abandoned_camp_used(character):
            sc_lbl = "🏚️ Лагерь (обыскан)"
        rows.append(
            [
                InlineKeyboardButton(
                    text=sc_lbl,
                    callback_data=f"flf:swcamp:{floor_number}",
                ),
            ],
        )

    wnpc = None if floor_number == 3 else wandering_npcs_mod.wandering_npc_for_floor(
        int(character.id),
        floor_number,
    )
    if wnpc is not None:
        btxt = str(wnpc["button"])
        if len(btxt) > 18:
            btxt = btxt[:15] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🎭 {btxt}",
                    callback_data=_cb(floor_number, "wnpc"),
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
    if floor_number != 3:
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    if nav:
        rows.append(nav)

    if floor_data.has_quest_npc(floor_number) and floor_number != 3:
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


def room_clear_floor_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 5 — зачистка комнат."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    # Кнопки комнат
    room_labels = ["Первая комната", "Вторая комната", "Третья комната", "Четвёртая комната", "Пятая комната"]
    buf: list[InlineKeyboardButton] = []
    for i, slot in enumerate(rc_mod.SLOT_ROOMS):
        label = f"🌿 {room_labels[i]}"
        if slot in beaten:
            label = f"✅ {room_labels[i]}"
        buf.append(InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, slot)))
        if len(buf) >= 2:
            rows.append(buf)
            buf = []
    if buf:
        rows.append(buf)

    # Кнопка босса — только если все комнаты зачищены
    if rc_mod.is_boss_unlocked(beaten):
        boss_label = "✅ 🌳 Страж Прохода" if rc_mod.SLOT_BOSS in beaten else "🌳 Страж Прохода"
        rows.append([InlineKeyboardButton(text=boss_label, callback_data=_cb(floor_number, rc_mod.SLOT_BOSS))])

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append([InlineKeyboardButton(text=f"⬆️ Этаж {pend}", callback_data=_cb(floor_number, "ascend"))])

    if floor_data.get_city_for_floor(floor_number):
        rows.append([InlineKeyboardButton(text="🏙️ Город", callback_data=_cb(floor_number, "city"))])

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wave_floor_screen_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 10 — волны вторжения (последовательно)."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    # Шкала пройденных волн
    wave_labels = {
        wv_mod.SLOT_WAVE_1: ("⚔️ Волна 1 — Авангард", "✅ Волна 1 — Авангард"),
        wv_mod.SLOT_WAVE_2: ("🗡️ Волна 2 — Берсерки", "✅ Волна 2 — Берсерки"),
        wv_mod.SLOT_WAVE_3: ("💀 Волна 3 — Чернокнижник", "✅ Волна 3 — Чернокнижник"),
    }
    current_slot = wv_mod.current_available_slot(beaten)

    for slot, (label_active, label_done) in wave_labels.items():
        if slot in beaten:
            rows.append([InlineKeyboardButton(text=label_done, callback_data=_cb(floor_number, slot))])
        elif slot == current_slot:
            rows.append([InlineKeyboardButton(text=label_active, callback_data=_cb(floor_number, slot))])
        else:
            # заблокирована (предыдущая волна не пройдена)
            rows.append([InlineKeyboardButton(text=f"🔒 {label_active[2:] if len(label_active) > 2 else label_active}", callback_data=f"wv:locked")])

    # Босс — только после всех волн
    if wv_mod.SLOT_WAVE_3 in beaten:
        if wv_mod.SLOT_BOSS in beaten:
            rows.append([InlineKeyboardButton(text="✅ 🌲 Древний Трент", callback_data=_cb(floor_number, wv_mod.SLOT_BOSS))])
        else:
            rows.append([InlineKeyboardButton(text="🌲 Древний Трент (БОСС)", callback_data=_cb(floor_number, wv_mod.SLOT_BOSS))])

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append([InlineKeyboardButton(text=f"⬆️ Этаж {pend}", callback_data=_cb(floor_number, "ascend"))])

    if floor_data.get_city_for_floor(floor_number):
        rows.append([InlineKeyboardButton(text="🏙️ Город", callback_data=_cb(floor_number, "city"))])

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

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
