"""Общая логика механики «исследование» для этажей 4, 8, 22."""

from __future__ import annotations

import random
from dataclasses import dataclass

from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate


@dataclass(frozen=True, slots=True)
class ExploreBanner:
    boss_done: str
    title_fmt: str
    boss_hint: str
    filled_tile: str = "🟦"
    empty_tile: str = "⬜"


@dataclass(frozen=True, slots=True)
class ExploreConfig:
    floor_number: int
    meta_key: str
    slot_boss: str
    slot_encounter: str
    count_key: str
    target_key: str
    boss_avail_key: str
    target_min: int
    target_max: int
    monster_templates: tuple[MonsterTemplate, ...]
    boss_template: MonsterTemplate
    event_types: tuple[str, ...]
    event_weights: tuple[float, ...]
    elite_chance: float
    banner: ExploreBanner
    all_slots_attr: str = "EXPLORE_ALL_SLOTS"


class ExploreMechanic:
    __slots__ = ("config", "spawn_boss", "all_slots")

    def __init__(self, config: ExploreConfig) -> None:
        self.config = config
        self.spawn_boss = FloorMonsterSpawn(
            slot_code=config.slot_boss,
            template=config.boss_template,
            is_elite=False,
            is_mini_boss=False,
            is_major_boss=True,
        )
        self.all_slots = frozenset({config.slot_boss, config.slot_encounter})

    @property
    def floor_number(self) -> int:
        return self.config.floor_number

    def is_floor(self, floor_number: int) -> bool:
        return int(floor_number) == self.config.floor_number

    def get_explore_count(self, extra: dict) -> int:
        c = extra.get(self.config.count_key, 0)
        return int(c) if isinstance(c, (int, float)) else 0

    def get_explore_target(self, extra: dict) -> int:
        t = extra.get(self.config.target_key)
        if isinstance(t, int) and self.config.target_min <= t <= self.config.target_max:
            return t
        return self.config.target_min

    def is_boss_available(self, extra: dict) -> bool:
        return bool(extra.get(self.config.boss_avail_key, False))

    def ensure_explore_started(self, extra: dict) -> dict:
        extra = dict(extra)
        if self.config.target_key not in extra:
            extra[self.config.target_key] = random.randint(
                self.config.target_min, self.config.target_max
            )
        if self.config.count_key not in extra:
            extra[self.config.count_key] = 0
        if self.config.boss_avail_key not in extra:
            extra[self.config.boss_avail_key] = False
        return extra

    def roll_explore_event(self) -> str:
        return random.choices(
            list(self.config.event_types),
            weights=list(self.config.event_weights),
            k=1,
        )[0]

    def make_encounter_spawn(self) -> FloorMonsterSpawn:
        tmpl = random.choice(self.config.monster_templates)
        is_elite = random.random() < self.config.elite_chance
        return FloorMonsterSpawn(
            slot_code=self.config.slot_encounter,
            template=tmpl,
            is_elite=is_elite,
            is_mini_boss=False,
            is_major_boss=False,
        )

    def spawn_by_slot(self, slot: str) -> FloorMonsterSpawn | None:
        if slot == self.config.slot_boss:
            return self.spawn_boss
        if slot == self.config.slot_encounter:
            return self.make_encounter_spawn()
        return None

    @staticmethod
    def progress_percent(count: int, target: int) -> int:
        if target <= 0:
            return 100
        return min(100, int(count * 100 / target))

    def increment_explore_count(self, extra: dict) -> dict:
        extra = dict(extra)
        count = self.get_explore_count(extra) + 1
        target = self.get_explore_target(extra)
        extra[self.config.count_key] = count
        if count >= target and not extra.get(self.config.boss_avail_key):
            extra[self.config.boss_avail_key] = True
        return extra

    def reset_explore_state(self, extra: dict) -> dict:
        extra = dict(extra)
        extra.pop(self.config.count_key, None)
        extra.pop(self.config.target_key, None)
        extra.pop(self.config.boss_avail_key, None)
        return extra

    def format_explore_banner_html(self, extra: dict) -> str:
        slots_cleared = list(extra.get("slots_cleared") or [])
        if self.config.slot_boss in slots_cleared:
            return self.config.banner.boss_done

        count = self.get_explore_count(extra)
        target = self.get_explore_target(extra)
        pct = self.progress_percent(count, target)
        b = self.config.banner
        bar_filled = pct // 10
        bar_empty = 10 - bar_filled
        bar = b.filled_tile * bar_filled + b.empty_tile * bar_empty
        boss_hint = b.boss_hint if self.is_boss_available(extra) else ""
        return b.title_fmt.format(bar=bar, pct=pct, boss_hint=boss_hint, count=count, target=target)


def expose_legacy_module(
    mech: ExploreMechanic,
    *,
    is_floor_name: str,
    floor_const_name: str,
    all_slots_name: str,
) -> dict[str, object]:
    cfg = mech.config
    fn = mech.floor_number
    return {
        floor_const_name: fn,
        f"EXPLORE_FLOOR_{fn}": fn,
        "DEFAULT_TARGET_MIN": cfg.target_min,
        "DEFAULT_TARGET_MAX": cfg.target_max,
        "META_KEY": cfg.meta_key,
        "SLOT_BOSS": cfg.slot_boss,
        "SLOT_ENCOUNTER": cfg.slot_encounter,
        all_slots_name: mech.all_slots,
        "SPAWN_BOSS": mech.spawn_boss,
        is_floor_name: mech.is_floor,
        "get_explore_count": mech.get_explore_count,
        "get_explore_target": mech.get_explore_target,
        "is_boss_available": mech.is_boss_available,
        "ensure_explore_started": mech.ensure_explore_started,
        "roll_explore_event": mech.roll_explore_event,
        "make_encounter_spawn": mech.make_encounter_spawn,
        "spawn_by_slot": mech.spawn_by_slot,
        "progress_percent": ExploreMechanic.progress_percent,
        "increment_explore_count": mech.increment_explore_count,
        "reset_explore_state": mech.reset_explore_state,
        "format_explore_banner_html": mech.format_explore_banner_html,
    }
