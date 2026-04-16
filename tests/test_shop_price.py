from game.economy.shop import effective_good_price


def test_effective_price_floor_1() -> None:
    assert effective_good_price(100, 1) == 102


def test_effective_price_cap_at_50() -> None:
    p60 = effective_good_price(100, 60)
    p50 = effective_good_price(100, 50)
    assert p60 == p50 == 175  # 100 * (1 + 50 * 0.015)
