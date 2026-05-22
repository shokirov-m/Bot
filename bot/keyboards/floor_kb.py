"""
Inline-клавиатура действий на этаже: монстры, город-хаб, навигация по этажам.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.menu_kb import menu_nav_button_row
from db.models.character import Character
from game.characters import pets as pets_mod
from game.tower.progression import floor_data
from game.tower.mechanics import registry as mech
import game.tower.progression.wandering_npcs as wandering_npcs_mod

forest_beginnings_mod = mech.forest_beginnings
long_floor_mod = mech.long_floor_mod
rotten_swamps_mod = mech.rotten_swamps
rc_mod = mech.room_clear_floor
rc10_mod = mech.room_clear_floor_10
rc24_mod = mech.room_clear_floor_24
rc30_mod = mech.room_clear_floor_30
rc40_mod = mech.room_clear_floor_40
rc26_mod = mech.room_clear_floor_26
wv_mod = mech.wave_floor
wv27_mod = mech.wave_floor_27
exp_mod = mech.explore_floor
exp4_mod = mech.explore_floor_4
exp22_mod = mech.explore_floor_22
from game.enemies.floors.spawns import FloorMonsterSpawn
from game.tower.progression.tower_ascent import tower_next_floor_pending
from services.combat.tutorial_battle_service import tutorial_battle_pending


def _navigation_max_floor(character: Character, nav_ceiling: int | None) -> int:
    if nav_ceiling is not None:
        return int(nav_ceiling)
    return int(character.highest_floor_reached)


def _cb(floor_number: int, code: str) -> str:
    """Короткий callback: fl:<этаж>:<код слота>."""
    return f"fl:{floor_number}:{code}"


def _append_city_hub_row(
    rows: list[list[InlineKeyboardButton]],
    character: Character,
    floor_number: int,
) -> None:
    """Кнопка безопасного города между ярусами (не на боевом номере)."""
    lbl = floor_data.city_button_label(
        int(floor_number),
        highest_reached=int(character.highest_floor_reached),
    )
    if not lbl:
        return
    if len(lbl) > 36:
        lbl = lbl[:33] + "…"
    rows.append(
        [
            InlineKeyboardButton(
                text=lbl,
                callback_data=f"hub:go:{_city_hub_floor_for_label(character, floor_number)}",
            ),
        ],
    )


def _city_hub_floor_for_label(character: Character, floor_number: int) -> int:
    from game.locations import hub_floors as hf

    city = floor_data.get_city_for_floor(
        int(floor_number),
        highest_reached=int(character.highest_floor_reached),
    )
    if city is None:
        return hf.city_hub_floor(0)
    return hf.city_hub_floor(int(city.after_floor))


def _append_tower_field_repair_row(rows: list[list[InlineKeyboardButton]], floor_number: int) -> None:
    """Починка за золото с карты этажа (как в городской кузнице), на сценарных этажах."""
    from game.locations import forge as forge_loc

    if forge_loc.tower_field_repair_allowed(int(floor_number)):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔨 Починка экипировки",
                    callback_data=f"frg:rpr:{int(floor_number)}",
                ),
            ],
        )


def show_floor_secret_search_button(floor_number: int) -> bool:
    """Кнопка тайника на карте этажа (логика: services.secret_chest_service)."""
    return int(floor_number) >= 2


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


def floor_screen_keyboard(
    character: Character,
    spawns: list[FloorMonsterSpawn],
    *,
    defeated_slots: frozenset[str] | set[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Кнопки этажа: ветка класса, цели, город, навигация 1..max."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    if tutorial_battle_pending(character) and floor_number == 2:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎓 Учебный бой наставника",
                    callback_data=_cb(floor_number, "tutorial"),
                ),
            ],
        )

    # Сюжетные NPC на Этаже 1
    if floor_number == 1:
        rows.append([
            InlineKeyboardButton(
                text="📜 Сюжетные NPC",
                callback_data=_cb(floor_number, "story_npc"),
            )
        ])

    rows.extend(_pet_rows(character, floor_number))

    if (
        forest_beginnings_mod.is_forest_beginnings_zone(floor_number)
        and floor_number != 1
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

    wnpc = None if floor_number == 1 else wandering_npcs_mod.wandering_npc_for_floor(
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

    import services.progression.pack_npc_quest_service as _pqn_svc

    zone_fl = floor_data.get_zone_for_floor(int(floor_number))
    if _pqn_svc.list_npcs_on_floor(int(floor_number)):
        hub_lbl = f"{zone_fl.emoji} Мастера зоны"[:36]
        rows.append(
            [
                InlineKeyboardButton(
                    text=hub_lbl,
                    callback_data=f"pqn:hub:{int(floor_number)}",
                ),
            ],
        )

    buffer: list[InlineKeyboardButton] = []

    def flush() -> None:
        nonlocal buffer
        if buffer:
            rows.append(buffer)
            buffer = []

    from game.tower.combat import boss_retry_cooldown as boss_retry_mod

    if not (tutorial_battle_pending(character) and floor_number == 2):
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
                if sp.is_major_boss:
                    cd_left = boss_retry_mod.retry_seconds_left(character, floor_number)
                    if cd_left > 0:
                        suffix = f" ⏳{cd_left // 60}м"
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

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
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


def long_floor_screen_keyboard(character: Character, *, nav_ceiling: int | None = None) -> InlineKeyboardMarkup:
    """Клавиатура пилотного длинного этажа (этаж 15): фазы сценария + навигация как на обычном этаже."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    ph = long_floor_mod.current_phase(character)
    rows: list[list[InlineKeyboardButton]] = []

    if tutorial_battle_pending(character) and floor_number == 2:
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
        and floor_number != 1
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

    wnpc = None if floor_number == 1 else wandering_npcs_mod.wandering_npc_for_floor(
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

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
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


def room_clear_floor_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 5 — зачистка комнат."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wave_floor_screen_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 10 — волны вторжения (последовательно)."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def room_clear_floor_10_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 10 — Тёмные Катакомбы (зачистка комнат)."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def explore_floor_4_keyboard(
    character: Character,
    *,
    extra: dict | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 4 — механика исследования леса."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    _extra = extra if extra is not None else {}
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
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
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 8 — механика исследования пещеры."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    _extra = extra if extra is not None else {}
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
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
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 22 — механика исследования Пещеры Теней."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    _extra = extra if extra is not None else {}
    beaten = frozenset(str(x) for x in _extra.get("slots_cleared") or [])
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
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
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 24 — Пещеры Теней (зачистка комнат)."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def room_clear_floor_30_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Этаж 30 — залы тьмы, затем босс зоны."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_pet_rows(character, floor_number))

    room_names = [
        "Зал отражений",
        "Галерея шипов",
        "Колодец холода",
        "Свод ткача",
        "Алтарь ночи",
    ]
    available_idx = rc30_mod.next_available_room_index(beaten)
    for i, btn_code in enumerate(rc30_mod.ROOM_BUTTON_CODES):
        room_slots = rc30_mod.ROOM_GROUPS[i]
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
            rows.append([InlineKeyboardButton(text=label[:36], callback_data="rc30:locked")])

    if rc30_mod.is_boss_unlocked(beaten):
        boss_label = "✅ 🌑 Ночной охотник" if rc30_mod.SLOT_BOSS in beaten else "🌑 Ночной охотник (БОСС)"
        rows.append([InlineKeyboardButton(text=boss_label, callback_data=_cb(floor_number, rc30_mod.SLOT_BOSS))])

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append([InlineKeyboardButton(text=f"⬆️ Этаж {pend}", callback_data=_cb(floor_number, "ascend"))])

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def room_clear_floor_40_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Этаж 40 — ледяные залы, затем босс зоны."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_pet_rows(character, floor_number))

    room_names = [
        "Ледяной зев",
        "Снежный туннель",
        "Ущелье ветров",
        "Логово тролля",
        "Ледник падений",
    ]
    available_idx = rc40_mod.next_available_room_index(beaten)
    for i, btn_code in enumerate(rc40_mod.ROOM_BUTTON_CODES):
        room_slots = rc40_mod.ROOM_GROUPS[i]
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
            rows.append([InlineKeyboardButton(text=label[:36], callback_data="rc40:locked")])

    if rc40_mod.is_boss_unlocked(beaten):
        boss_label = "✅ ❄️ Король ледников" if rc40_mod.SLOT_BOSS in beaten else "❄️ Король ледников (БОСС)"
        rows.append([InlineKeyboardButton(text=boss_label, callback_data=_cb(floor_number, rc40_mod.SLOT_BOSS))])

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append([InlineKeyboardButton(text=f"⬆️ Этаж {pend}", callback_data=_cb(floor_number, "ascend"))])

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def room_clear_floor_26_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Этаж 26 — зал сомнений (зачистка комнат)."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_pet_rows(character, floor_number))

    room_names = ["Порог шёпота", "Зеркальный коридор", "Зал кандалов", "Площадь сомнений", "Переход"]
    available_idx = rc26_mod.next_available_room_index(beaten)
    for i, btn_code in enumerate(rc26_mod.ROOM_BUTTON_CODES):
        room_slots = rc26_mod.ROOM_GROUPS[i]
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
            rows.append([InlineKeyboardButton(text=label[:36], callback_data="rc26:locked")])

    if rc26_mod.is_boss_unlocked(beaten):
        boss_label = "✅ 🗝️ Привратник" if rc26_mod.SLOT_BOSS in beaten else "🗝️ Привратник (БОСС)"
        rows.append([InlineKeyboardButton(text=boss_label, callback_data=_cb(floor_number, rc26_mod.SLOT_BOSS))])

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append([InlineKeyboardButton(text=f"⬆️ Этаж {pend}", callback_data=_cb(floor_number, "ascend"))])

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def room_clear_floor_26_cleared_keyboard(
    character: Character,
    *,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Этаж 26 после зачистки: только тёмный проход и навигация."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    rows: list[list[InlineKeyboardButton]] = []

    rows.extend(_pet_rows(character, floor_number))

    rows.append(
        [InlineKeyboardButton(text="🌑 Тёмный проход (рынок)", callback_data=_cb(floor_number, "shadow_pass"))],
    )

    pend = tower_next_floor_pending(character)
    if pend is not None:
        rows.append([InlineKeyboardButton(text=f"⬆️ Этаж {pend}", callback_data=_cb(floor_number, "ascend"))])

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wave_floor_27_keyboard(
    character: Character,
    *,
    defeated_slots: frozenset[str] | None = None,
    nav_ceiling: int | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура этажа 27 — волны теней."""
    floor_number = int(character.floor_number)
    highest = _navigation_max_floor(character, nav_ceiling)
    beaten = defeated_slots if defeated_slots is not None else frozenset()
    rows: list[list[InlineKeyboardButton]] = []

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

    _append_tower_field_repair_row(rows, floor_number)

    _append_city_hub_row(rows, character, floor_number)

    nav: list[InlineKeyboardButton] = []
    if floor_number < highest:
        nav.append(InlineKeyboardButton(text="⬆️ Выше", callback_data="flnav:up"))
    if floor_number > 1:
        nav.append(InlineKeyboardButton(text="⬇️ Ниже", callback_data="flnav:dn"))
    if show_floor_secret_search_button(floor_number):
        nav.append(InlineKeyboardButton(text="🔮 Тайник", callback_data=_cb(floor_number, "srch")))
    rows.append(nav)

    rows.append(menu_nav_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def secret_result_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    """После открытия сундука / текста обыска — вернуться к списку целей."""
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


def secret_chest_closed_keyboard(floor_number: int) -> InlineKeyboardMarkup:
    """Закрытый сундук тайника: открыть или уйти на карту этажа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗝️ Открыть",
                    callback_data=_cb(floor_number, "chest_open"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗺️ К этажу",
                    callback_data=_cb(floor_number, "return"),
                ),
            ],
            menu_nav_button_row(),
        ],
    )
