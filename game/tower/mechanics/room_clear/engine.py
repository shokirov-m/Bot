"""Общая логика механики «зачистка комнат» для этажей 5, 10, 24, 26, 30, 40."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from db.models.character import Character
from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate


@dataclass(frozen=True, slots=True)
class RoomClearBanner:
    boss_done: str
    """Шаблон активного баннера: {room_bar} {cleared} {total} {hint} {monster_line}."""
    title_fmt: str
    hint_boss: str
    monster_line_fmt: str = "Монстров: {mon}/{mon_total} {subhint}"
    monster_subhint: str = "<i>(в каждой комнате 2-3 последовательных боя)</i>"
    filled_tile: str = "🟩"
    empty_tile: str = "⬜"


@dataclass(frozen=True, slots=True)
class RoomClearConfig:
    floor_number: int
    meta_key: str
    slot_boss: str
    button_prefix: str
    room_groups: tuple[tuple[str, ...], ...]
    room_templates: tuple[tuple[MonsterTemplate, ...], ...]
    boss_template: MonsterTemplate
    banner: RoomClearBanner
    duo_room_index: int = 3
    all_slots_attr: str = "ROOM_CLEAR_ALL_SLOTS"


class RoomClearMechanic:
    """Экземпляр механики для одного этажа."""

    __slots__ = ("config", "total_rooms", "room_button_codes", "slot_rooms", "room_spawns", "spawn_boss", "all_slots")

    def __init__(self, config: RoomClearConfig) -> None:
        self.config = config
        self.total_rooms = len(config.room_groups)
        self.room_button_codes = [f"{config.button_prefix}{i}" for i in range(self.total_rooms)]
        self.slot_rooms = [s for grp in config.room_groups for s in grp]
        self.room_spawns = self._build_room_spawns()
        self.spawn_boss = FloorMonsterSpawn(
            slot_code=config.slot_boss,
            template=config.boss_template,
            is_elite=False,
            is_mini_boss=False,
            is_major_boss=True,
        )
        self.all_slots = frozenset(self.room_button_codes + self.slot_rooms + [config.slot_boss])

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
    def room_groups(self) -> tuple[tuple[str, ...], ...]:
        return self.config.room_groups

    @property
    def room_duo_index(self) -> int:
        return self.config.duo_room_index

    # Aliases for legacy module attribute names
    @property
    def ROOM_CLEAR_FLOOR(self) -> int:
        return self.config.floor_number

    @property
    def TOTAL_ROOMS(self) -> int:
        return self.total_rooms

    @property
    def META_KEY(self) -> str:
        return self.config.meta_key

    @property
    def SLOT_BOSS(self) -> str:
        return self.config.slot_boss

    @property
    def ROOM_BUTTON_CODES(self) -> list[str]:
        return self.room_button_codes

    @property
    def ROOM_GROUPS(self) -> list[list[str]]:
        return [list(g) for g in self.config.room_groups]

    @property
    def SLOT_ROOMS(self) -> list[str]:
        return list(self.slot_rooms)

    @property
    def ROOM_DUO_INDEX(self) -> int:
        return self.config.duo_room_index

    @property
    def SPAWN_BOSS(self) -> FloorMonsterSpawn:
        return self.spawn_boss

    def _build_room_spawns(self) -> list[list[FloorMonsterSpawn]]:
        result: list[list[FloorMonsterSpawn]] = []
        for room_idx, (slots, templates) in enumerate(zip(self.config.room_groups, self.config.room_templates)):
            room_spawns: list[FloorMonsterSpawn] = []
            for m_idx, (slot, tmpl) in enumerate(zip(slots, templates)):
                if room_idx == self.config.duo_room_index:
                    room_spawns.append(
                        FloorMonsterSpawn(
                            slot_code=slot,
                            template=tmpl,
                            is_elite=False,
                            is_mini_boss=True,
                            is_major_boss=False,
                        )
                    )
                else:
                    is_elite = m_idx == len(slots) - 1
                    room_spawns.append(
                        FloorMonsterSpawn(
                            slot_code=slot,
                            template=tmpl,
                            is_elite=is_elite,
                            is_mini_boss=False,
                            is_major_boss=False,
                        )
                    )
            result.append(room_spawns)
        return result

    def all_room_clear_spawns(self) -> list[FloorMonsterSpawn]:
        result: list[FloorMonsterSpawn] = []
        for grp in self.room_spawns:
            result.extend(grp)
        result.append(self.spawn_boss)
        return result

    def spawn_by_slot(self, slot: str) -> FloorMonsterSpawn | None:
        for s in self.all_room_clear_spawns():
            if s.slot_code == slot:
                return s
        return None

    def is_floor(self, floor_number: int) -> bool:
        return int(floor_number) == self.config.floor_number

    def room_index_for_button(self, button_code: str) -> int | None:
        if button_code in self.room_button_codes:
            try:
                return int(button_code.replace(self.config.button_prefix, ""))
            except ValueError:
                return None
        return None

    def next_slot_in_room(self, room_idx: int, beaten: frozenset[str]) -> str | None:
        if room_idx < 0 or room_idx >= self.total_rooms:
            return None
        for slot in self.config.room_groups[room_idx]:
            if slot not in beaten:
                return slot
        return None

    def is_room_complete(self, room_idx: int, beaten: frozenset[str]) -> bool:
        if room_idx < 0 or room_idx >= self.total_rooms:
            return False
        return all(s in beaten for s in self.config.room_groups[room_idx])

    def rooms_cleared_count(self, defeated_slots: frozenset[str]) -> int:
        return sum(1 for i in range(self.total_rooms) if self.is_room_complete(i, defeated_slots))

    def total_monsters_cleared(self, defeated_slots: frozenset[str]) -> int:
        return sum(1 for s in self.slot_rooms if s in defeated_slots)

    def is_boss_unlocked(self, defeated_slots: frozenset[str]) -> bool:
        return all(self.is_room_complete(i, defeated_slots) for i in range(self.total_rooms))

    def next_available_room_index(self, beaten: frozenset[str]) -> int:
        for i in range(self.total_rooms):
            if not self.is_room_complete(i, beaten):
                return i
        return self.total_rooms

    def slot_room_and_monster_index(self, slot: str) -> tuple[int, int] | None:
        for room_idx, room_slots in enumerate(self.config.room_groups):
            for monster_idx, s in enumerate(room_slots):
                if s == slot:
                    return room_idx, monster_idx
        return None

    def next_slot_after_defeat(self, slot: str) -> str | None:
        result = self.slot_room_and_monster_index(slot)
        if result is None:
            return None
        room_idx, monster_idx = result
        room_slots = self.config.room_groups[room_idx]
        if monster_idx + 1 < len(room_slots):
            return room_slots[monster_idx + 1]
        return None

    def ensure_started(self, character: Character) -> None:
        if int(character.floor_number) != self.config.floor_number:
            return
        meta = dict(character.meta_progress or {})
        if not meta.get(self.config.meta_key):
            meta[self.config.meta_key] = {"started": True}
            character.meta_progress = meta

    def format_room_clear_banner_html(self, defeated_slots: frozenset[str]) -> str:
        b = self.config.banner
        if self.config.slot_boss in defeated_slots:
            return b.boss_done

        cleared_rooms = self.rooms_cleared_count(defeated_slots)
        total_mon = self.total_monsters_cleared(defeated_slots)
        total_slots = len(self.slot_rooms)

        hint = b.hint_boss if cleared_rooms == self.total_rooms else ""
        room_bar = b.filled_tile * cleared_rooms + b.empty_tile * (self.total_rooms - cleared_rooms)
        monster_line = b.monster_line_fmt.format(
            mon=total_mon,
            mon_total=total_slots,
            subhint=b.monster_subhint,
        )
        return b.title_fmt.format(
            room_bar=room_bar,
            cleared=cleared_rooms,
            total=self.total_rooms,
            hint=hint,
            monster_line=monster_line,
        )


def expose_legacy_module(
    mech: RoomClearMechanic,
    *,
    is_floor_name: str,
    all_slots_name: str | None = None,
) -> dict[str, object]:
    """Словарь атрибутов для обратной совместимости с ``import room_clear_floor as mod``."""
    slots_name = all_slots_name or mech.config.all_slots_attr
    out: dict[str, object] = {
        "ROOM_CLEAR_FLOOR": mech.config.floor_number,
        f"ROOM_CLEAR_FLOOR_{mech.config.floor_number}": mech.config.floor_number,
        "TOTAL_ROOMS": mech.total_rooms,
        "META_KEY": mech.meta_key,
        "SLOT_BOSS": mech.slot_boss,
        "ROOM_BUTTON_CODES": mech.room_button_codes,
        "ROOM_GROUPS": mech.ROOM_GROUPS,
        "SLOT_ROOMS": mech.slot_rooms,
        "ROOM_DUO_INDEX": mech.room_duo_index,
        "SPAWN_BOSS": mech.spawn_boss,
        slots_name: mech.all_slots,
        "all_room_clear_spawns": mech.all_room_clear_spawns,
        "spawn_by_slot": mech.spawn_by_slot,
        is_floor_name: mech.is_floor,
        "room_index_for_button": mech.room_index_for_button,
        "next_slot_in_room": mech.next_slot_in_room,
        "is_room_complete": mech.is_room_complete,
        "rooms_cleared_count": mech.rooms_cleared_count,
        "total_monsters_cleared": mech.total_monsters_cleared,
        "is_boss_unlocked": mech.is_boss_unlocked,
        "next_available_room_index": mech.next_available_room_index,
        "slot_room_and_monster_index": mech.slot_room_and_monster_index,
        "next_slot_after_defeat": mech.next_slot_after_defeat,
        "ensure_started": mech.ensure_started,
        "format_room_clear_banner_html": mech.format_room_clear_banner_html,
    }
    return out
