"""Городские хабы 91xx: якорь в callback, get_city_for_floor, покупки."""

from __future__ import annotations

from game.tower.progression import floor_data


class _FakeCharacter:
    __slots__ = ("floor_number", "highest_floor_reached", "meta_progress", "gold")

    def __init__(
        self,
        *,
        floor_number: int = 9130,
        highest_floor_reached: int = 35,
    ) -> None:
        self.floor_number = floor_number
        self.highest_floor_reached = highest_floor_reached
        self.meta_progress: dict = {"hub_return_floor_v1": 32}
        self.gold = 50_000


def test_city_service_floor_ok_on_hub() -> None:
    ch = _FakeCharacter(floor_number=9130, highest_floor_reached=35)
    assert floor_data.city_service_floor_ok(ch, 30) is True  # type: ignore[arg-type]
    assert floor_data.city_service_floor_ok(ch, 9130) is True  # legacy callback
    assert floor_data.city_service_floor_ok(ch, 60) is False  # type: ignore[arg-type]


def test_get_city_for_hub_floor() -> None:
    city = floor_data.get_city_for_floor(9130, highest_reached=35)
    assert city is not None
    assert int(city.after_floor) == 30


def test_normalize_city_callback_key() -> None:
    assert floor_data.normalize_city_callback_key(9130) == 30
    assert floor_data.normalize_city_callback_key(30) == 30


def test_city_callback_key() -> None:
    ch = _FakeCharacter(floor_number=9130)
    assert floor_data.city_callback_key(ch) == 30  # type: ignore[arg-type]


def test_economy_pricing_floor_on_hub() -> None:
    ch = _FakeCharacter(floor_number=9130, highest_floor_reached=35)
    assert floor_data.economy_pricing_floor(ch) == 32  # type: ignore[arg-type]


def test_shop_buy_floor_check_uses_anchor() -> None:
    import asyncio

    from services.economy import shop_service

    ch = _FakeCharacter(floor_number=9130, highest_floor_reached=35)

    async def _run() -> tuple[bool, str]:
        return await shop_service.try_buy_good(
            None,  # type: ignore[arg-type]
            ch,  # type: ignore[arg-type]
            "nonexistent_key_xyz",
            expected_floor=30,
        )

    ok, msg = asyncio.get_event_loop().run_until_complete(_run())
    assert ok is False
    assert msg != "Ты не на этом этаже."
