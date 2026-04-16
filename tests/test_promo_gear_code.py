"""Статический промокод с экипировкой в сумку."""

from game.promos import bag_payloads_for_code, reward_for_code


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
