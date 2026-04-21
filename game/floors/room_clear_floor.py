"""
Этаж 5 — Зачистка комнат (Вариант 1).

Игрок зачищает 5 комнат последовательно; после этого открывается
комната Стража Прохода (финальный босс этажа-сценария).
Победа над Стражем → set_tower_ascent_pending(6).

Прогресс хранится в floor_progress.extra["slots_cleared"] — стандартный
механизм combat_service, никаких дополнительных столбцов не нужно.

meta_progress["room_clear_v1"] = {"started": True}  — только флаг «баннер показан».
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ──────────────────────────────────────────────────────────────
ROOM_CLEAR_FLOOR = 5
TOTAL_ROOMS = 5

META_KEY = "room_clear_v1"

SLOT_ROOMS: list[str] = [f"rc_r{i}" for i in range(TOTAL_ROOMS)]
SLOT_BOSS = "rc_boss"
ROOM_CLEAR_ALL_SLOTS: frozenset[str] = frozenset(SLOT_ROOMS + [SLOT_BOSS])

# ── Шаблоны монстров в комнатах ─────────────────────────────────────────────
_ROOM_TEMPLATES: list[MonsterTemplate] = [
    MonsterTemplate("rc_scout_1",  "Лесной дозорный",  "🌿", "earth", "Страж зарослей охраняет этот проход."),
    MonsterTemplate("rc_scout_2",  "Ядовитый паук",    "🕷️", "earth", "Плетёт сети между вековыми дубами."),
    MonsterTemplate("rc_scout_3",  "Тёмный волк",      "🐺", "dark",  "Вожак лесной стаи выходит на охоту."),
    MonsterTemplate("rc_scout_4",  "Дух леса",         "🍂", "earth", "Древний дух охраняет потайную тропу."),
    MonsterTemplate("rc_scout_5",  "Лесной тролль",    "👹", "earth", "Косматый великан бьёт кулаком по земле."),
]

_TMPL_BOSS = MonsterTemplate(
    "boss_forest_warden",
    "Страж Прохода",
    "🌳",
    "earth",
    "Вековой Страж Прохода закрыл ворота башни своим телом.",
)

# ── Объекты FloorMonsterSpawn ───────────────────────────────────────────────
SPAWN_ROOMS: list[FloorMonsterSpawn] = [
    FloorMonsterSpawn(
        slot_code=SLOT_ROOMS[i],
        template=_ROOM_TEMPLATES[i],
        is_elite=True,
        is_mini_boss=False,
        is_major_boss=False,
    )
    for i in range(TOTAL_ROOMS)
]

SPAWN_BOSS = FloorMonsterSpawn(
    slot_code=SLOT_BOSS,
    template=_TMPL_BOSS,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=True,
)


# ── Публичные функции ───────────────────────────────────────────────────────

def all_room_clear_spawns() -> list[FloorMonsterSpawn]:
    """Все спавны сценария (5 комнат + босс) — для tower_progress."""
    return list(SPAWN_ROOMS) + [SPAWN_BOSS]


def spawn_by_slot(slot: str) -> FloorMonsterSpawn | None:
    for s in all_room_clear_spawns():
        if s.slot_code == slot:
            return s
    return None


def is_room_clear_floor(floor_number: int) -> bool:
    return int(floor_number) == ROOM_CLEAR_FLOOR


def rooms_cleared_count(defeated_slots: frozenset[str]) -> int:
    return sum(1 for s in SLOT_ROOMS if s in defeated_slots)


def is_boss_unlocked(defeated_slots: frozenset[str]) -> bool:
    """Все 5 комнат зачищены → доступна финальная комната со Стражем."""
    return all(s in defeated_slots for s in SLOT_ROOMS)


def ensure_started(character: Character) -> None:
    """Помечаем в meta_progress что сценарий запущен (только для баннера)."""
    if int(character.floor_number) != ROOM_CLEAR_FLOOR:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_room_clear_banner_html(defeated_slots: frozenset[str]) -> str:
    cleared = rooms_cleared_count(defeated_slots)
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return "🌳 <b>Сценарий завершён!</b> Страж Прохода пал — ворота открыты."
    bar = "🟩" * cleared + "⬜" * (TOTAL_ROOMS - cleared)
    hint = " → <b>открылся Страж!</b>" if cleared == TOTAL_ROOMS else ""
    return (
        f"🗺️ <b>Зачистка комнат</b> [{bar}] {cleared}/{TOTAL_ROOMS}{hint}\n"
        "<i>Зачисти все 5 комнат — появится финальный Страж Прохода.</i>"
    )
