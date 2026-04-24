"""
Этаж 27 — Волна теней (3 волны + финальный босс).

Три последовательные волны теневых врагов; после всех трёх пробуждается
Ночной Охотник — хозяин пещер.

Правило последовательности:
  волна1 → волна2 → волна3 → босс

Прогресс хранится в floor_progress.extra["slots_cleared"].
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ──────────────────────────────────────────────────────────────
WAVE_FLOOR_27 = 27
TOTAL_WAVES = 3

META_KEY = "wave_floor_27_v1"

SLOT_WAVE_1 = "wv27_w1"
SLOT_WAVE_2 = "wv27_w2"
SLOT_WAVE_3 = "wv27_w3"
SLOT_BOSS   = "wv27_boss"

WAVE_SLOTS: list[str] = [SLOT_WAVE_1, SLOT_WAVE_2, SLOT_WAVE_3]
WAVE_FLOOR_27_ALL_SLOTS: frozenset[str] = frozenset(WAVE_SLOTS + [SLOT_BOSS])

# ── Шаблоны монстров ────────────────────────────────────────────────────────
_TMPL_W1 = MonsterTemplate(
    "wv27_shadow_scouts",
    "Теневые разведчики",
    "🌑",
    "dark",
    "Первая волна — быстрые призраки, выскальзывающие из стен.",
)
_TMPL_W2 = MonsterTemplate(
    "wv27_dark_hunters",
    "Охотники тьмы",
    "🦇",
    "dark",
    "Вторая волна — стая тёмных охотников, ведомых инстинктом крови.",
)
_TMPL_W3 = MonsterTemplate(
    "wv27_void_wraith",
    "Пустотный призрак",
    "👻",
    "dark",
    "Третья волна — существо из самой пустоты, почти неуязвимое для света.",
)
_TMPL_BOSS = MonsterTemplate(
    "boss_night_stalker_27",
    "Ночной Охотник",
    "🌑",
    "dark",
    "Повелитель теней выходит из глубин. Три волны — лишь его свита. "
    "Он сам — воплощение пещерного мрака.",
)

# ── Объекты FloorMonsterSpawn ───────────────────────────────────────────────
SPAWN_W1 = FloorMonsterSpawn(
    slot_code=SLOT_WAVE_1,
    template=_TMPL_W1,
    is_elite=True,
    is_mini_boss=False,
    is_major_boss=False,
)
SPAWN_W2 = FloorMonsterSpawn(
    slot_code=SLOT_WAVE_2,
    template=_TMPL_W2,
    is_elite=True,
    is_mini_boss=False,
    is_major_boss=False,
)
SPAWN_W3 = FloorMonsterSpawn(
    slot_code=SLOT_WAVE_3,
    template=_TMPL_W3,
    is_elite=True,
    is_mini_boss=False,
    is_major_boss=False,
)
SPAWN_BOSS = FloorMonsterSpawn(
    slot_code=SLOT_BOSS,
    template=_TMPL_BOSS,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=True,
)


# ── Публичные функции ───────────────────────────────────────────────────────

def all_wave_floor_27_spawns() -> list[FloorMonsterSpawn]:
    """Все спавны сценария (3 волны + босс) — для tower_progress."""
    return [SPAWN_W1, SPAWN_W2, SPAWN_W3, SPAWN_BOSS]


def spawn_by_slot(slot: str) -> FloorMonsterSpawn | None:
    for s in all_wave_floor_27_spawns():
        if s.slot_code == slot:
            return s
    return None


def is_wave_floor_27(floor_number: int) -> bool:
    return int(floor_number) == WAVE_FLOOR_27


def waves_cleared_count(defeated_slots: frozenset[str]) -> int:
    return sum(1 for s in WAVE_SLOTS if s in defeated_slots)


def current_available_slot(defeated_slots: frozenset[str]) -> str | None:
    """Текущий слот для боя (первая незачищенная волна, затем босс)."""
    for slot in WAVE_SLOTS:
        if slot not in defeated_slots:
            return slot
    if SLOT_BOSS not in defeated_slots:
        return SLOT_BOSS
    return None


def ensure_started(character: Character) -> None:
    """Помечаем сценарий как запущенный."""
    if int(character.floor_number) != WAVE_FLOOR_27:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_wave_floor_27_banner_html(defeated_slots: frozenset[str]) -> str:
    cleared = waves_cleared_count(defeated_slots)
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return "🌑 <b>Волны теней отбиты!</b> Ночной Охотник повержен — путь на 28-й этаж открыт."
    if cleared == TOTAL_WAVES:
        return (
            "🌑 <b>Все волны отбиты!</b> Из глубин появился <b>Ночной Охотник</b>.\n"
            "<i>Победи его, чтобы открыть путь наверх.</i>"
        )
    bar = "🟣" * cleared + "⬜" * (TOTAL_WAVES - cleared)
    return (
        f"🌑 <b>Волна теней</b> [{bar}] {cleared}/{TOTAL_WAVES}\n"
        f"<i>Следующая волна выходит из темноты!</i>"
    )
