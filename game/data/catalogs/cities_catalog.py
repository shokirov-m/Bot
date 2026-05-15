"""Загрузка городов-хабов из cities_hubs.json."""

from __future__ import annotations

from game.data.catalogs._loader import load_catalog_json
from game.locations.cities import CityHubDef


def catalog_city_hubs() -> dict[int, CityHubDef] | None:
    raw = load_catalog_json("cities_hubs.json")
    hubs = raw.get("hubs")
    if not isinstance(hubs, list) or not hubs:
        return None
    out: dict[int, CityHubDef] = {}
    for row in hubs:
        if not isinstance(row, dict):
            continue
        try:
            fl = int(row["floor"])
        except (KeyError, TypeError, ValueError):
            continue
        out[fl] = CityHubDef(
            key=str(row.get("key", f"hub_{fl}")),
            tagline=str(row.get("tagline", "")),
            welcome_html=str(row.get("welcome_html", "")),
            retention_note=str(row.get("retention_note", "")),
            npc_guard_title=str(row.get("npc_guard_title", "стражник")),
            economy_blurb=str(row.get("economy_blurb", "")),
        )
    return out if out else None


def catalog_hub_key_by_floor() -> dict[int, str] | None:
    raw = load_catalog_json("cities_hubs.json")
    m = raw.get("hub_key_by_floor")
    if not isinstance(m, dict):
        return None
    out: dict[int, str] = {}
    for k, v in m.items():
        try:
            out[int(k)] = str(v)
        except (TypeError, ValueError):
            continue
    return out if out else None
