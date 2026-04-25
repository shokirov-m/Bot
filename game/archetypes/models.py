"""
Core Models for Archetype System 2.0.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

NodeType = Literal["active_skill", "passive_bonus", "stat_boost"]

@dataclass(frozen=True, slots=True)
class SkillV2:
    key: str
    name_ru: str
    description_ru: str
    mp_cost: int
    cooldown: int
    power_mult: float
    kind: Literal["phys", "mag"]
    effect_key: str | None = None
    effect_chance: float = 0.0
    required_level: int = 1

@dataclass(frozen=True, slots=True)
class PassiveV2:
    key: str
    name_ru: str
    description_ru: str
    # Modifiers: {"def_bonus": 5.0, "mag_bonus_percent": 10, ...}
    modifiers: dict[str, float | int] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class SkillTreeNode:
    key: str
    name_ru: str
    description_ru: str
    node_type: NodeType
    
    # Reference to a SkillV2 key if type is active_skill
    # Reference to modifier keys if type is passive_bonus or stat_boost
    value: str | dict[str, float | int]
    
    cost_sp: int = 1
    
    # Prerequisite node keys
    parent_keys: tuple[str, ...] = field(default_factory=tuple)
    
    # Tier requirement
    required_tier: int = 1

@dataclass(frozen=True, slots=True)
class Archetype:
    key: str
    name_ru: str
    emoji: str
    tier: int  # 0: Wanderer, 1: Base, 2: Specialization, 3: Master
    description_ru: str
    
    # Base stats at the moment of choosing the archetype
    base_stats: dict[str, int] = field(default_factory=dict)
    
    # Combat passives unique to this archetype
    passives: tuple[PassiveV2, ...] = field(default_factory=tuple)
    
    # Keys of skills available to this archetype
    skills: tuple[str, ...] = field(default_factory=tuple)
    
    # Stat multipliers
    hp_multiplier: float = 1.0
    mp_multiplier: float = 1.0
    
    # Requirement to unlock (e.g., {"level": 10, "stat_strength": 50})
    requirements: dict[str, int] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.emoji} {self.name_ru}"
