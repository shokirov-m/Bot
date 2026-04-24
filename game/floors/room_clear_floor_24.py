"""
Этаж 24 — Пещеры Теней: зачистка комнат (5 комнат, 2-3 монстра последовательно).

Механика аналогична этажам 5 и 10:
  • при входе открыта только 1-я комната, остальные 🔒
  • в каждой комнате последовательные бои (2-й и 3-й монстр — бесплатно по стамине)
  • комната 4 — мини-босс (Повелитель гарпий)
  • после зачистки всех 5 комнат появляется кнопка финального босса
  • победа над боссом → этаж 25

Прогресс хранится в floor_progress.extra["slots_cleared"].
Слоты вида r24_r{room}_{monster}.
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ──────────────────────────────────────────────────────────────
ROOM_CLEAR_FLOOR_24 = 24
TOTAL_ROOMS = 5
META_KEY = "room_clear_24_v1"

SLOT_BOSS = "r24_boss"

# Кнопочные коды (один на комнату)
ROOM_BUTTON_CODES: list[str] = [f"r24_r{i}" for i in range(TOTAL_ROOMS)]

# Группы слотов монстров внутри каждой комнаты
ROOM_GROUPS: list[list[str]] = [
    ["r24_r0_m0", "r24_r0_m1"],                    # Комната 1: 2 монстра
    ["r24_r1_m0", "r24_r1_m1", "r24_r1_m2"],       # Комната 2: 3 монстра
    ["r24_r2_m0", "r24_r2_m1"],                    # Комната 3: 2 монстра
    ["r24_r3_m0"],                                 # Комната 4: мини-босс
    ["r24_r4_m0", "r24_r4_m1"],                    # Комната 5: 2 монстра
]

# Плоский список всех слотов монстров
SLOT_ROOMS: list[str] = [s for grp in ROOM_GROUPS for s in grp]

# Все слоты
ROOM_CLEAR_24_ALL_SLOTS: frozenset[str] = frozenset(
    ROOM_BUTTON_CODES + SLOT_ROOMS + [SLOT_BOSS]
)

# Комната с мини-боссом
ROOM_DUO_INDEX = 3

# ── Шаблоны монстров по комнатам ─────────────────────────────────────────────

# Комната 1 — Вход в пещеру (2 монстра)
_C1: list[MonsterTemplate] = [
    MonsterTemplate("r24_r0_bat",    "Рой летучих",     "🦇", "dark",
                    "Стая летучих мышей бросается из темноты."),
    MonsterTemplate("r24_r0_crawler","Пещерный ползун", "🪨", "earth",
                    "Приполз из глубины, почуяв живое."),
]

# Комната 2 — Туннель эха (3 монстра)
_C2: list[MonsterTemplate] = [
    MonsterTemplate("r24_r1_shade",   "Теневой дух",   "🌑", "dark",
                    "Шепчет проклятия в темноте тоннеля."),
    MonsterTemplate("r24_r1_wisp",    "Огонёк-обман",  "🔥", "fire",
                    "Заманивает жертву к обрыву."),
    MonsterTemplate("r24_r1_echo",    "Эхо-призрак",   "👻", "dark",
                    "Отражение чьей-то смерти в этих стенах."),
]

# Комната 3 — Кристальный грот (2 монстра)
_C3: list[MonsterTemplate] = [
    MonsterTemplate("r24_r2_stalactite", "Живой сталактит", "🪨", "earth",
                    "Камень ожил и тянется к добыче."),
    MonsterTemplate("r24_r2_weaver",     "Ткач мрака",      "🕸️", "dark",
                    "Расставил нити-ловушки по всему гроту."),
]

# Комната 4 — Пропасть гарпий (мини-босс)
_C4: list[MonsterTemplate] = [
    MonsterTemplate("r24_r3_harpy_lord", "Повелитель гарпий", "🦅", "dark",
                    "Крылатый демон управляет всей стаей пещерных гарпий. "
                    "Его крик разрушает камень."),
]

# Комната 5 — Алтарь тьмы (2 монстра)
_C5: list[MonsterTemplate] = [
    MonsterTemplate("r24_r4_dark_acolyte", "Тёмный жрец",    "🔱", "dark",
                    "Служитель культа тьмы, проводящий ритуал."),
    MonsterTemplate("r24_r4_shadow_beast", "Теневой зверь",  "🐺", "dark",
                    "Призванный из тьмы страж алтаря."),
]

# Шаблоны, сгруппированные по комнатам
_ROOM_TEMPLATES: list[list[MonsterTemplate]] = [_C1, _C2, _C3, _C4, _C5]

# Шаблон финального босса
_TMPL_BOSS = MonsterTemplate(
    "boss_shadow_lord_24",
    "Теневой Владыка",
    "🌑",
    "dark",
    "Древний повелитель пещерной тьмы. Его тело соткано из живых теней — "
    "он не умирает, пока горит хоть один светоч.",
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


def is_room_clear_floor_24(floor_number: int) -> bool:
    return int(floor_number) == ROOM_CLEAR_FLOOR_24


def room_index_for_button(button_code: str) -> int | None:
    """Возвращает индекс комнаты (0-4) для кода кнопки r24_r0..r24_r4, иначе None."""
    if button_code in ROOM_BUTTON_CODES:
        try:
            return int(button_code.replace("r24_r", ""))
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
    """Все комнаты зачищены → доступен Теневой Владыка."""
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
    if int(character.floor_number) != ROOM_CLEAR_FLOOR_24:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_room_clear_banner_html(defeated_slots: frozenset[str]) -> str:
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return "🌑 <b>Пещера зачищена!</b> Теневой Владыка повержен — путь на 25-й этаж открыт."

    cleared_rooms = rooms_cleared_count(defeated_slots)
    total_mon = total_monsters_cleared(defeated_slots)
    total_slots = len(SLOT_ROOMS)

    hint = " → <b>Теневой Владыка пробудился!</b>" if cleared_rooms == TOTAL_ROOMS else ""
    room_bar = "🟣" * cleared_rooms + "⬜" * (TOTAL_ROOMS - cleared_rooms)
    return (
        f"🕯️ <b>Пещеры Теней</b> [{room_bar}] {cleared_rooms}/{TOTAL_ROOMS} комнат{hint}\n"
        f"Монстров: {total_mon}/{total_slots} "
        f"<i>(в каждой комнате 2-3 последовательных боя)</i>"
    )
