"""Бойцы PvE-колизея."""

from game.enemies.coliseum.fighters import *  # noqa: F403
from game.enemies.coliseum.rewards import COLISEUM_LOOT, LootEntry, loot_for_fighter_id

__all__ = [n for n in globals() if not n.startswith("_")]
