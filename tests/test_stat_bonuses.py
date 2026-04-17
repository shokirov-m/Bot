"""Бонусы характеристик с предметов (item_data)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from game.items.stat_bonuses import stat_bonuses_from_item_data


def test_stat_bonuses_flat_and_nested_and_aliases() -> None:
    d = {
        "str": 2,
        "strength": 1,
        "stat_bonus": {"dex": 1, "luck": 2},
    }
    b = stat_bonuses_from_item_data(d)
    assert b["str"] == 3
    assert b["dex"] == 1
    assert b["luck"] == 2
    assert b["int"] == 0
    assert b["vit"] == 0


def test_stat_bonuses_enchant_on_armor() -> None:
    d = {
        "kind": "armor",
        "rarity": "rare",
        "str": 2,
        "enchant": 5,
    }
    b = stat_bonuses_from_item_data(d)
    # +6 от редкости к ненулевому stat, +3 от заточки ( (5+1)//2 )
    assert b["str"] == 2 + 6 + 3


def test_stat_bonuses_enchant_pure_defense_ring() -> None:
    d = {"kind": "ring", "rarity": "common", "defense": 5, "enchant": 4}
    b = stat_bonuses_from_item_data(d)
    assert b["vit"] >= 2  # (4+1)//2


@pytest.mark.asyncio
async def test_equipped_gear_stat_bonuses_includes_ring2_and_offhand(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сервис суммирует все надетые строки: второе кольцо и оружие во второй руке не отбрасываются."""
    from services import stat_bonus_service

    async def fake_list(_session, _character_id: int):
        return [
            SimpleNamespace(item_data={"kind": "ring", "int": 2, "ring_slot": "2"}),
            SimpleNamespace(item_data={"kind": "weapon", "hand": "off", "dex": 5, "attack": 3}),
        ]

    monkeypatch.setattr(stat_bonus_service.inventory_repo, "list_equipped_items", fake_list)
    total = await stat_bonus_service.equipped_gear_stat_bonuses(None, 1)  # type: ignore[arg-type]
    assert total["int"] == 2
    assert total["dex"] == 5
