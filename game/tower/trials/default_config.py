"""
Процедурные испытания 1–99: ~60% ярусов — уникальный вариант из пула зоны (псевдорандом).
Остальные — упрощённый случайный тип без повторяющегося цикла.

61–70 blood_spire — JSON пака (не трогаем).
"""

from __future__ import annotations

import random
from typing import Any

from game.tower.progression import floor_data
from game.tower.progression.floor_data import ZoneInfo
from game.tower.trials.trial_variants import (
    ALL_VARIANTS,
    VARIANTS_BY_ZONE,
    TrialVariant,
    _UNIVERSAL,
)

CORE_TRIAL_TYPES: tuple[str, ...] = ("hunt", "search", "capture", "rescue", "defense")

# Доля ярусов с «богатым» вариантом (уникальный лор)
RICH_VARIANT_PCT = 60

_GROUND_LABEL: dict[str, str] = {
    "hunt": "🎯",
    "search": "🔍",
    "rescue": "⛓️",
    "capture": "📍",
    "escort": "🛡️",
    "ritual": "🕯️",
    "defense": "🚧",
}


def is_trial_eligible_floor(floor_number: int) -> bool:
    from game.tower.mechanics import long_floor as long_floor_mod
    from game.tower.mechanics import registry as mech_registry

    n = int(floor_number)
    if n < 1 or n > floor_data.KNOWN_MAX_FLOOR:
        return False
    if floor_data.is_major_boss_floor(n):
        return True
    if mech_registry.is_scenario_floor(n):
        return False
    if n == long_floor_mod.PILOT_FLOOR:
        return False
    return True


def _rng(floor: int, zone_key: str) -> random.Random:
    seed = int(floor) * 10007 + sum(ord(c) for c in zone_key) * 31
    return random.Random(seed)


def _is_rich_floor(floor: int, zone_key: str) -> bool:
    r = _rng(floor, zone_key)
    return r.randint(1, 100) <= RICH_VARIANT_PCT


def _tier(floor: int) -> int:
    if floor <= 10:
        return 1
    if floor <= 30:
        return 2
    if floor <= 60:
        return 3
    if floor <= 80:
        return 4
    return 5


def _pool_for_zone(zone_key: str, floor: int) -> list[TrialVariant]:
    zone_pool = list(VARIANTS_BY_ZONE.get(zone_key, ()))
    uni = list(_UNIVERSAL)
    r = _rng(floor, zone_key + "_pool")
    # На ярусах ×9 чаще лагерь-оборона
    if floor % 10 == 9:
        hubs = [v for v in zone_pool + uni if v.defense_mode == "hub"]
        if hubs:
            return hubs + [v for v in zone_pool if v.defense_mode != "hub"] + uni
    mixed = zone_pool + uni
    r.shuffle(mixed)
    return mixed


def _pick_variant(floor: int, zone: ZoneInfo) -> TrialVariant:
    pool = _pool_for_zone(zone.key, floor)
    if not pool:
        pool = list(ALL_VARIANTS)
    r = _rng(floor, zone.key)
    return pool[r.randint(0, len(pool) - 1)]


def _pick_simple_random(floor: int, zone: ZoneInfo) -> TrialVariant:
    """~40%: короткий случайный тип, без фиксированного цикла."""
    r = _rng(floor, zone.key + "_simple")
    ttype = r.choice(CORE_TRIAL_TYPES)
    titles = {
        "hunt": ("Разовая охота", "Слабая стая — зачисти угодья."),
        "search": ("Быстрый поиск", "Несколько следов на ярусе."),
        "capture": ("Малый захват", "Пара узлов удержать силой."),
        "rescue": ("Малый вызов", "Небольшая группа в беде."),
        "defense": ("Короткая оборона", "Рубежи без осадного лагеря."),
    }
    title, blurb = titles[ttype]
    return TrialVariant(
        id=f"simple_{ttype}_{floor}",
        trial_type=ttype,
        title_ru=title,
        blurb_ru=blurb,
        ground_prefix=_GROUND_LABEL.get(ttype, "⚔️"),
        grounds_delta=-1 if ttype != "defense" else 0,
    )


def trial_type_label_ru(trial_type: str, cfg: dict[str, Any] | None = None) -> str:
    if cfg and cfg.get("trial_title_ru"):
        return str(cfg["trial_title_ru"])
    return {
        "hunt": "Охота",
        "search": "Поиск",
        "capture": "Захват",
        "rescue": "Спасение",
        "defense": "Оборона",
        "boss_chamber": "Залы босса",
    }.get(trial_type, trial_type)


def _scale_base(fl: int, tier: int, variant: TrialVariant) -> dict[str, Any]:
    grounds = min(18, max(4, 3 + fl // 8 + tier + variant.grounds_delta))
    if fl % 10 == 0:
        grounds = max(4, grounds - 2)
    wins = max(2, (3 if tier <= 1 else (4 if tier <= 3 else 5)) + variant.wins_delta)
    req_pct = min(94, 80 + tier * 3 + variant.required_pct_delta)
    hardcore = variant.hardcore if variant.hardcore is not None else fl >= 45
    daily_cap = max(4, 12 - tier * 2)
    stamina_cost = 1 if fl <= 25 else (2 if fl <= 55 else 3)
    death_reset = variant.death_reset or ("full_trial" if variant.trial_type == "rescue" and fl >= 55 else "phase")

    cfg: dict[str, Any] = {
        "floor": fl,
        "trial_type": variant.trial_type,
        "trial_title_ru": variant.title_ru,
        "variant_id": variant.id,
        "grounds_count": grounds,
        "wins_per_ground": wins,
        "grounds_visible_initial": min(6, max(3, grounds // 2)),
        "checkpoint_every_grounds": 3,
        "required_progress_pct": req_pct,
        "death_reset": death_reset,
        "hardcore": hardcore,
        "stamina_per_venture": stamina_cost,
        "daily_venture_cap": daily_cap,
        "generated": True,
        "hub_blurb_ru": variant.blurb_ru,
        "ground_prefix": variant.ground_prefix or _GROUND_LABEL.get(variant.trial_type, "⚔️"),
        "targets": dict(variant.targets),
    }

    fights = max(12, grounds * wins + fl * 2)
    elites = max(4, grounds + tier * 3)
    cfg["targets"].setdefault("fights", fights)
    cfg["targets"].setdefault("elites", elites)
    if fl >= 35:
        cfg["targets"].setdefault("named", max(2, 2 + (fl - 35) // 15))
    if fl % 10 == 0:
        cfg["targets"].setdefault("mini_bosses", 1)

    if variant.defense_mode == "hub":
        waves = min(16, max(8, 6 + tier * 2 + variant.waves_delta))
        perim = max(2, (3 if tier <= 2 else (4 if tier <= 4 else 5)) + variant.perim_delta)
        cfg.update(
            {
                "defense_mode": "hub",
                "grounds_count": perim,
                "grounds_visible_initial": perim,
                "waves_total": waves,
                "waves_loss_on_death": 2 if tier <= 3 else 3,
                "checkpoint_every_waves": 4,
                "wins_per_ground": max(4, wins),
                "required_progress_pct": min(94, req_pct),
            },
        )
        cfg["targets"]["waves"] = waves

    return cfg


def build_default_trial_config(
    floor_number: int,
    zone: ZoneInfo | None = None,
) -> dict[str, Any]:
    fl = int(floor_number)
    zone = zone or floor_data.get_zone_for_floor(fl)
    tier = _tier(fl)

    if _is_rich_floor(fl, zone.key):
        variant = _pick_variant(fl, zone)
    else:
        variant = _pick_simple_random(fl, zone)

    cfg = _scale_base(fl, tier, variant)
    cfg["zone_key"] = zone.key
    return cfg


def trial_type_distribution_preview() -> dict[str, list[int]]:
    from game.tower.trials.pack_config import get_trial_config

    out: dict[str, list[int]] = {}
    for fl in range(1, floor_data.KNOWN_MAX_FLOOR + 1):
        cfg = get_trial_config(fl)
        if not cfg.get("trial_type"):
            continue
        label = str(cfg.get("variant_id") or cfg.get("trial_type"))
        if cfg.get("defense_mode") == "hub":
            label = f"hub:{label}"
        out.setdefault(label, []).append(fl)
    return out

# Legacy aliases (старый код мог ссылаться)
DEFENSE_HUB_FLOORS: frozenset[int] = frozenset()


def resolve_trial_type(floor_number: int, zone: ZoneInfo) -> tuple[str, bool]:
    cfg = build_default_trial_config(floor_number, zone)
    return (
        str(cfg.get("trial_type") or "hunt"),
        str(cfg.get("defense_mode") or "") == "hub",
    )
