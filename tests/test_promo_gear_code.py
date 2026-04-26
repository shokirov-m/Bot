"""Статический промокод с экипировкой в сумку."""

from types import SimpleNamespace

from game.characters import pets as pets_mod
from game.promos import bag_payloads_for_code, promo_pet_key_for_code, reward_for_code


def test_gift10k_reward() -> None:
    r = reward_for_code("GIFT10K")
    assert r is not None
    assert r.gold == 10000
    assert r.xp == 10000
    assert r.rune_stones == 0
    assert bag_payloads_for_code("GIFT10K") is None
    assert promo_pet_key_for_code("GIFT10K") is None


def test_basekit26_reward_and_bag_payloads() -> None:
    r = reward_for_code("BASEKIT26")
    assert r is not None
    assert r.gold == 30
    assert r.xp == 40

    bags = bag_payloads_for_code("BASEKIT26")
    assert bags is not None
    assert len(bags) == 2
    assert bags[0].get("kind") == "armor"
    assert bags[1].get("kind") == "amulet"


def test_unknown_code_no_bag() -> None:
    assert bag_payloads_for_code("NOSUCH") is None


def test_voidpromo26_pet_and_reward() -> None:
    r = reward_for_code("VOIDPROMO26")
    assert r is not None
    assert promo_pet_key_for_code("VOIDPROMO26") == "pet_void_wisp"
    ch = SimpleNamespace(meta_progress={})
    st, nm = pets_mod.try_grant_promo_pet(ch, "pet_void_wisp")
    assert st == "new"
    assert nm
    assert "pet_void_wisp" in pets_mod.owned_keys(ch)
    st2, _ = pets_mod.try_grant_promo_pet(ch, "pet_void_wisp")
    assert st2 == "dup"
