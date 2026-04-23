"""
Этаж 8 — Механика «Исследование».

Игрок нажимает «🔍 Исследовать» 30-35 раз, чтобы достичь 100%.
При каждой попытке случайное событие:
  70% — бой с монстром  (slot_code = "exp_encounter")
  12% — тайник с золотом
   8% — NPC-торговец
   7% — мистическое событие
   3% — редкий предмет

При 100% открывается кнопка «Хранитель Пещеры» (БОСС).
Победа над боссом открывает путь на этаж 9.

Прогресс хранится в floor_progress.extra:
  "explore_count":  int   — число пройденных попыток
  "explore_target": int   — цель (30-35, задаётся при первой попытке)
  "boss_available": bool  — достигнуто 100%
"""

from __future__ import annotations

import random

from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ─────────────────────────────────────────────────────────────────
EXPLORE_FLOOR = 8
DEFAULT_TARGET_MIN = 30
DEFAULT_TARGET_MAX = 35
META_KEY = "explore_floor_v1"

SLOT_BOSS = "exp_boss"
SLOT_ENCOUNTER = "exp_encounter"

EXPLORE_ALL_SLOTS: frozenset[str] = frozenset({SLOT_BOSS, SLOT_ENCOUNTER})

# Вероятности событий при исследовании
_EVENT_TYPES = ("monster", "gold", "merchant", "mystical", "rare_item")
_EVENT_WEIGHTS = (0.70, 0.12, 0.08, 0.07, 0.03)

# ── Шаблоны монстров ───────────────────────────────────────────────────────────
_MONSTER_TEMPLATES: list[MonsterTemplate] = [
    MonsterTemplate("exp_cave_bat",    "Пещерная летучая мышь",  "🦇", "dark",  "Стремительно атакует из темноты."),
    MonsterTemplate("exp_lurker",      "Притаившийся лурк",      "👁️", "dark",  "Поджидает в тёмном углу пещеры."),
    MonsterTemplate("exp_stone_crab",  "Каменный краб",           "🦀", "earth", "Прячется под каменными плитами."),
    MonsterTemplate("exp_cave_spider", "Пещерный паук",           "🕷️", "earth", "Плетёт ловушки в расселинах."),
    MonsterTemplate("exp_lost_soul",   "Потерянная душа",         "💀", "dark",  "Дух погибшего исследователя бродит здесь."),
    MonsterTemplate("exp_fungal",      "Грибной страж",           "🍄", "earth", "Охраняет грибной лес пещеры."),
    MonsterTemplate("exp_golem",       "Мини-голем",              "🪨", "earth", "Ожившая каменная статуэтка."),
    MonsterTemplate("exp_shade",       "Тёмная тень",             "🌑", "dark",  "Порождение кромешной тьмы пещеры."),
]

_TMPL_BOSS = MonsterTemplate(
    "boss_cave_guardian",
    "Хранитель Пещеры",
    "🗿",
    "earth",
    "Древний страж запечатал выход из пещеры своим телом.",
)

SPAWN_BOSS = FloorMonsterSpawn(
    slot_code=SLOT_BOSS,
    template=_TMPL_BOSS,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=True,
)

# ── Вспомогательные функции ────────────────────────────────────────────────────

def is_explore_floor(floor_number: int) -> bool:
    return int(floor_number) == EXPLORE_FLOOR


def get_explore_count(extra: dict) -> int:
    c = extra.get("explore_count", 0)
    return int(c) if isinstance(c, (int, float)) else 0


def get_explore_target(extra: dict) -> int:
    t = extra.get("explore_target")
    if isinstance(t, int) and DEFAULT_TARGET_MIN <= t <= DEFAULT_TARGET_MAX:
        return t
    return DEFAULT_TARGET_MIN


def is_boss_available(extra: dict) -> bool:
    return bool(extra.get("boss_available", False))


def ensure_explore_started(extra: dict) -> dict:
    """Инициализирует explore_target при первом запуске; возвращает обновлённый extra."""
    extra = dict(extra)
    if "explore_target" not in extra:
        extra["explore_target"] = random.randint(DEFAULT_TARGET_MIN, DEFAULT_TARGET_MAX)
    if "explore_count" not in extra:
        extra["explore_count"] = 0
    if "boss_available" not in extra:
        extra["boss_available"] = False
    return extra


def roll_explore_event() -> str:
    """Бросает кубик и возвращает тип события."""
    return random.choices(_EVENT_TYPES, weights=_EVENT_WEIGHTS, k=1)[0]


def make_encounter_spawn() -> FloorMonsterSpawn:
    """Создаёт спаун для случайного боя-исследования (15% шанс элиты)."""
    tmpl = random.choice(_MONSTER_TEMPLATES)
    is_elite = random.random() < 0.15
    return FloorMonsterSpawn(
        slot_code=SLOT_ENCOUNTER,
        template=tmpl,
        is_elite=is_elite,
        is_mini_boss=False,
        is_major_boss=False,
    )


def spawn_by_slot(slot: str) -> FloorMonsterSpawn | None:
    if slot == SLOT_BOSS:
        return SPAWN_BOSS
    if slot == SLOT_ENCOUNTER:
        return make_encounter_spawn()
    return None


def progress_percent(count: int, target: int) -> int:
    if target <= 0:
        return 100
    return min(100, int(count * 100 / target))


def increment_explore_count(extra: dict) -> dict:
    """Инкрементирует счётчик, при необходимости разблокирует босса. Возвращает обновлённый extra."""
    extra = dict(extra)
    count = get_explore_count(extra) + 1
    target = get_explore_target(extra)
    extra["explore_count"] = count
    if count >= target and not extra.get("boss_available"):
        extra["boss_available"] = True
    return extra


def reset_explore_state(extra: dict) -> dict:
    """Сброс прогресса исследования (при переходе этажа)."""
    extra = dict(extra)
    extra.pop("explore_count", None)
    extra.pop("explore_target", None)
    extra.pop("boss_available", None)
    return extra


def format_explore_banner_html(extra: dict) -> str:
    """Баннер прогресса исследования для экрана этажа."""
    slots_cleared = list(extra.get("slots_cleared") or [])
    boss_done = SLOT_BOSS in slots_cleared

    if boss_done:
        return "🗿 <b>Исследование завершено!</b> Хранитель Пещеры пал — проход открыт."

    count = get_explore_count(extra)
    target = get_explore_target(extra)
    pct = progress_percent(count, target)

    bar_filled = pct // 10
    bar_empty = 10 - bar_filled
    bar = "🟦" * bar_filled + "⬜" * bar_empty

    boss_hint = " → <b>Хранитель пробудился!</b>" if is_boss_available(extra) else ""

    return (
        f"🔍 <b>Исследование пещеры</b> [{bar}] {pct}%{boss_hint}\n"
        f"Попыток: {count}/{target} "
        f"<i>(70% бой, 12% тайник, 8% торговец, 7% событие, 3% редкость)</i>"
    )
