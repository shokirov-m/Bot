"""Роли наёмников: базовые боевые статы (упрощённо для 1v1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MercenaryRoleDef:
    key: str
    name_ru: str
    base_hp: int
    base_atk: int
    is_tank: bool


ROLES: dict[str, MercenaryRoleDef] = {
    "tank": MercenaryRoleDef("tank", "Страж", 120, 12, True),
    "dd_phys": MercenaryRoleDef("dd_phys", "Наёмник клинка", 85, 22, False),
    "dd_mag": MercenaryRoleDef("dd_mag", "Чародей тени", 70, 24, False),
    "healer": MercenaryRoleDef("healer", "Целитель", 90, 14, False),
    "hybrid": MercenaryRoleDef("hybrid", "Универсал", 95, 18, False),
}


def role_def(key: str) -> MercenaryRoleDef:
    return ROLES.get(key, ROLES["dd_phys"])
