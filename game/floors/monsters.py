"""
Шаблоны монстров по зонам и выбор врагов для этажа (UI + задел под бой).
"""

from __future__ import annotations

from dataclasses import dataclass

from game.data.monsters import MONSTER_TEMPLATE_META, ZONE_POOL_KEYS
from game.floors import floor_data


def _template(key: str) -> MonsterTemplate:
    m = MONSTER_TEMPLATE_META[key]
    return MonsterTemplate(key, m["display_name"], m["emoji"], m["element"], m["blurb"])


@dataclass(frozen=True, slots=True)
class MonsterTemplate:
    """Описание монстра для отображения и будущего боя."""

    key: str
    name: str
    emoji: str
    element: str  # fire, ice, lightning, dark, light, earth
    blurb: str


def _short_monster_name(name: str, max_len: int = 15) -> str:
    """Короткая подпись для кнопок этажа и телефонов."""
    n = (name or "").strip()
    if len(n) <= max_len:
        return n
    return n[: max_len - 1] + "…"


@dataclass(frozen=True, slots=True)
class FloorMonsterSpawn:
    """Вариант на экране этажа."""

    slot_code: str  # 0-4 обычные, e — элита, m — мини-босс, b — сильный босс
    template: MonsterTemplate
    is_elite: bool
    is_mini_boss: bool
    is_major_boss: bool

    @property
    def display_name(self) -> str:
        short = _short_monster_name(self.template.name)
        if self.is_major_boss:
            return f"👑 {short}"
        if self.is_mini_boss:
            return f"⚔️ {short}"
        if self.is_elite:
            return f"⭐ {short}"
        return f"{self.template.emoji} {short}"


def zone_monster_templates(zone_key: str) -> tuple[MonsterTemplate, ...]:
    """Все шаблоны монстров зоны (для квестов NPC и т.п.)."""
    return _pool(zone_key)


def _pool(zone_key: str) -> tuple[MonsterTemplate, ...]:
    keys = ZONE_POOL_KEYS.get(zone_key, ZONE_POOL_KEYS["forest_beginnings"])
    return tuple(_template(k) for k in keys)


def _pick_indices(floor_number: int, count: int, pool_len: int) -> list[int]:
    """Детерминированный выбор индексов без random (стабильный UI)."""
    if pool_len <= 0:
        return []
    seed = floor_number * 1103515245 + 12345
    indices: list[int] = []
    used: set[int] = set()
    x = seed % (2**31)
    while len(indices) < min(count, pool_len):
        x = (x * 1664525 + 1013904223) % (2**32)
        idx = x % pool_len
        if idx not in used:
            used.add(idx)
            indices.append(idx)
    return indices


def floor_spawn_indices(floor_number: int, count: int = 6) -> list[int]:
    """
    Публичный хелпер: возвращает индексы (в `zone_monster_templates`)
    тех монстров, что реально могут заспавниться на этаже.
    Используется в квестах, чтобы не выдавать охоту на «несуществующего» моба.
    """
    zone = floor_data.get_zone_for_floor(floor_number)
    pool = _pool(zone.key)
    return _pick_indices(int(floor_number), int(count), len(pool))


def mini_boss_for_zone(zone: floor_data.ZoneInfo, floor_number: int) -> MonsterTemplate:
    """Уникальный мини-босс по зоне."""
    table: dict[str, str] = {
        "forest_beginnings": "mini_alpha_wolf",
        "rotten_swamps": "mini_bog_queen",
        "shadow_caves": "mini_shadow_weaver",
        "icy_peaks": "mini_frost_troll",
        "desert_oblivion": "mini_sand_titan",
        "volcanic_ruins": "mini_magma_lord",
        "sky_citadel": "mini_storm_herald",
        "chaos_abyss": "mini_chaos_knight",
        "eternity_hall": "mini_time_judge",
        floor_data.ZONE_FINAL_KEY: "final_warden",
    }
    return _template(table.get(zone.key, table["forest_beginnings"]))


def major_boss_for_zone(zone: floor_data.ZoneInfo, floor_number: int) -> MonsterTemplate:
    """Сильный босс на каждом 10-м этаже."""
    # Для этажа 135 — финальный страж
    if floor_number >= 135:
        return _template("boss_tower_core")
    table: dict[str, str] = {
        "forest_beginnings": "boss_ancient_treant",
        "rotten_swamps": "boss_slime_king",
        "shadow_caves": "boss_night_stalker",
        "icy_peaks": "boss_glacier_king",
        "desert_oblivion": "boss_time_scarab",
        "volcanic_ruins": "boss_ember_dragon",
        "sky_citadel": "boss_sky_tyrant",
        "chaos_abyss": "boss_chaos_avatar",
        "eternity_hall": "boss_eternity_judge",
        "jade_labyrinth": "boss_eternity_judge",
        "frozen_wastes": "boss_chaos_avatar",
        "faction_war_plains": "boss_eternity_judge",
    }
    return _template(table.get(zone.key, table["forest_beginnings"]))


def build_spawns_for_floor(floor_number: int) -> list[FloorMonsterSpawn]:
    """
    Список целей на этаже: 6 обычных + элита (на базе первого),
    плюс мини-босс / сильный босс по правилам этажа.
    """
    # Этаж 3 — только город-хаб: боёв на карте нет (монстры, тайник, привал — убраны с экрана).
    if int(floor_number) == 3:
        return []
    if floor_number >= 135:
        zone = floor_data.ZONE_FINAL
        bb = major_boss_for_zone(zone, floor_number)
        return [
            FloorMonsterSpawn(
                slot_code="b",
                template=bb,
                is_elite=False,
                is_mini_boss=False,
                is_major_boss=True,
            ),
        ]

    zone = floor_data.get_zone_for_floor(floor_number)
    pool = _pool(zone.key)
    picks = _pick_indices(floor_number, 6, len(pool))
    spawns: list[FloorMonsterSpawn] = []

    for i, idx in enumerate(picks):
        tpl = pool[idx]
        spawns.append(
            FloorMonsterSpawn(
                slot_code=str(i),
                template=tpl,
                is_elite=False,
                is_mini_boss=False,
                is_major_boss=False,
            ),
        )

    if spawns:
        first = spawns[0].template
        spawns.append(
            FloorMonsterSpawn(
                slot_code="e",
                template=MonsterTemplate(
                    key=f"elite_{first.key}",
                    name=first.name,
                    emoji=first.emoji,
                    element=first.element,
                    blurb=first.blurb + " (элита: усилен; +~62% к HP и урону)",
                ),
                is_elite=True,
                is_mini_boss=False,
                is_major_boss=False,
            ),
        )

    if floor_data.is_mini_boss_floor(floor_number):
        mb = mini_boss_for_zone(zone, floor_number)
        spawns.append(
            FloorMonsterSpawn(
                slot_code="m",
                template=mb,
                is_elite=False,
                is_mini_boss=True,
                is_major_boss=False,
            ),
        )

    if floor_data.is_major_boss_floor(floor_number):
        bb = major_boss_for_zone(zone, floor_number)
        spawns.append(
            FloorMonsterSpawn(
                slot_code="b",
                template=bb,
                is_elite=False,
                is_mini_boss=False,
                is_major_boss=True,
            ),
        )

    return spawns
