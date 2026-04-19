"""Построить key->zone для всех шаблонов из game/floors/monsters.py + long_floor."""
from __future__ import annotations

import ast
import pathlib

from game.floors import floor_data
from game.floors import long_floor as lf
from game.floors import monsters as m


def _pool_keys(zone: str) -> tuple[str, ...]:
    return tuple(t.key for t in m._pool(zone))  # noqa: SLF001


def main() -> None:
    zmap: dict[str, str] = {}
    for z in (*floor_data.ZONES, floor_data.ZONE_FINAL):
        for k in _pool_keys(z.key):
            zmap[k] = z.key
    for t in (lf.SPAWN_W1.template, lf.SPAWN_W2.template, lf.SPAWN_BOSS.template):
        zmap[t.key] = "long_floor_15"
    # minis
    for z in (*floor_data.ZONES, floor_data.ZONE_FINAL):
        mb = m.mini_boss_for_zone(z, z.floor_from)
        zmap[mb.key] = z.key
    # majors
    for z in floor_data.ZONES:
        bb = m.major_boss_for_zone(z, z.floor_from)
        zmap[bb.key] = z.key
    zmap[m.major_boss_for_zone(floor_data.ZONE_FINAL, 100).key] = floor_data.ZONE_FINAL_KEY

    print("KEY_TO_ZONE = {")
    for k in sorted(zmap):
        print(f"    {k!r}: {zmap[k]!r},")
    print("}")


if __name__ == "__main__":
    main()
