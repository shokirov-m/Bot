"""Списание и проверка стамины."""

from __future__ import annotations

from db.models.character import Character


def can_start_combat(character: Character, max_stamina: int) -> bool:
    return character.stamina >= 1


def spend_stamina_for_combat(character: Character) -> None:
    """
    Устаревшее синхронное списание; в бою используйте game.economy.stamina.spend_stamina (атомарно в БД).
    """
    character.stamina = max(0, int(character.stamina) - 1)
