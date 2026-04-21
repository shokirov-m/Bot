"""
Этаж 10 — Оборона от волн (Вариант 3).

Три последовательные волны врагов; после всех трёх пробуждается
финальный босс «Древний Трент».

Правило последовательности:
  волна1 → волна2 → волна3 → босс

Прогресс хранится в floor_progress.extra["slots_cleared"].
meta_progress["wave_floor_v1"] = {"started": True}  — флаг для баннера.
"""

from __future__ import annotations

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ──────────────────────────────────────────────────────────────
WAVE_FLOOR = 10
TOTAL_WAVES = 3

META_KEY = "wave_floor_v1"

SLOT_WAVE_1 = "wv_w1"
SLOT_WAVE_2 = "wv_w2"
SLOT_WAVE_3 = "wv_w3"
SLOT_BOSS   = "wv_boss"

WAVE_SLOTS: list[str]         = [SLOT_WAVE_1, SLOT_WAVE_2, SLOT_WAVE_3]
WAVE_FLOOR_ALL_SLOTS: frozenset[str] = frozenset(WAVE_SLOTS + [SLOT_BOSS])

# ── Шаблоны монстров ────────────────────────────────────────────────────────
_TMPL_W1 = MonsterTemplate(
    "wv_vanguard",
    "Авангард орды",
    "⚔️",
    "dark",
    "Первая волна — стремительные разведчики тёмной орды.",
)
_TMPL_W2 = MonsterTemplate(
    "wv_berserker",
    "Берсерки орды",
    "🗡️",
    "dark",
    "Вторая волна — яростные воины в закопчённых доспехах.",
)
_TMPL_W3 = MonsterTemplate(
    "wv_warlock",
    "Чернокнижник орды",
    "💀",
    "dark",
    "Третья волна — колдун, усилившийся кровью павших.",
)
_TMPL_BOSS = MonsterTemplate(
    "boss_ancient_treant_wv",
    "Древний Трент",
    "🌲",
    "earth",
    "Три волны орды разбудили вековое дерево — оно жаждет мести.",
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

def all_wave_floor_spawns() -> list[FloorMonsterSpawn]:
    """Все спавны сценария (3 волны + босс) — для tower_progress."""
    return [SPAWN_W1, SPAWN_W2, SPAWN_W3, SPAWN_BOSS]


def spawn_by_slot(slot: str) -> FloorMonsterSpawn | None:
    for s in all_wave_floor_spawns():
        if s.slot_code == slot:
            return s
    return None


def is_wave_floor(floor_number: int) -> bool:
    return int(floor_number) == WAVE_FLOOR


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
    if int(character.floor_number) != WAVE_FLOOR:
        return
    meta = dict(character.meta_progress or {})
    if not meta.get(META_KEY):
        meta[META_KEY] = {"started": True}
        character.meta_progress = meta


def format_wave_floor_banner_html(defeated_slots: frozenset[str]) -> str:
    cleared = waves_cleared_count(defeated_slots)
    boss_done = SLOT_BOSS in defeated_slots
    if boss_done:
        return "🌊 <b>Орда отбита!</b> Древний Трент повержен — путь на 11-й этаж открыт."
    if cleared == TOTAL_WAVES:
        return (
            "🌊 <b>Все волны отбиты!</b> Пробудился <b>Древний Трент</b>.\n"
            "<i>Победи его, чтобы открыть путь наверх.</i>"
        )
    bar = "🟥" * cleared + "⬜" * (TOTAL_WAVES - cleared)
    return (
        f"🌊 <b>Волна вторжения</b> [{bar}] {cleared}/{TOTAL_WAVES}\n"
        f"<i>Следующая волна уже рвётся вперёд!</i>"
    )
