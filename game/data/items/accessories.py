"""Кольца, амулеты, щиты, гримуары — тонкий агрегатор для редактирования."""

from __future__ import annotations

from game.data.items.amulets import amulet_examples
from game.data.items.offhand import grimoire_examples, shield_examples
from game.data.items.rings import ring_examples

__all__ = [
    "amulet_examples",
    "grimoire_examples",
    "ring_examples",
    "shield_examples",
]
