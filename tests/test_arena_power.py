from services.arena_service import _arena_power


def test_arena_power_numeric() -> None:
    p = _arena_power(strength=10, dexterity=5, level=3, floor_number=7, weapon_attack=8)
    assert p == 10 * 3 + 5 * 2 + 3 * 5 + 7 * 1.5 + 8 * 1.2
