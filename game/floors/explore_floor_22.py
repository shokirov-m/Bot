"""
Этаж 22 — Механика «Исследование Пещеры Теней».

Аналог этажа 8/4, но с монстрами зоны shadow_caves (Пещеры Теней).

Игрок нажимает «🕯️ Исследовать» 20-30 раз, чтобы достичь 100%.
При каждой попытке случайное событие:
  58% — бой с монстром       (slot_code = "e22_encounter")
  10% — тайник с золотом
   8% — светящийся кристалл  (восстанавливает MP)
   7% — ловушка              (урон + золото в обломках)
   6% — мистическое событие
   6% — древняя надпись
   5% — редкий предмет

При 100% открывается кнопка «Ткач Теней» (МИНИ-БОСС / финальный босс).
Победа над боссом открывает путь на этаж 23.

Прогресс хранится в floor_progress.extra:
  "e22_count":      int   — число пройденных попыток
  "e22_target":     int   — цель (20-30)
  "e22_boss_avail": bool  — достигнуто 100%
"""

from __future__ import annotations

import random

from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

# ── Константы ─────────────────────────────────────────────────────────────────
EXPLORE_FLOOR_22 = 22
DEFAULT_TARGET_MIN = 20
DEFAULT_TARGET_MAX = 30
META_KEY = "explore_floor_22_v1"

SLOT_BOSS = "e22_boss"
SLOT_ENCOUNTER = "e22_encounter"

EXPLORE_22_ALL_SLOTS: frozenset[str] = frozenset({SLOT_BOSS, SLOT_ENCOUNTER})

# Вероятности событий (cave-specific)
_EVENT_TYPES = (
    "monster",
    "gold",
    "crystal",       # светящийся кристалл → MP
    "trap",
    "mystical",
    "ancient_inscription",
    "rare_item",
)
_EVENT_WEIGHTS = (0.58, 0.10, 0.08, 0.07, 0.06, 0.06, 0.05)

# ── Шаблоны монстров (зона shadow_caves) ──────────────────────────────────────
_MONSTER_TEMPLATES: list[MonsterTemplate] = [
    MonsterTemplate("sh_bat_swarm",   "Рой летучих",      "🦇", "dark",  "Стремительная стая из глубин пещеры."),
    MonsterTemplate("sh_shade",       "Теневой дух",      "🌑", "dark",  "Бестелесное существо, питающееся страхом."),
    MonsterTemplate("sh_crawler",     "Пещерный ползун",  "🪨", "earth", "Медленный, но смертоносный хищник трещин."),
    MonsterTemplate("sh_wisp",        "Огонёк-обман",     "🔥", "fire",  "Манит путников в тёмные провалы."),
    MonsterTemplate("sh_echo_ghost",  "Эхо-призрак",      "👻", "dark",  "Отражение погибшего путника в пещерах."),
    MonsterTemplate("sh_stalactite",  "Живой сталактит",  "🪨", "earth", "Каменная тварь, висящая под сводами."),
    MonsterTemplate("sh_gloom_weaver","Ткач мрака",       "🕸️", "dark",  "Плетёт ловушки из темноты."),
]

_TMPL_BOSS = MonsterTemplate(
    "e22_shadow_weaver_boss",
    "Ткач Теней",
    "🕸️",
    "dark",
    "Великий паук-демон, соткавший всю тьму этих пещер. "
    "Его нити поглощают свет и надежду.",
)

SPAWN_BOSS = FloorMonsterSpawn(
    slot_code=SLOT_BOSS,
    template=_TMPL_BOSS,
    is_elite=False,
    is_mini_boss=False,
    is_major_boss=True,
)


# ── Вспомогательные функции ────────────────────────────────────────────────────

def is_explore_floor_22(floor_number: int) -> bool:
    return int(floor_number) == EXPLORE_FLOOR_22


def get_explore_count(extra: dict) -> int:
    c = extra.get("e22_count", 0)
    return int(c) if isinstance(c, (int, float)) else 0


def get_explore_target(extra: dict) -> int:
    t = extra.get("e22_target")
    if isinstance(t, int) and DEFAULT_TARGET_MIN <= t <= DEFAULT_TARGET_MAX:
        return t
    return DEFAULT_TARGET_MIN


def is_boss_available(extra: dict) -> bool:
    return bool(extra.get("e22_boss_avail", False))


def ensure_explore_started(extra: dict) -> dict:
    """Инициализирует параметры исследования при первом запуске."""
    extra = dict(extra)
    if "e22_target" not in extra:
        extra["e22_target"] = random.randint(DEFAULT_TARGET_MIN, DEFAULT_TARGET_MAX)
    if "e22_count" not in extra:
        extra["e22_count"] = 0
    if "e22_boss_avail" not in extra:
        extra["e22_boss_avail"] = False
    return extra


def roll_explore_event() -> str:
    """Бросает кубик и возвращает тип события."""
    return random.choices(_EVENT_TYPES, weights=_EVENT_WEIGHTS, k=1)[0]


def make_encounter_spawn() -> FloorMonsterSpawn:
    """Создаёт спаун для случайного боя-исследования (20% шанс элиты)."""
    tmpl = random.choice(_MONSTER_TEMPLATES)
    is_elite = random.random() < 0.20
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
    extra["e22_count"] = count
    if count >= target and not extra.get("e22_boss_avail"):
        extra["e22_boss_avail"] = True
    return extra


def reset_explore_state(extra: dict) -> dict:
    """Сброс прогресса исследования (при переходе этажа)."""
    extra = dict(extra)
    extra.pop("e22_count", None)
    extra.pop("e22_target", None)
    extra.pop("e22_boss_avail", None)
    return extra


def format_explore_banner_html(extra: dict) -> str:
    """Баннер прогресса исследования для экрана этажа."""
    slots_cleared = list(extra.get("slots_cleared") or [])
    boss_done = SLOT_BOSS in slots_cleared

    if boss_done:
        return "🕸️ <b>Пещера исследована!</b> Ткач Теней повержен — путь на 23-й этаж открыт."

    count = get_explore_count(extra)
    target = get_explore_target(extra)
    pct = progress_percent(count, target)

    bar_filled = pct // 10
    bar_empty = 10 - bar_filled
    bar = "🟣" * bar_filled + "⬜" * bar_empty

    boss_hint = " → <b>Ткач Теней пробудился!</b>" if is_boss_available(extra) else ""

    return (
        f"🕯️ <b>Исследование пещеры</b> [{bar}] {pct}%{boss_hint}\n"
        f"Попыток: {count}/{target}"
    )
