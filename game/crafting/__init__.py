"""Крафт / рецепты."""

from game.crafting.recipes_data import (
    RECIPES,
    forge_recipes_only,
    get_recipe_by_id,
    is_forge_instant,
    recipes_for_profession,
)

__all__ = [
    "RECIPES",
    "forge_recipes_only",
    "get_recipe_by_id",
    "is_forge_instant",
    "recipes_for_profession",
]
