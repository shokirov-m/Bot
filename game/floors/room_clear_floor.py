"""
Этаж 5 — Зачистка комнат (5 комнат, 2-3 монстра в каждой последовательно).

Прогресс хранится в floor_progress.extra["slots_cleared"] — стандартный
механизм combat_service. Слоты вида rc_r{room}_{monster}.

Кнопки на клавиатуре используют коды rc_r0..rc_r4 (один на комнату);
обработчик floor.py сам определяет, какого следующего монстра атаковать.
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ──────────────────────────────────────────────────────────────
ROOM_CLEAR_FLOOR = 5
TOTAL_ROOMS = 5
META_KEY = "room_clear_v1"

SLOT_BOSS = "rc_boss"

# Кнопочные коды (один на комнату — пользователь нажимает их)
ROOM_BUTTON_CODES: list[str] = [f"rc_r{i}" for i in range(TOTAL_ROOMS)]

# Группы слотов монстров внутри каждой комнаты
ROOM_GROUPS: list[list[str]] = [
    ["rc_r0_m0", "rc_r0_m1"],                   # Комната 1: 2 монстра
    ["rc_r1_m0", "rc_r1_m1", "rc_r1_m2"],       # Комната 2: 3 монстра
    ["rc_r2_m0", "rc_r2_m1"],                   # Комната 3: 2 монстра
    ["rc_r3_m0", "rc_r3_m1", "rc_r3_m2"],       # Комната 4: 3 монстра
    ["rc_r4_m0", "rc_r4_m1"],                   # Комната 5: 2 монстра
]

# Плоский список всех слотов монстров (12 всего)
SLOT_ROOMS: list[str] = [s for grp in ROOM_GROUPS for s in grp]

# Все слоты: кнопочные + монстры + босс
ROOM_CLEAR_ALL_SLOTS: frozenset[str] = frozenset(
    ROOM_BUTTON_CODES + SLOT_ROOMS + [SLOT_BOSS]
)

# ── Шаблоны монстров по комнатам ─────────────────────────────────────────────

# Комната 1 — Лесная застава (2 монстра)
_C1: list[MonsterTemplate] = [
    MonsterTemplate("rc_r0_scout",  "Лесной дозорный",  "🌿", "earth",
                    "Охраняет первые ворота заставы."),
    MonsterTemplate("rc_r0_spider", "Ядовитый паук",    "🕷️", "earth",
                    "Плетёт смертоносные сети между дубами."),
]

# Комната 2 — Волчье логово (3 монстра)
_C2: list[MonsterTemplate] = [
    MonsterTemplate("rc_r1_wolf",   "Тёмный волк",       "🐺", "dark",
                    "Рыщет в поисках добычи."),
    MonsterTemplate("rc_r1_alpha",  "Волк-вожак",        "🐺", "dark",
                    "Вожак стаи — свирепее и крупнее сородичей."),
    MonsterTemplate("rc_r1_ghost",  "Лесной призрак",    "👻", "dark",
                    "Дух погибшего охотника бродит среди деревьев."),
]

# Комната 3 — Древние руины (2 монстра)
_C3: list[MonsterTemplate] = [
    MonsterTemplate("rc_r2_spirit", "Дух леса",         "🍂", "earth",
                    "Хранитель старинных камней пробудился."),
    MonsterTemplate("rc_r2_idol",   "Каменный идол",    "🗿", "earth",
                    "Ожившая статуя не пропустит чужаков."),
]

# Комната 4 — Пещера троллей (3 монстра)
_C4: list[MonsterTemplate] = [
    MonsterTemplate("rc_r3_troll",   "Лесной тролль",    "👹", "earth",
                    "Косматый великан встречает ударом дубины."),
    MonsterTemplate("rc_r3_guard",   "Тролль-охранник",  "👹", "earth",
                    "Охраняет вход в пещеру вожака."),
    MonsterTemplate("rc_r3_shaman",  "Трольячий шаман",  "🧙", "dark",
                    "Призывает тёмную магию предков."),
]

# Комната 5 — Передпокои Стража (2 монстра)
_C5: list[MonsterTemplate] = [
    MonsterTemplate("rc_r4_gatekeeper", "Страж Врат",     "🛡️", "earth",
                    "Последний защитник перед самим Стражем Прохода."),
    MonsterTemplate("rc_r4_knight",     "Лесной рыцарь",  "⚔️", "earth",
                    "Закованный в кору рыцарь — верный слуга Стража."),
]

# Шаблоны, сгруппированные по комнатам
_ROOM_TEMPLATES: list[list[MonsterTemplate]] = [_C1, _C2, _C3, _C4, _C5]

# Шаблон босса (без изменений)
_TMPL_BOSS = MonsterTemplate(
    "boss_forest_warden",
    "Страж Прохода",
    "🌳",
    "earth",
    "Вековой Страж Прохода закрыл ворота башни своим телом.",
)

# ── Объекты FloorMonsterSpawn ───────────────────────────────────────────────

# Все спауны монстров: ROOM_GROUPS[room][monster_idx]
_ROOM_SPAWNS: list[list[FloorMonsterSpawn]] = []
for _room_idx, (_slots, _tmpls) in enumerate(zip(ROOM_GROUPS, _ROOM_TEMPLATES)):
    _room_spawns: list[FloorMonsterSpawn] = []
    for _m_idx, (_slot, _tmpl) in enumerate(zip(_slots, _tmpls)):
        # Последний монстр в комнате — элита; остальные — рядовые
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


def is_room_clear_floor(floor_number: int) -> bool:
    return int(floor_number) == ROOM_CLEAR_FLOOR


def room_index_for_button(button_code: str) -> int | None:
    """Возвращает индекс комнаты (0-4) для кода кнопки rc_r0..rc_r4, иначе None."""
    if button_code in ROOM_BUTTON_CODES:
        try:
            return int(button_code.replace("rc_r", ""))
        except ValueError:
            pass
    return None


def next_slot_in_room(room_idx: int, beaten: frozenset[str]) -> str | None:
    """Возвращает слот следующего незачищенного монстра в комнате, или None если вся комната пройдена."""
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
    """Все комнаты зачищены → доступен Страж Прохода."""
    return all(is_room_complete(i, defeated_slots) for i in range(TOTAL_ROOMS))


def ensure_started(character: Character) -> None:
    if int(character.floor_number) != ROOM_CLEAR_FLOOR:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_room_clear_banner_html(defeated_slots: frozenset[str]) -> str:
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return "🌳 <b>Сценарий завершён!</b> Страж Прохода пал — ворота открыты."

    cleared_rooms = rooms_cleared_count(defeated_slots)
    total_mon = total_monsters_cleared(defeated_slots)
    total_slots = len(SLOT_ROOMS)

    hint = " → <b>открылся Страж!</b>" if cleared_rooms == TOTAL_ROOMS else ""
    room_bar = "🟩" * cleared_rooms + "⬜" * (TOTAL_ROOMS - cleared_rooms)
    return (
        f"🗺️ <b>Зачистка комнат</b> [{room_bar}] {cleared_rooms}/{TOTAL_ROOMS} комнат{hint}\n"
        f"Монстров: {total_mon}/{total_slots} "
        f"<i>(в каждой комнате 2-3 последовательных боя)</i>"
    )
