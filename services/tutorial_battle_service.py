"""
Обучающий бой на этаже 1: награда — звание (path_ranks), не титул.
"""

from __future__ import annotations

from db.models.character import Character
from game.characters.classes import get_class_or_none
from game.characters.path_ranks import PATH_RANK_BY_KEY, path_rank_key_from_battle
from services import character_service

_META_TUTORIAL = "tutorial_battle"
_META_PATH_RANK = "path_rank_key"
_META_PATH_PASSIVE = "path_passive_key"
# Совместимость со старыми сохранениями
_LEGACY_PATH_TITLE = "tutorial_path_title"


def tutorial_battle_pending(character: Character) -> bool:
    mp = character.meta_progress or {}
    v = mp.get(_META_TUTORIAL)
    if v is None:
        return False
    return str(v) == "pending"


def _recompute_pools(character: Character) -> None:
    cls = get_class_or_none(character.class_key)
    if cls is None:
        return
    hp_ratio = int(character.hp_current) / max(1, int(character.hp_max))
    mp_ratio = int(character.mp_current) / max(1, max(1, int(character.mp_max)))
    character.hp_max = max(
        1,
        character_service._compute_hp_max(
            int(character.stat_vitality),
            int(character.stat_strength),
            cls,
        ),
    )
    character.mp_max = max(
        0,
        character_service._compute_mp_max(int(character.stat_intelligence), cls),
    )
    character.hp_current = max(1, min(int(character.hp_max), int(character.hp_max * hp_ratio)))
    character.mp_current = max(0, min(int(character.mp_max), int(character.mp_max * mp_ratio)))


def apply_path_rank_from_tutorial(
    character: Character,
    *,
    player_rounds: int,
    hp_end: int,
    hp_max: int,
    used_skill: bool,
) -> tuple[str, str]:
    """
    Начислить звание по исходу боя. Возвращает (ключ звания, описание пассива).
    Не трогает титулы и active_title.
    """
    key = path_rank_key_from_battle(player_rounds, hp_end, hp_max, used_skill)
    r = PATH_RANK_BY_KEY[key]

    character.stat_strength = int(character.stat_strength) + int(r.stat_str)
    character.stat_dexterity = int(character.stat_dexterity) + int(r.stat_dex)
    character.stat_intelligence = int(character.stat_intelligence) + int(r.stat_int)
    character.stat_vitality = int(character.stat_vitality) + int(r.stat_vit)
    character.stat_luck = int(character.stat_luck) + int(r.stat_luck)
    _recompute_pools(character)

    mp = dict(character.meta_progress or {})
    mp[_META_TUTORIAL] = "done"
    mp[_META_PATH_RANK] = key
    mp[_LEGACY_PATH_TITLE] = key
    if r.passive_key:
        mp[_META_PATH_PASSIVE] = str(r.passive_key)
    character.meta_progress = mp

    return key, r.skill_ru
