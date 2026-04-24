"""
Этаж 4 — Механика «Исследование Леса».

Аналог этажа 8, но с монстрами Леса Начал (зона forest_beginnings).

Игрок нажимает «🔍 Исследовать» 15-20 раз, чтобы достичь 100%.
При каждой попытке случайное событие:
  60% — бой с монстром  (slot_code = "e4_encounter")
  11% — тайник с золотом
   7% — NPC-торговец
   7% — мистическое событие
   7% — ловушка
   5% — древняя надпись
   3% — редкий предмет

При 100% открывается кнопка «Хранитель Рощи» (БОСС).
Победа над боссом открывает путь на этаж 5.

Прогресс хранится в floor_progress.extra:
  "e4_count":     int   — число пройденных попыток
  "e4_target":    int   — цель (15-20)
  "e4_boss_avail": bool — достигнуто 100%
"""

from __future__ import annotations

import random

from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ─────────────────────────────────────────────────────────────────
EXPLORE_FLOOR_4 = 4
DEFAULT_TARGET_MIN = 15
DEFAULT_TARGET_MAX = 20
META_KEY = "explore_floor_4_v1"

SLOT_BOSS = "e4_boss"
SLOT_ENCOUNTER = "e4_encounter"

EXPLORE_4_ALL_SLOTS: frozenset[str] = frozenset({SLOT_BOSS, SLOT_ENCOUNTER})

# Вероятности событий (те же типы что и у этажа 8)
_EVENT_TYPES = ("monster", "gold", "merchant", "mystical", "rare_item", "trap", "ancient_inscription")
_EVENT_WEIGHTS = (0.60, 0.11, 0.07, 0.07, 0.03, 0.07, 0.05)

# ── Шаблоны монстров (лесная зона) ────────────────────────────────────────────
_MONSTER_TEMPLATES: list[MonsterTemplate] = [
    MonsterTemplate("orc",    "Лесной орк",        "👹", "earth", "Громила из засады на лесной тропе."),
    MonsterTemplate("spider", "Паук-ткач",          "🕷️", "earth", "Плетёт тенёта между высоких дубов."),
    MonsterTemplate("goblin", "Гоблин",             "👺", "earth", "Шустрый мародёр из лесного лагеря."),
    MonsterTemplate("boar",   "Кабан",              "🐗", "earth", "Разъярённый зверь мчится напролом."),
    MonsterTemplate("sprite", "Лесной спрайт",     "✨", "earth", "Озорное существо из чащи."),
    MonsterTemplate("bandit", "Лесной разбойник",  "🗡️", "dark",  "Скрывается в тени деревьев."),
    MonsterTemplate("ent",    "Энт",               "🌵", "earth", "Живое дерево стережёт заросли."),
]

_TMPL_BOSS = MonsterTemplate(
    "e4_forest_warden",
    "Хранитель Рощи",
    "🌳",
    "earth",
    "Древний дух леса пробудился, почуяв чужака. Его гнев — это сама природа.",
)

SPAWN_BOSS = FloorMonsterSpawn(
    slot_code=SLOT_BOSS,
    template=_TMPL_BOSS,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=True,
)


# ── Вспомогательные функции ────────────────────────────────────────────────────

def is_explore_floor_4(floor_number: int) -> bool:
    return int(floor_number) == EXPLORE_FLOOR_4


def get_explore_count(extra: dict) -> int:
    c = extra.get("e4_count", 0)
    return int(c) if isinstance(c, (int, float)) else 0


def get_explore_target(extra: dict) -> int:
    t = extra.get("e4_target")
    if isinstance(t, int) and DEFAULT_TARGET_MIN <= t <= DEFAULT_TARGET_MAX:
        return t
    return DEFAULT_TARGET_MIN


def is_boss_available(extra: dict) -> bool:
    return bool(extra.get("e4_boss_avail", False))


def ensure_explore_started(extra: dict) -> dict:
    """Инициализирует параметры исследования при первом запуске."""
    extra = dict(extra)
    if "e4_target" not in extra:
        extra["e4_target"] = random.randint(DEFAULT_TARGET_MIN, DEFAULT_TARGET_MAX)
    if "e4_count" not in extra:
        extra["e4_count"] = 0
    if "e4_boss_avail" not in extra:
        extra["e4_boss_avail"] = False
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
    """Инкрементирует счётчик, при необходимости разблокирует босса."""
    extra = dict(extra)
    count = get_explore_count(extra) + 1
    target = get_explore_target(extra)
    extra["e4_count"] = count
    if count >= target and not extra.get("e4_boss_avail"):
        extra["e4_boss_avail"] = True
    return extra


def reset_explore_state(extra: dict) -> dict:
    """Сброс прогресса исследования (при переходе этажа)."""
    extra = dict(extra)
    extra.pop("e4_count", None)
    extra.pop("e4_target", None)
    extra.pop("e4_boss_avail", None)
    return extra


def format_explore_banner_html(extra: dict) -> str:
    """Баннер прогресса исследования для экрана этажа."""
    slots_cleared = list(extra.get("slots_cleared") or [])
    boss_done = SLOT_BOSS in slots_cleared

    if boss_done:
        return "🌳 <b>Лес исследован!</b> Хранитель Рощи повержен — путь на 5-й этаж открыт."

    count = get_explore_count(extra)
    target = get_explore_target(extra)
    pct = progress_percent(count, target)

    bar_filled = pct // 10
    bar_empty = 10 - bar_filled
    bar = "🟩" * bar_filled + "⬜" * bar_empty

    boss_hint = " → <b>Хранитель пробудился!</b>" if is_boss_available(extra) else ""

    return (
        f"🔍 <b>Исследование леса</b> [{bar}] {pct}%{boss_hint}\n"
        f"Попыток: {count}/{target}"
    )
