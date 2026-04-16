"""
Ночной режим (22:00–06:00 UTC): сильнее монстры, выше золото и опыт.
"""

from __future__ import annotations

from datetime import UTC, datetime

# +20% к HP и атаке врага; +40% к золоту и опыту за победу (до титулов / штрафов).
MONSTER_STATS_MULT = 1.2
REWARD_MULT = 1.4


def is_night_utc_at_hour(hour: int) -> bool:
    """0–23, для тестов без подмены часов."""
    return hour >= 22 or hour < 6


def is_night_utc() -> bool:
    return is_night_utc_at_hour(datetime.now(UTC).hour)


def apply_night_to_monster_bundle(monster: dict) -> None:
    """Пересчитать hp/max_hp/atk на месте."""
    m = MONSTER_STATS_MULT
    hp = max(1, int(int(monster["hp"]) * m))
    monster["hp"] = hp
    monster["max_hp"] = hp
    monster["atk"] = max(1, int(int(monster["atk"]) * m))
