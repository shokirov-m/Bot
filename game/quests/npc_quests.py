"""
Расширенные квесты NPC на этажах, кратных 3 (отдельно от «странника» tower_slain_*).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from game.floors import floor_data
from game.floors.monsters import (
    MonsterTemplate,
    major_boss_for_zone,
    mini_boss_for_zone,
    zone_monster_templates,
)


@dataclass(frozen=True, slots=True)
class QuestTemplate:
    key: str
    floor: int
    npc_name: str
    npc_emoji: str
    title: str
    description: str
    quest_type: str  # kill | kill_elite | kill_mini | defeat_boss
    target_key: str  # monster key или пусто для «любой элиты»
    target_count: int
    reward_gold: int
    reward_exp: int
    reward_item_chance: float
    reward_rune_chance: float


_ZONE_NPC: dict[str, tuple[str, str]] = {
    "forest_beginnings": ("Лесник Борис", "🌲"),
    "rotten_swamps": ("Болотник Дрозд", "🐸"),
    "shadow_caves": ("Шахтёр Грим", "⛏️"),
    "icy_peaks": ("Следопыт Юна", "🧣"),
    "desert_oblivion": ("Караванщик Саид", "🐪"),
    "volcanic_ruins": ("Кузнец Варрак", "🔥"),
    "sky_citadel": ("Дозорный Кейл", "☁️"),
    "chaos_abyss": ("Отступник Малекс", "🌀"),
    "eternity_hall": ("Глашатай Век", "⚡"),
    floor_data.ZONE_FINAL_KEY: ("Эхо башни", "👁️"),
}


def _scaled_rewards(floor: int) -> tuple[int, int, float, float]:
    gold = 50 + floor * 8
    exp = 30 + floor * 5
    item_chance = min(0.85, 0.05 + (floor / 100.0) * 0.25)
    rune_chance = min(0.45, 0.02 + floor / 250.0)
    return gold, exp, item_chance, rune_chance


def _boss_rewards(floor: int) -> tuple[int, int, float, float]:
    """Усиленная награда за сильного босса (этажи ×10)."""
    gold = max(400, 200 + floor * 12)
    exp = max(250, 120 + floor * 8)
    item_chance = min(0.9, 0.35 + floor / 200.0)
    rune_chance = min(0.55, 0.15 + floor / 180.0)
    return gold, exp, item_chance, rune_chance


def _npc_for_floor(floor: int) -> tuple[str, str]:
    z = floor_data.get_zone_for_floor(floor)
    return _ZONE_NPC.get(z.key, ("Странник", "📜"))


def _pick_hunt_monster(zone_key: str, floor: int) -> MonsterTemplate:
    pool = zone_monster_templates(zone_key)
    if not pool:
        raise RuntimeError(f"Нет пула монстров для зоны {zone_key}")
    i = max(0, floor - 1) % len(pool)
    return pool[i]


def _two_quests_for_floor(floor: int) -> list[QuestTemplate]:
    """Два поручения на этаж (кратный 3)."""
    z = floor_data.get_zone_for_floor(floor)
    npc_name, npc_emoji = _npc_for_floor(floor)
    g1, e1, ic1, rc1 = _scaled_rewards(floor)
    m_a = _pick_hunt_monster(z.key, floor)

    kill_need = 5 if floor <= 12 else 6 if floor <= 40 else 7 if floor <= 70 else 8
    q1 = QuestTemplate(
        key=f"npcq_{floor}_hunt",
        floor=floor,
        npc_name=npc_name,
        npc_emoji=npc_emoji,
        title=f"Охота: {m_a.name}",
        description=(
            f"Убей {kill_need} × {m_a.name.lower()} — угроза для окрестностей."
        ),
        quest_type="kill",
        target_key=m_a.key,
        target_count=kill_need,
        reward_gold=g1,
        reward_exp=e1,
        reward_item_chance=ic1,
        reward_rune_chance=rc1,
    )

    if floor_data.is_major_boss_floor(floor):
        boss = major_boss_for_zone(z, floor)
        gb, eb, icb, rcb = _boss_rewards(floor)
        q2 = QuestTemplate(
            key=f"npcq_{floor}_lord",
            floor=floor,
            npc_name=npc_name,
            npc_emoji=npc_emoji,
            title=f"Падение: {boss.name}",
            description=f"Срази сильного стража этажа — {boss.name.lower()}.",
            quest_type="defeat_boss",
            target_key=boss.key,
            target_count=1,
            reward_gold=gb,
            reward_exp=eb,
            reward_item_chance=icb,
            reward_rune_chance=rcb,
        )
    elif floor_data.is_mini_boss_floor(floor):
        mini = mini_boss_for_zone(z, floor)
        q2 = QuestTemplate(
            key=f"npcq_{floor}_champ",
            floor=floor,
            npc_name=npc_name,
            npc_emoji=npc_emoji,
            title=f"Чемпион: {mini.name}",
            description=f"Победи мини-босса — {mini.name.lower()}.",
            quest_type="kill_mini",
            target_key=mini.key,
            target_count=1,
            reward_gold=g1 + 40 + floor,
            reward_exp=e1 + 25 + floor // 2,
            reward_item_chance=min(0.9, ic1 + 0.08),
            reward_rune_chance=min(0.5, rc1 + 0.05),
        )
    else:
        q2 = QuestTemplate(
            key=f"npcq_{floor}_elite",
            floor=floor,
            npc_name=npc_name,
            npc_emoji=npc_emoji,
            title="Звезда зоны: элита",
            description="Убей элитного врага на этом кольце башни.",
            quest_type="kill_elite",
            target_key="",
            target_count=1,
            reward_gold=g1 + 25 + floor // 2,
            reward_exp=e1 + 15 + floor // 3,
            reward_item_chance=min(0.88, ic1 + 0.06),
            reward_rune_chance=min(0.48, rc1 + 0.04),
        )

    return [q1, q2]


def generate_quest_pool() -> dict[int, list[QuestTemplate]]:
    """Квесты для каждого этажа 3, 6, …, 99."""
    return {f: _two_quests_for_floor(f) for f in range(3, 100, 3)}


@lru_cache(maxsize=1)
def quest_pool() -> dict[int, list[QuestTemplate]]:
    return generate_quest_pool()


def templates_for_floor(floor: int) -> list[QuestTemplate]:
    if floor <= 0 or floor % 3 != 0 or floor >= 100:
        return []
    return list(quest_pool().get(floor, []))


def template_by_key(quest_key: str) -> QuestTemplate | None:
    for group in quest_pool().values():
        for t in group:
            if t.key == quest_key:
                return t
    return None


def quest_bonus_item_payload(floor: int) -> dict | None:
    """Предмет из каталога за выполнение квеста NPC."""
    from game.items.catalog_loot import roll_catalog_item
    return roll_catalog_item(floor)
