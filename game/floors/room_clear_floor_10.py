"""
Этаж 10 — Тёмные Катакомбы: зачистка комнат (5 комнат, 2-3 монстра в каждой последовательно).

Механика полностью аналогична этажу 5 (room_clear_floor.py):
  • при входе на этаж открыта только 1-я комната, остальные 🔒
  • в каждой комнате последовательные бои (2-й и 3-й монстр не тратят стамину)
  • комната 4 — одновременный бой с мини-боссом (два демона разом)
  • после зачистки всех комнат появляется кнопка босса
  • победа над боссом → этаж 11

Прогресс хранится в floor_progress.extra["slots_cleared"] — стандартный механизм.
Слоты вида r10_r{room}_{monster}.
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ──────────────────────────────────────────────────────────────
ROOM_CLEAR_FLOOR_10 = 10
TOTAL_ROOMS = 5
META_KEY = "room_clear_10_v1"

SLOT_BOSS = "r10_boss"

# Кнопочные коды (один на комнату)
ROOM_BUTTON_CODES: list[str] = [f"r10_r{i}" for i in range(TOTAL_ROOMS)]

# Группы слотов монстров внутри каждой комнаты
ROOM_GROUPS: list[list[str]] = [
    ["r10_r0_m0", "r10_r0_m1"],                    # Комната 1: 2 монстра
    ["r10_r1_m0", "r10_r1_m1", "r10_r1_m2"],       # Комната 2: 3 монстра
    ["r10_r2_m0", "r10_r2_m1"],                    # Комната 3: 2 монстра
    ["r10_r3_m0"],                                 # Комната 4: 1 бой — 2 демона ОДНОВРЕМЕННО
    ["r10_r4_m0", "r10_r4_m1"],                    # Комната 5: 2 монстра
]

# Плоский список всех слотов монстров
SLOT_ROOMS: list[str] = [s for grp in ROOM_GROUPS for s in grp]

# Все слоты: кнопочные + монстры + босс
ROOM_CLEAR_10_ALL_SLOTS: frozenset[str] = frozenset(
    ROOM_BUTTON_CODES + SLOT_ROOMS + [SLOT_BOSS]
)

# Комната с одновременным боем (мини-босс)
ROOM_DUO_INDEX = 3

# ── Шаблоны монстров по комнатам ─────────────────────────────────────────────

# Комната 1 — Склеп (2 монстра)
_C1: list[MonsterTemplate] = [
    MonsterTemplate("r10_r0_zombie",   "Склепный мертвец",   "🧟", "dark",
                    "Поднялся из забытой могилы."),
    MonsterTemplate("r10_r0_wraith",   "Призрак склепа",     "👻", "dark",
                    "Дух, прикованный к старому гробу."),
]

# Комната 2 — Тёмный коридор (3 монстра)
_C2: list[MonsterTemplate] = [
    MonsterTemplate("r10_r1_bat",      "Тёмная летучая мышь", "🦇", "dark",
                    "Стремительно пикирует из тени."),
    MonsterTemplate("r10_r1_imp",      "Бесёнок-разведчик",   "😈", "dark",
                    "Мелкий демон с острыми когтями."),
    MonsterTemplate("r10_r1_shadow",   "Живая тень",           "🌑", "dark",
                    "Тень, отделившаяся от стены."),
]

# Комната 3 — Алхимическая лаборатория (2 монстра)
_C3: list[MonsterTemplate] = [
    MonsterTemplate("r10_r2_golem",    "Кислотный голем",     "🧪", "dark",
                    "Создан из отравленной слизи."),
    MonsterTemplate("r10_r2_lich",     "Недо-лич",            "💀", "dark",
                    "Некромант, не завершивший ритуал бессмертия."),
]

# Комната 4 — Тронный зал (1 бой: два демона одновременно → мини-босс)
_C4: list[MonsterTemplate] = [
    MonsterTemplate("r10_r3_twin_demons", "Братья-демоны", "👹", "dark",
                    "Два старших демона атакуют слаженно — огонь и лёд разом."),
]

# Комната 5 — Покои Лорда Тьмы (2 монстра)
_C5: list[MonsterTemplate] = [
    MonsterTemplate("r10_r4_dark_knight", "Рыцарь Тьмы",    "🗡️", "dark",
                    "Закованный в чёрные доспехи телохранитель."),
    MonsterTemplate("r10_r4_herald",      "Глашатай Мрака",  "🔱", "dark",
                    "Служитель Лорда, призывающий тёмную энергию."),
]

# Шаблоны, сгруппированные по комнатам
_ROOM_TEMPLATES: list[list[MonsterTemplate]] = [_C1, _C2, _C3, _C4, _C5]

# Шаблон босса
_TMPL_BOSS = MonsterTemplate(
    "boss_dark_lord_10",
    "Лорд Тьмы",
    "👑",
    "dark",
    "Повелитель катакомб восседает на троне из теней. Его власть питается страхом живых.",
)

# ── Объекты FloorMonsterSpawn ───────────────────────────────────────────────

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


# ── Публичные функции ───────────────────────────────────────────────────────

def all_room_clear_spawns() -> list[FloorMonsterSpawn]:
    """Все спауны сценария (монстры всех комнат + босс) — для tower_progress."""
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


def is_room_clear_floor_10(floor_number: int) -> bool:
    return int(floor_number) == ROOM_CLEAR_FLOOR_10


def room_index_for_button(button_code: str) -> int | None:
    """Возвращает индекс комнаты (0-4) для кода кнопки r10_r0..r10_r4, иначе None."""
    if button_code in ROOM_BUTTON_CODES:
        try:
            return int(button_code.replace("r10_r", ""))
        except ValueError:
            pass
    return None


def next_slot_in_room(room_idx: int, beaten: frozenset[str]) -> str | None:
    """Возвращает слот следующего незачищенного монстра в комнате, или None."""
    if room_idx < 0 or room_idx >= TOTAL_ROOMS:
        return None
    for slot in ROOM_GROUPS[room_idx]:
        if slot not in beaten:
            return slot
    return None


def is_room_complete(room_idx: int, beaten: frozenset[str]) -> bool:
    """True если все монстры комнаты побеждены."""
    if room_idx < 0 or room_idx >= TOTAL_ROOMS:
        return False
    return all(s in beaten for s in ROOM_GROUPS[room_idx])


def rooms_cleared_count(defeated_slots: frozenset[str]) -> int:
    """Количество полностью пройденных комнат."""
    return sum(1 for i in range(TOTAL_ROOMS) if is_room_complete(i, defeated_slots))


def total_monsters_cleared(defeated_slots: frozenset[str]) -> int:
    """Суммарное кол-во побеждённых монстров (не считая босса)."""
    return sum(1 for s in SLOT_ROOMS if s in defeated_slots)


def is_boss_unlocked(defeated_slots: frozenset[str]) -> bool:
    """Все комнаты зачищены → доступен Лорд Тьмы."""
    return all(is_room_complete(i, defeated_slots) for i in range(TOTAL_ROOMS))


def next_available_room_index(beaten: frozenset[str]) -> int:
    """Индекс первой незачищенной комнаты. Если все очищены — возвращает TOTAL_ROOMS."""
    for i in range(TOTAL_ROOMS):
        if not is_room_complete(i, beaten):
            return i
    return TOTAL_ROOMS


def slot_room_and_monster_index(slot: str) -> tuple[int, int] | None:
    """Возвращает (room_idx, monster_idx) для слота монстра, или None."""
    for room_idx, room_slots in enumerate(ROOM_GROUPS):
        for monster_idx, s in enumerate(room_slots):
            if s == slot:
                return room_idx, monster_idx
    return None


def next_slot_after_defeat(slot: str) -> str | None:
    """Следующий слот монстра в той же комнате после победы, или None если комната зачищена."""
    result = slot_room_and_monster_index(slot)
    if result is None:
        return None
    room_idx, monster_idx = result
    room_slots = ROOM_GROUPS[room_idx]
    if monster_idx + 1 < len(room_slots):
        return room_slots[monster_idx + 1]
    return None


def ensure_started(character: Character) -> None:
    if int(character.floor_number) != ROOM_CLEAR_FLOOR_10:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_room_clear_banner_html(defeated_slots: frozenset[str]) -> str:
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return "👑 <b>Катакомбы зачищены!</b> Лорд Тьмы пал — путь на 11-й этаж открыт."

    cleared_rooms = rooms_cleared_count(defeated_slots)
    total_mon = total_monsters_cleared(defeated_slots)
    total_slots = len(SLOT_ROOMS)

    hint = " → <b>Лорд пробудился!</b>" if cleared_rooms == TOTAL_ROOMS else ""
    room_bar = "🟥" * cleared_rooms + "⬜" * (TOTAL_ROOMS - cleared_rooms)
    return (
        f"💀 <b>Тёмные Катакомбы</b> [{room_bar}] {cleared_rooms}/{TOTAL_ROOMS} комнат{hint}\n"
        f"Монстров: {total_mon}/{total_slots} "
        f"<i>(в каждой комнате 2-3 последовательных боя)</i>"
    )
