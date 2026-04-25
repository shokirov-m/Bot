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
from game.floors import room_clear_floor_10 as rc10_mod
from game.floors import rotten_swamps as rotten_swamps_mod
from game.floors import wave_floor as wv_mod
from game.floors import wandering_npcs as wandering_npcs_mod
from game.floors import explore_floor as exp_mod
from game.floors import explore_floor_4 as exp4_mod
from game.floors import explore_floor_22 as exp22_mod
from game.floors import room_clear_floor_24 as rc24_mod
from game.floors import wave_floor_27 as wv27_mod
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

    if not (tutorial_battle_pending(character) and floor_number == 1):
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
    else:
        # Если учебный бой активен, можно добавить подсказку или оставить пусто
        pass

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

    # Кнопки комнат — последовательная блокировка
    room_names = ["Комната 1", "Комната 2", "Комната 3", "Комната 4", "Комната 5"]
    available_idx = rc_mod.next_available_room_index(beaten)
    for i, btn_code in enumerate(rc_mod.ROOM_BUTTON_CODES):
        room_slots = rc_mod.ROOM_GROUPS[i]
        done = sum(1 for s in room_slots if s in beaten)
        total = len(room_slots)
        if done == total:
            label = f"✅ {room_names[i]}"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, btn_code))])
        elif i == available_idx:
            if done == 0:
                label = f"⚔️ {room_names[i]} [0/{total}]"
            else:
                label = f"⚔️ {room_names[i]} [{done}/{total}]"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, btn_code))])
        else:
            label = f"🔒 {room_names[i]}"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data="rc:locked")])

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


def room_clear_floor_10_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 10 — Тёмные Катакомбы (зачистка комнат)."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    room_names = ["Склеп", "Тёмный коридор", "Лаборатория", "Тронный зал", "Покои Лорда"]
    available_idx = rc10_mod.next_available_room_index(beaten)
    for i, btn_code in enumerate(rc10_mod.ROOM_BUTTON_CODES):
        room_slots = rc10_mod.ROOM_GROUPS[i]
        done = sum(1 for s in room_slots if s in beaten)
        total = len(room_slots)
        if done == total:
            label = f"✅ {room_names[i]}"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, btn_code))])
        elif i == available_idx:
            if done == 0:
                label = f"⚔️ {room_names[i]} [0/{total}]"
            else:
                label = f"⚔️ {room_names[i]} [{done}/{total}]"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, btn_code))])
        else:
            label = f"🔒 {room_names[i]}"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data="rc10:locked")])

    # Кнопка босса — только если все комнаты зачищены
    if rc10_mod.is_boss_unlocked(beaten):
        boss_label = "✅ 👑 Лорд Тьмы" if rc10_mod.SLOT_BOSS in beaten else "👑 Лорд Тьмы (БОСС)"
        rows.append([InlineKeyboardButton(text=boss_label, callback_data=_cb(floor_number, rc10_mod.SLOT_BOSS))])

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


def explore_floor_4_keyboard(
    character: Character,
    *,
    extra: dict | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 4 — механика исследования леса."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    _extra = extra if extra is not None else {}
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    count = exp4_mod.get_explore_count(_extra)
    target = exp4_mod.get_explore_target(_extra)
    pct = exp4_mod.progress_percent(count, target)
    boss_done = exp4_mod.SLOT_BOSS in beaten
    boss_available = exp4_mod.is_boss_available(_extra)

    if not boss_done:
        explore_label = f"🔍 Исследовать [{pct}%]"
        rows.append([InlineKeyboardButton(text=explore_label, callback_data=_cb(floor_number, "e4_explore"))])

    if boss_available:
        if boss_done:
            rows.append([InlineKeyboardButton(text="✅ 🌳 Хранитель Рощи", callback_data=_cb(floor_number, exp4_mod.SLOT_BOSS))])
        else:
            rows.append([InlineKeyboardButton(text="🌳 Хранитель Рощи (БОСС)", callback_data=_cb(floor_number, exp4_mod.SLOT_BOSS))])

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


def explore_floor_4_event_keyboard(
    floor_number: int,
    *,
    extra: dict | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура после не-боевого события исследования леса (этаж 4)."""
    _extra = extra if extra is not None else {}
    boss_available = exp4_mod.is_boss_available(_extra)
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])

    count = exp4_mod.get_explore_count(_extra)
    target = exp4_mod.get_explore_target(_extra)
    pct = exp4_mod.progress_percent(count, target)

    rows: list[list[InlineKeyboardButton]] = []

    if exp4_mod.SLOT_BOSS not in beaten:
        label = f"🔍 Продолжить [{pct}%]"
        rows.append([InlineKeyboardButton(text=label, callback_data=_cb(floor_number, "e4_explore"))])

    if boss_available and exp4_mod.SLOT_BOSS not in beaten:
        rows.append([InlineKeyboardButton(text="🌳 Хранитель Рощи (БОСС)", callback_data=_cb(floor_number, exp4_mod.SLOT_BOSS))])

    rows.append([InlineKeyboardButton(text="🗺️ К этажу", callback_data=_cb(floor_number, "return"))])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def explore_floor_keyboard(
    character: Character,
    *,
    extra: dict | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 8 — механика исследования пещеры."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    _extra = extra if extra is not None else {}
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    count = exp_mod.get_explore_count(_extra)
    target = exp_mod.get_explore_target(_extra)
    pct = exp_mod.progress_percent(count, target)
    boss_done = exp_mod.SLOT_BOSS in beaten
    boss_available = exp_mod.is_boss_available(_extra)

    # Кнопка исследования (скрывается после победы над боссом)
    if not boss_done:
        explore_label = f"🔍 Исследовать [{pct}%]"
        rows.append([InlineKeyboardButton(text=explore_label, callback_data=_cb(floor_number, "exp_explore"))])

    # Кнопка босса — только если 100% достигнуто
    if boss_available:
        if boss_done:
            rows.append([InlineKeyboardButton(text="✅ 🗿 Хранитель Пещеры", callback_data=_cb(floor_number, exp_mod.SLOT_BOSS))])
        else:
            rows.append([InlineKeyboardButton(text="🗿 Хранитель Пещеры (БОСС)", callback_data=_cb(floor_number, exp_mod.SLOT_BOSS))])

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


def explore_event_keyboard(
    floor_number: int,
    *,
    extra: dict | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура после не-боевого события исследования: продолжить или вернуться к этажу."""
    _extra = extra if extra is not None else {}
    boss_available = exp_mod.is_boss_available(_extra)
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])

    count = exp_mod.get_explore_count(_extra)
    target = exp_mod.get_explore_target(_extra)
    pct = exp_mod.progress_percent(count, target)

    rows: list[list[InlineKeyboardButton]] = []

    # Кнопка «Продолжить исследование» (только если босс ещё не победил)
    if not (exp_mod.SLOT_BOSS in beaten):
        label = f"🔍 Продолжить [{pct}%]"
        rows.append([InlineKeyboardButton(text=label, callback_data=_cb(floor_number, "exp_explore"))])

    # Кнопка босса если разблокирован
    if boss_available and exp_mod.SLOT_BOSS not in beaten:
        rows.append([InlineKeyboardButton(text="🗿 Хранитель Пещеры (БОСС)", callback_data=_cb(floor_number, exp_mod.SLOT_BOSS))])

    rows.append([InlineKeyboardButton(text="🗺️ К этажу", callback_data=_cb(floor_number, "return"))])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def explore_floor_22_keyboard(
    character: Character,
    *,
    extra: dict | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 22 — механика исследования Пещеры Теней."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    _extra = extra if extra is not None else {}
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    count = exp22_mod.get_explore_count(_extra)
    target = exp22_mod.get_explore_target(_extra)
    pct = exp22_mod.progress_percent(count, target)
    boss_done = exp22_mod.SLOT_BOSS in beaten
    boss_available = exp22_mod.is_boss_available(_extra)

    if not boss_done:
        explore_label = f"🕯️ Исследовать [{pct}%]"
        rows.append([InlineKeyboardButton(text=explore_label, callback_data=_cb(floor_number, "e22_explore"))])

    if boss_available:
        if boss_done:
            rows.append([InlineKeyboardButton(text="✅ 🕸️ Ткач Теней", callback_data=_cb(floor_number, exp22_mod.SLOT_BOSS))])
        else:
            rows.append([InlineKeyboardButton(text="🕸️ Ткач Теней (БОСС)", callback_data=_cb(floor_number, exp22_mod.SLOT_BOSS))])

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


def explore_floor_22_event_keyboard(
    floor_number: int,
    *,
    extra: dict | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура после не-боевого события исследования Пещеры Теней (этаж 22)."""
    _extra = extra if extra is not None else {}
    boss_available = exp22_mod.is_boss_available(_extra)
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])

    count = exp22_mod.get_explore_count(_extra)
    target = exp22_mod.get_explore_target(_extra)
    pct = exp22_mod.progress_percent(count, target)

    rows: list[list[InlineKeyboardButton]] = []

    if exp22_mod.SLOT_BOSS not in beaten:
        label = f"🕯️ Продолжить [{pct}%]"
        rows.append([InlineKeyboardButton(text=label, callback_data=_cb(floor_number, "e22_explore"))])

    if boss_available and exp22_mod.SLOT_BOSS not in beaten:
        rows.append([InlineKeyboardButton(text="🕸️ Ткач Теней (БОСС)", callback_data=_cb(floor_number, exp22_mod.SLOT_BOSS))])

    rows.append([InlineKeyboardButton(text="🗺️ К этажу", callback_data=_cb(floor_number, "return"))])
    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def room_clear_floor_24_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 24 — Пещеры Теней (зачистка комнат)."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    room_names = ["Вход в пещеру", "Туннель эха", "Кристальный грот", "Пропасть гарпий", "Алтарь тьмы"]
    available_idx = rc24_mod.next_available_room_index(beaten)
    for i, btn_code in enumerate(rc24_mod.ROOM_BUTTON_CODES):
        room_slots = rc24_mod.ROOM_GROUPS[i]
        done = sum(1 for s in room_slots if s in beaten)
        total = len(room_slots)
        if done == total:
            label = f"✅ {room_names[i]}"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, btn_code))])
        elif i == available_idx:
            label = f"⚔️ {room_names[i]} [{done}/{total}]" if done > 0 else f"⚔️ {room_names[i]} [0/{total}]"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data=_cb(floor_number, btn_code))])
        else:
            label = f"🔒 {room_names[i]}"
            rows.append([InlineKeyboardButton(text=label[:36], callback_data="rc24:locked")])

    if rc24_mod.is_boss_unlocked(beaten):
        boss_label = "✅ 🌑 Теневой Владыка" if rc24_mod.SLOT_BOSS in beaten else "🌑 Теневой Владыка (БОСС)"
        rows.append([InlineKeyboardButton(text=boss_label, callback_data=_cb(floor_number, rc24_mod.SLOT_BOSS))])

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


def wave_floor_27_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 27 — волны теней."""
    floor_number = int(character.floor_number)
    highest = int(character.highest_floor_reached)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_class_arc_rows(character))
    rows.extend(_pet_rows(character, floor_number))

    wave_labels = {
        wv27_mod.SLOT_WAVE_1: ("🌑 Волна 1 — Разведчики", "✅ Волна 1 — Разведчики"),
        wv27_mod.SLOT_WAVE_2: ("🦇 Волна 2 — Охотники", "✅ Волна 2 — Охотники"),
        wv27_mod.SLOT_WAVE_3: ("👻 Волна 3 — Пустотный призрак", "✅ Волна 3 — Призрак"),
    }
    current_slot = wv27_mod.current_available_slot(beaten)

    for slot, (label_active, label_done) in wave_labels.items():
        if slot in beaten:
            rows.append([InlineKeyboardButton(text=label_done, callback_data=_cb(floor_number, slot))])
        elif slot == current_slot:
            rows.append([InlineKeyboardButton(text=label_active, callback_data=_cb(floor_number, slot))])
        else:
            rows.append([InlineKeyboardButton(text=f"🔒 {label_active[2:]}", callback_data="wv27:locked")])

    if wv27_mod.SLOT_WAVE_3 in beaten:
        if wv27_mod.SLOT_BOSS in beaten:
            rows.append([InlineKeyboardButton(text="✅ 🌑 Ночной Охотник", callback_data=_cb(floor_number, wv27_mod.SLOT_BOSS))])
        else:
            rows.append([InlineKeyboardButton(text="🌑 Ночной Охотник (БОСС)", callback_data=_cb(floor_number, wv27_mod.SLOT_BOSS))])

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
