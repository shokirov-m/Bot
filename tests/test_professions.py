"""Профессии: разблокировки, второй слот по этажу, миграция со старого класса."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from db.models.character import Character
from game.characters.professions import PROFESSION_BY_KEY, SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR
from game.items import enchant as enchant_mod
from services import profession_service, stat_bonus_service


def _bare_character(**kwargs: object) -> Character:
    defaults = dict(
        user_id=1,
        display_name="T",
        class_key="wanderer",
        stat_strength=10,
        stat_dexterity=10,
        stat_intelligence=10,
        stat_vitality=10,
        stat_luck=10,
        level=1,
        floor_number=1,
        highest_floor_reached=1,
        enchant_attempts=0,
        meta_progress={},
    )
    defaults.update(kwargs)
    return Character(**defaults)


def test_meets_unlock_warrior_at_str() -> None:
    c = _bare_character(stat_strength=80)
    assert profession_service.meets_unlock(c, PROFESSION_BY_KEY["warrior"]) is True
    c2 = _bare_character(stat_strength=79)
    assert profession_service.meets_unlock(c2, PROFESSION_BY_KEY["warrior"]) is False


def test_meets_unlock_smith_enchants() -> None:
    c = _bare_character(enchant_attempts=80)
    assert profession_service.meets_unlock(c, PROFESSION_BY_KEY["smith"]) is True


def test_secondary_slot_requires_floor() -> None:
    c = _bare_character(
        highest_floor_reached=SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR - 1,
        meta_progress={
            "professions_unlocked": ["warrior", "mage"],
            "active_profession": "warrior",
            "active_profession_2": "mage",
            "_professions_migrated_v1": True,
        },
    )
    profession_service.ensure_profession_meta(c)
    assert profession_service.active_secondary_key(c) is None


def test_migrate_legacy_sets_active_from_class_key() -> None:
    c = _bare_character(class_key="mage", meta_progress={})
    profession_service.ensure_profession_meta(c)
    assert "mage" in profession_service.unlocked_keys(c)
    assert profession_service.active_primary_key(c) == "mage"
    assert profession_service.combat_skill_class_key(c) == "mage"


def test_combat_skill_fallback_wanderer() -> None:
    c = _bare_character(
        class_key="wanderer",
        meta_progress={"_professions_migrated_v1": True},
    )
    profession_service.ensure_profession_meta(c)
    assert profession_service.combat_skill_class_key(c) == "wanderer"


@pytest.mark.asyncio
async def test_profession_stat_bonus_in_effective(monkeypatch: pytest.MonkeyPatch) -> None:
    c = _bare_character(
        stat_strength=50,
        meta_progress={
            "professions_unlocked": ["warrior"],
            "active_profession": "warrior",
            "_professions_migrated_v1": True,
        },
    )
    profession_service.ensure_profession_meta(c)

    async def empty_gear(_s: object, _cid: int) -> dict[str, int]:
        return {"str": 0, "dex": 0, "int": 0, "vit": 0, "luck": 0}

    monkeypatch.setattr(stat_bonus_service, "equipped_gear_stat_bonuses", empty_gear)
    session = AsyncMock()
    eff = await stat_bonus_service.effective_primary_stats(session, c)
    assert eff["str"] == 60


def test_enchant_roll_accepts_bonus() -> None:
    enchant_mod.roll_enchant_outcome(5, success_chance_bonus=0.1)
