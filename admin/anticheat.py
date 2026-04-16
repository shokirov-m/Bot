"""
Правила детекции: скорость боёв, экономика, урон, скачки по этажам.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Пороги (легко менять)
SPEED_MAX_FIGHTS_PER_10S = 3
ECONOMY_MAX_GOLD_GAIN_PER_HOUR = 100_000
DAMAGE_MAX_MULTIPLIER = 5.0
# Запас на силу навыка, крит и боевые модификаторы (укус в спину, низкое HP и т.д.)
SKILL_DAMAGE_COMBO_MULT = 3.5
PROGRESS_MAX_FLOOR_JUMP_PER_MINUTE = 3


@dataclass
class AnticheatAlert:
    severity: str  # INFO / ALERT / CRITICAL
    check_type: str  # speed / economy / damage / progress
    telegram_id: int
    username: str | None
    floor: int
    level: int
    description: str
    value: Any
    expected_max: Any
    timestamp: datetime

    def to_payload(self) -> dict[str, Any]:
        return {
            "check_type": self.check_type,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "floor": self.floor,
            "level": self.level,
            "description": self.description,
            "value": self.value,
            "expected_max": self.expected_max,
            "timestamp": self.timestamp.isoformat(),
        }


def check_fight_speed(
    fights_in_last_10s: int,
    *,
    telegram_id: int,
    username: str | None,
    floor: int,
    level: int,
) -> AnticheatAlert | None:
    if fights_in_last_10s < SPEED_MAX_FIGHTS_PER_10S:
        return None
    return AnticheatAlert(
        severity="ALERT",
        check_type="speed",
        telegram_id=telegram_id,
        username=username,
        floor=floor,
        level=level,
        description="Слишком частые старты боя (< 10 с)",
        value=fights_in_last_10s,
        expected_max=SPEED_MAX_FIGHTS_PER_10S - 1,
        timestamp=datetime.now(UTC),
    )


def check_gold_gain(
    gold_gained: int,
    *,
    telegram_id: int,
    username: str | None,
    floor: int,
    level: int,
) -> AnticheatAlert | None:
    if gold_gained <= ECONOMY_MAX_GOLD_GAIN_PER_HOUR:
        return None
    sev = "CRITICAL" if gold_gained > ECONOMY_MAX_GOLD_GAIN_PER_HOUR * 2 else "ALERT"
    return AnticheatAlert(
        severity=sev,
        check_type="economy",
        telegram_id=telegram_id,
        username=username,
        floor=floor,
        level=level,
        description="Аномальный прирост золота за час",
        value=gold_gained,
        expected_max=ECONOMY_MAX_GOLD_GAIN_PER_HOUR,
        timestamp=datetime.now(UTC),
    )


def check_damage_value(
    damage: int,
    *,
    strength: int,
    weapon_atk: int,
    telegram_id: int,
    username: str | None,
    floor: int,
    level: int,
) -> AnticheatAlert | None:
    """Урон выше (СИЛ*2 + оружие) * 1.15 * DAMAGE_MAX_MULTIPLIER — подозрительно."""
    base = int(strength) * 2 + int(weapon_atk)
    ceiling = max(50, int(base * 1.15 * DAMAGE_MAX_MULTIPLIER))
    if damage <= ceiling:
        return None
    return AnticheatAlert(
        severity="CRITICAL",
        check_type="damage",
        telegram_id=telegram_id,
        username=username,
        floor=floor,
        level=level,
        description="Невозможный урон за один удар (физ.)",
        value=damage,
        expected_max=ceiling,
        timestamp=datetime.now(UTC),
    )


def check_skill_damage_value(
    damage: int,
    *,
    kind: str,
    strength: int,
    intelligence: int,
    weapon_atk: int,
    skill_power: float,
    telegram_id: int,
    username: str | None,
    floor: int,
    level: int,
) -> AnticheatAlert | None:
    """Потолок урона по навыку: база как в движке × сила навыка × запас под крит/модификаторы."""
    w = int(weapon_atk)
    sp = max(float(skill_power), 0.1)
    if kind == "mag":
        focus = max(2, w // 2)
        base = int(intelligence) * 2 + focus
        label = "маг. навык"
    else:
        base = int(strength) * 2 + w
        label = "физ. навык"
    ceiling = max(
        80,
        int(base * 1.15 * DAMAGE_MAX_MULTIPLIER * sp * SKILL_DAMAGE_COMBO_MULT),
    )
    if damage <= ceiling:
        return None
    return AnticheatAlert(
        severity="CRITICAL",
        check_type="damage_skill",
        telegram_id=telegram_id,
        username=username,
        floor=floor,
        level=level,
        description=f"Невозможный урон за один навык ({label})",
        value=damage,
        expected_max=ceiling,
        timestamp=datetime.now(UTC),
    )


def check_floor_progress(
    old_floor: int,
    new_floor: int,
    time_delta_seconds: float,
    *,
    telegram_id: int,
    username: str | None,
    floor: int,
    level: int,
) -> AnticheatAlert | None:
    if new_floor <= old_floor or time_delta_seconds <= 0:
        return None
    jump = new_floor - old_floor
    per_min = jump / (time_delta_seconds / 60.0)
    if per_min <= PROGRESS_MAX_FLOOR_JUMP_PER_MINUTE:
        return None
    return AnticheatAlert(
        severity="ALERT",
        check_type="progress",
        telegram_id=telegram_id,
        username=username,
        floor=floor,
        level=level,
        description="Слишком быстрый подъём по этажам",
        value=round(per_min, 2),
        expected_max=PROGRESS_MAX_FLOOR_JUMP_PER_MINUTE,
        timestamp=datetime.now(UTC),
    )
