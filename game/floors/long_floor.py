"""
Пилотный «длинный» этаж: один сценарий на этаже 15 без смены floor_number до победы над боссом.

meta_progress["long_floor_v1"] = {
    "floor": 15,
    "phase": "keys" | "wave1" | "wave2" | "npc" | "boss",
    "completed": bool,
}
"""

from __future__ import annotations

from typing import Any

from db.models.character import Character
from game.floors.monsters import FloorMonsterSpawn, MonsterTemplate

PILOT_FLOOR = 15
META_KEY = "long_floor_v1"

SLOT_W1 = "lf_w1"
SLOT_W2 = "lf_w2"
SLOT_BOSS = "lf_boss"
LONG_FLOOR_SLOTS = frozenset({SLOT_W1, SLOT_W2, SLOT_BOSS})

_TMPL_W1 = MonsterTemplate(
    "lf_swarm",
    "Болотная стая",
    "🐸",
    "dark",
    "Шипастые твари выползают из тумана.",
)
_TMPL_W2 = MonsterTemplate(
    "lf_guardian",
    "Страж ключа",
    "🔑",
    "earth",
    "Каменный идол сияет проклятым светом.",
)
_TMPL_BOSS = MonsterTemplate(
    "lf_bog_lord",
    "Владыка топи",
    "👑",
    "dark",
    "Три ключа в зубах — три печати на выходе.",
)

SPAWN_W1 = FloorMonsterSpawn(
    slot_code=SLOT_W1,
    template=_TMPL_W1,
    is_elite=True,
    is_mini_boss=False,
    is_major_boss=False,
)
SPAWN_W2 = FloorMonsterSpawn(
    slot_code=SLOT_W2,
    template=_TMPL_W2,
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


def all_long_floor_spawns() -> list[FloorMonsterSpawn]:
    return [SPAWN_W1, SPAWN_W2, SPAWN_BOSS]


def spawn_by_slot(slot: str) -> FloorMonsterSpawn | None:
    for s in all_long_floor_spawns():
        if s.slot_code == slot:
            return s
    return None


def _lf_meta(character: Character) -> dict[str, Any] | None:
    raw = character.meta_progress or {}
    lf = raw.get(META_KEY)
    return lf if isinstance(lf, dict) else None


def is_long_floor_scenario_active(character: Character) -> bool:
    """Сценарий длинного этажа ещё актуален (клавиатура фаз / учёт слотов lf_*)."""
    if int(character.floor_number) != PILOT_FLOOR:
        return False
    lf = _lf_meta(character)
    if lf is None:
        return True
    return not bool(lf.get("completed"))


def is_long_floor_active(character: Character) -> bool:
    """Алиас: отдельный UI вместо обычного списка целей."""
    return is_long_floor_scenario_active(character)


def ensure_long_floor_started(character: Character) -> None:
    if int(character.floor_number) != PILOT_FLOOR:
        return
    meta = dict(character.meta_progress or {})
    lf = meta.get(META_KEY)
    if not isinstance(lf, dict):
        meta[META_KEY] = {
            "floor": PILOT_FLOOR,
            "phase": "keys",
            "completed": False,
        }
        character.meta_progress = meta
        return
    if "phase" not in lf:
        lf = dict(lf)
        lf.setdefault("floor", PILOT_FLOOR)
        lf["phase"] = "keys"
        lf.setdefault("completed", False)
        meta[META_KEY] = lf
        character.meta_progress = meta


def current_phase(character: Character) -> str:
    lf = _lf_meta(character)
    if lf is None:
        return "keys"
    p = str(lf.get("phase") or "keys")
    if p in ("keys", "wave1", "wave2", "npc", "boss"):
        return p
    return "keys"


def mark_completed(character: Character) -> None:
    meta = dict(character.meta_progress or {})
    lf = dict(meta.get(META_KEY) or {})
    lf["completed"] = True
    lf["phase"] = "boss"
    meta[META_KEY] = lf
    character.meta_progress = meta


def advance_from_keys(character: Character) -> None:
    meta = dict(character.meta_progress or {})
    lf = dict(meta.get(META_KEY) or {})
    lf["phase"] = "wave1"
    lf.setdefault("floor", PILOT_FLOOR)
    lf.setdefault("completed", False)
    meta[META_KEY] = lf
    character.meta_progress = meta


def advance_from_npc(character: Character) -> None:
    meta = dict(character.meta_progress or {})
    lf = dict(meta.get(META_KEY) or {})
    lf["phase"] = "boss"
    meta[META_KEY] = lf
    character.meta_progress = meta


def advance_phase_after_wave(character: Character, slot: str) -> None:
    meta = dict(character.meta_progress or {})
    lf = dict(meta.get(META_KEY) or {})
    if slot == SLOT_W1:
        lf["phase"] = "wave2"
    elif slot == SLOT_W2:
        lf["phase"] = "npc"
    meta[META_KEY] = lf
    character.meta_progress = meta


def spawns_for_tower_progress(character: Character, floor_number: int) -> list[FloorMonsterSpawn]:
    """Слоты для учёта «все цели этажа» — на особых этажах возвращает слоты сценария."""
    from game.floors.monsters import build_spawns_for_floor

    if floor_number == PILOT_FLOOR and is_long_floor_scenario_active(character):
        return all_long_floor_spawns()

    # Этаж 5 — зачистка комнат
    from game.floors import room_clear_floor as rc_mod
    if rc_mod.is_room_clear_floor(floor_number):
        return rc_mod.all_room_clear_spawns()

    # Этаж 10 — волны вторжения
    from game.floors import wave_floor as wv_mod
    if wv_mod.is_wave_floor(floor_number):
        return wv_mod.all_wave_floor_spawns()

    return build_spawns_for_floor(floor_number)


def format_long_floor_banner_html() -> str:
    return (
        "🗺️ <b>Особый этаж — длинный сценарий</b>\n"
        "Три печати в зале: две волны стражей, затем владыка топи. "
        "Пока сценарий не завершён, обычные цели этажа скрыты."
    )
