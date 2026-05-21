"""Шаблоны монстров из паков зон (после merge в MONSTER_TEMPLATE_META)."""

from __future__ import annotations

from game.data.monsters import MONSTER_TEMPLATE_META
from game.enemies.floors.spawns import MonsterTemplate

NAMED_ELITE_KEYS: tuple[str, ...] = (
    "sister_elis",
    "judge_noct",
    "baroneta_elite",
    "fang_pastor",
    "vamp_huntress",
)


def template_from_key(key: str) -> MonsterTemplate | None:
    mid = str(key or "").strip()
    if not mid or mid not in MONSTER_TEMPLATE_META:
        return None
    m = MONSTER_TEMPLATE_META[mid]
    name = str(m.get("display_name") or m.get("name") or mid)
    return MonsterTemplate(
        mid,
        name,
        str(m.get("emoji") or "👹"),
        str(m.get("element") or "dark"),
        str(m.get("blurb") or ""),
    )


def is_named_elite_key(key: str) -> bool:
    return str(key) in NAMED_ELITE_KEYS
