"""
Этаж 26 — Зал сомнений: зачистка комнат (5 комнат). После победы над боссом
монстры на этаже исчезают навсегда; открывается «Тёмный проход» к чёрному рынку.

Прогресс: floor_progress.extra[\"slots_cleared\"]; постоянный флаг — character.meta shadow_market_v1.floor_26_cleared.
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

ROOM_CLEAR_FLOOR_26 = 26
TOTAL_ROOMS = 5
META_KEY = "room_clear_26_v1"

SLOT_BOSS = "r26_boss"

ROOM_BUTTON_CODES: list[str] = [f"r26_r{i}" for i in range(TOTAL_ROOMS)]

ROOM_GROUPS: list[list[str]] = [
    ["r26_r0_m0", "r26_r0_m1"],
    ["r26_r1_m0", "r26_r1_m1", "r26_r1_m2"],
    ["r26_r2_m0", "r26_r2_m1"],
    ["r26_r3_m0"],
    ["r26_r4_m0", "r26_r4_m1"],
]

SLOT_ROOMS: list[str] = [s for grp in ROOM_GROUPS for s in grp]

ROOM_CLEAR_26_ALL_SLOTS: frozenset[str] = frozenset(
    ROOM_BUTTON_CODES + SLOT_ROOMS + [SLOT_BOSS],
)

ROOM_DUO_INDEX = 3

_C1: list[MonsterTemplate] = [
    MonsterTemplate("r26_r0_wraith", "Шепчущий призрак", "👻", "dark", "Виток тьмы у входа в зал."),
    MonsterTemplate("r26_r0_sentinel", "Сомневающийся страж", "🗿", "earth", "Каменная статуя ожила, чтобы задать вопрос без слов."),
]

_C2: list[MonsterTemplate] = [
    MonsterTemplate("r26_r1_gloom", "Порождение мрака", "🌑", "dark", "Сгусток нерешительности."),
    MonsterTemplate("r26_r1_mirror", "Двойник в зеркале", "🪞", "dark", "Отражение бьёт так же больно, как оригинал."),
    MonsterTemplate("r26_r1_moth", "Мотылёк забвения", "🦋", "dark", "Крылья осыпают пылью, от которой клонит ко сну."),
]

_C3: list[MonsterTemplate] = [
    MonsterTemplate("r26_r2_chain", "Кандалы живые", "⛓️", "earth", "Металл тянется к лодыжкам."),
    MonsterTemplate("r26_r2_judge", "Судья без лица", "⚖️", "dark", "Вынесет приговор, пока ты думаешь."),
]

_C4: list[MonsterTemplate] = [
    MonsterTemplate("r26_r3_doubt_lord", "Владыка сомнений", "😶‍🌫️", "dark", "Каждый его удар — вопрос: «А стоило ли идти сюда?»"),
]

_C5: list[MonsterTemplate] = [
    MonsterTemplate("r26_r4_usher", "Проводник теней", "🕯️", "dark", "Ведёт к проходу, откуда не возвращаются прежними."),
    MonsterTemplate("r26_r4_broker", "Брокер страха", "💀", "dark", "Торгует чужими кошмарами."),
]

_ROOM_TEMPLATES: list[list[MonsterTemplate]] = [_C1, _C2, _C3, _C4, _C5]

_TMPL_BOSS = MonsterTemplate(
    "boss_shadow_gatekeeper_26",
    "Привратник Чёрного Рынка",
    "🗝️",
    "dark",
    "Хранитель тайного прохода. Пока он стоит — нет ни рынка, ни наёмников. "
    "Падёт — зал опустеет навсегда.",
)

_ROOM_SPAWNS: list[list[FloorMonsterSpawn]] = []
for _room_idx, (_slots, _tmpls) in enumerate(zip(ROOM_GROUPS, _ROOM_TEMPLATES)):
    _room_spawns: list[FloorMonsterSpawn] = []
    for _m_idx, (_slot, _tmpl) in enumerate(zip(_slots, _tmpls)):
        if _room_idx == ROOM_DUO_INDEX:
            _room_spawns.append(FloorMonsterSpawn(
                slot_code=_slot,
                template=_tmpl,
                is_elite=False,
                is_mini_boss=True,
                is_major_boss=False,
            ))
        else:
            _is_elite = (_m_idx == len(_slots) - 1)
            _room_spawns.append(FloorMonsterSpawn(
                slot_code=_slot,
                template=_tmpl,
                is_elite=_is_elite,
                is_mini_boss=False,
                is_major_boss=False,
            ))
    _ROOM_SPAWNS.append(_room_spawns)

SPAWN_BOSS = FloorMonsterSpawn(
    slot_code=SLOT_BOSS,
    template=_TMPL_BOSS,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=True,
)


def all_room_clear_spawns() -> list[FloorMonsterSpawn]:
    result: list[FloorMonsterSpawn] = []
    for grp in _ROOM_SPAWNS:
        result.extend(grp)
    result.append(SPAWN_BOSS)
    return result


def spawn_by_slot(slot: str) -> FloorMonsterSpawn | None:
    for s in all_room_clear_spawns():
        if s.slot_code == slot:
            return s
    return None


def is_room_clear_floor_26(floor_number: int) -> bool:
    return int(floor_number) == ROOM_CLEAR_FLOOR_26


def room_index_for_button(button_code: str) -> int | None:
    if button_code in ROOM_BUTTON_CODES:
        try:
            return int(button_code.replace("r26_r", ""))
        except ValueError:
            pass
    return None


def next_slot_in_room(room_idx: int, beaten: frozenset[str]) -> str | None:
    if room_idx < 0 or room_idx >= TOTAL_ROOMS:
        return None
    for slot in ROOM_GROUPS[room_idx]:
        if slot not in beaten:
            return slot
    return None


def is_room_complete(room_idx: int, beaten: frozenset[str]) -> bool:
    if room_idx < 0 or room_idx >= TOTAL_ROOMS:
        return False
    return all(s in beaten for s in ROOM_GROUPS[room_idx])


def rooms_cleared_count(defeated_slots: frozenset[str]) -> int:
    return sum(1 for i in range(TOTAL_ROOMS) if is_room_complete(i, defeated_slots))


def total_monsters_cleared(defeated_slots: frozenset[str]) -> int:
    return sum(1 for s in SLOT_ROOMS if s in defeated_slots)


def is_boss_unlocked(defeated_slots: frozenset[str]) -> bool:
    return all(is_room_complete(i, defeated_slots) for i in range(TOTAL_ROOMS))


def next_available_room_index(beaten: frozenset[str]) -> int:
    for i in range(TOTAL_ROOMS):
        if not is_room_complete(i, beaten):
            return i
    return TOTAL_ROOMS


def slot_room_and_monster_index(slot: str) -> tuple[int, int] | None:
    for room_idx, room_slots in enumerate(ROOM_GROUPS):
        for monster_idx, s in enumerate(room_slots):
            if s == slot:
                return room_idx, monster_idx
    return None


def next_slot_after_defeat(slot: str) -> str | None:
    result = slot_room_and_monster_index(slot)
    if result is None:
        return None
    room_idx, monster_idx = result
    room_slots = ROOM_GROUPS[room_idx]
    if monster_idx + 1 < len(room_slots):
        return room_slots[monster_idx + 1]
    return None


def ensure_started(character: Character) -> None:
    if int(character.floor_number) != ROOM_CLEAR_FLOOR_26:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_room_clear_banner_html(defeated_slots: frozenset[str]) -> str:
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return (
            "🗝️ <b>Зал сомнений пуст.</b> Привратник пал — монстры больше не вернутся. "
            "Открыт <b>Тёмный проход</b> к рынку «Тени Башни». Поднимись на <b>27</b> этаж, когда будешь готов."
        )

    cleared_rooms = rooms_cleared_count(defeated_slots)
    total_mon = total_monsters_cleared(defeated_slots)
    total_slots = len(SLOT_ROOMS)

    hint = " → <b>Привратник ждёт!</b>" if cleared_rooms == TOTAL_ROOMS else ""
    room_bar = "⬛" * cleared_rooms + "⬜" * (TOTAL_ROOMS - cleared_rooms)
    return (
        f"🗝️ <b>Зал сомнений</b> [{room_bar}] {cleared_rooms}/{TOTAL_ROOMS} залов{hint}\n"
        f"Монстров: {total_mon}/{total_slots} "
        f"<i>(последовательные бои в каждом зале)</i>"
    )
