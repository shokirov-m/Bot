"""Общая логика механики «волны» для этажей 10, 27."""

from __future__ import annotations

from dataclasses import dataclass

from db.models.character import Character
from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate


@dataclass(frozen=True, slots=True)
class WaveBanner:
    boss_done: str
    all_waves_done: str
    title_fmt: str
    next_hint: str
    filled_tile: str = "🟥"
    empty_tile: str = "⬜"


@dataclass(frozen=True, slots=True)
class WaveConfig:
    floor_number: int
    meta_key: str
    wave_slots: tuple[str, str, str]
    slot_boss: str
    wave_templates: tuple[MonsterTemplate, MonsterTemplate, MonsterTemplate]
    boss_template: MonsterTemplate
    banner: WaveBanner
    all_slots_attr: str
    all_spawns_attr: str
    format_banner_attr: str


class WaveMechanic:
    __slots__ = (
        "config",
        "total_waves",
        "wave_slots",
        "spawns",
        "spawn_boss",
        "all_slots",
    )

    def __init__(self, config: WaveConfig) -> None:
        self.config = config
        self.total_waves = len(config.wave_slots)
        self.wave_slots = list(config.wave_slots)
        self.spawns = [
            FloorMonsterSpawn(
                slot_code=slot,
                template=tmpl,
                is_elite=True,
                is_mini_boss=False,
                is_major_boss=False,
            )
            for slot, tmpl in zip(config.wave_slots, config.wave_templates)
        ]
        self.spawn_boss = FloorMonsterSpawn(
            slot_code=config.slot_boss,
            template=config.boss_template,
            is_elite=False,
            is_mini_boss=False,
            is_major_boss=True,
        )
        self.all_slots = frozenset(self.wave_slots + [config.slot_boss])

    @property
    def floor_number(self) -> int:
        return self.config.floor_number

    @property
    def meta_key(self) -> str:
        return self.config.meta_key

    @property
    def slot_boss(self) -> str:
        return self.config.slot_boss

    @property
    def SLOT_WAVE_1(self) -> str:
        return self.config.wave_slots[0]

    @property
    def SLOT_WAVE_2(self) -> str:
        return self.config.wave_slots[1]

    @property
    def SLOT_WAVE_3(self) -> str:
        return self.config.wave_slots[2]

    @property
    def SPAWN_W1(self) -> FloorMonsterSpawn:
        return self.spawns[0]

    @property
    def SPAWN_W2(self) -> FloorMonsterSpawn:
        return self.spawns[1]

    @property
    def SPAWN_W3(self) -> FloorMonsterSpawn:
        return self.spawns[2]

    @property
    def SPAWN_BOSS(self) -> FloorMonsterSpawn:
        return self.spawn_boss

    @property
    def TOTAL_WAVES(self) -> int:
        return self.total_waves

    def is_floor(self, floor_number: int) -> bool:
        return int(floor_number) == self.config.floor_number

    def all_spawns(self) -> list[FloorMonsterSpawn]:
        return [*self.spawns, self.spawn_boss]

    def spawn_by_slot(self, slot: str) -> FloorMonsterSpawn | None:
        for s in self.all_spawns():
            if s.slot_code == slot:
                return s
        return None

    def waves_cleared_count(self, defeated_slots: frozenset[str]) -> int:
        return sum(1 for s in self.wave_slots if s in defeated_slots)

    def current_available_slot(self, defeated_slots: frozenset[str]) -> str | None:
        for slot in self.wave_slots:
            if slot not in defeated_slots:
                return slot
        if self.config.slot_boss not in defeated_slots:
            return self.config.slot_boss
        return None

    def ensure_started(self, character: Character) -> None:
        if int(character.floor_number) != self.config.floor_number:
            return
        meta = dict(character.meta_progress or {})
        if not meta.get(self.config.meta_key):
            meta[self.config.meta_key] = {"started": True}
            character.meta_progress = meta

    def format_banner_html(self, defeated_slots: frozenset[str]) -> str:
        cleared = self.waves_cleared_count(defeated_slots)
        b = self.config.banner
        if self.config.slot_boss in defeated_slots:
            return b.boss_done
        if cleared == self.total_waves:
            return b.all_waves_done
        bar = b.filled_tile * cleared + b.empty_tile * (self.total_waves - cleared)
        return b.title_fmt.format(bar=bar, cleared=cleared, total=self.total_waves, hint=b.next_hint)


def expose_legacy_module(
    mech: WaveMechanic,
    *,
    is_floor_name: str,
    floor_const_name: str,
    all_slots_name: str,
    all_spawns_name: str,
    format_banner_name: str,
) -> dict[str, object]:
    cfg = mech.config
    fn = mech.floor_number
    out: dict[str, object] = {
        floor_const_name: fn,
        f"WAVE_FLOOR_{fn}": fn,
        "TOTAL_WAVES": mech.total_waves,
        "META_KEY": cfg.meta_key,
        "SLOT_WAVE_1": mech.SLOT_WAVE_1,
        "SLOT_WAVE_2": mech.SLOT_WAVE_2,
        "SLOT_WAVE_3": mech.SLOT_WAVE_3,
        "SLOT_BOSS": cfg.slot_boss,
        "WAVE_SLOTS": mech.wave_slots,
        all_slots_name: mech.all_slots,
        "SPAWN_W1": mech.SPAWN_W1,
        "SPAWN_W2": mech.SPAWN_W2,
        "SPAWN_W3": mech.SPAWN_W3,
        "SPAWN_BOSS": mech.SPAWN_BOSS,
        all_spawns_name: mech.all_spawns,
        "spawn_by_slot": mech.spawn_by_slot,
        is_floor_name: mech.is_floor,
        "waves_cleared_count": mech.waves_cleared_count,
        "current_available_slot": mech.current_available_slot,
        "ensure_started": mech.ensure_started,
        format_banner_name: mech.format_banner_html,
    }
    return out
