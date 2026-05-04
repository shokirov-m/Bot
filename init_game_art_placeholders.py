#!/usr/bin/env python3
"""Run from project root: python init_game_art_placeholders.py — PNG stubs in assets/game_art/."""

from __future__ import annotations

from pathlib import Path

_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
    b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00"
    b"\x03\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

_ROOT = Path(__file__).resolve().parent / "assets" / "game_art"

_MENU_FILES = [
    "locations.png", "quests.png", "daily.png", "portal.png", "leaderboard.png",
    "auction.png", "titles.png", "clan.png", "city.png", "arena.png",
    "settings.png", "shop.png", "shop_vip.png", "workshop.png",
    "workshop_orders.png", "home.png", "home_wardrobe.png", "home_library.png",
    "coliseum.png",
]
_NPC_KEYS = [
    "scribe", "herbalist", "tavern_keeper", "temple", "market", "bank",
    "quest_giver", "city_guide", "wandering_trader",
]


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_bytes(_MIN_PNG)


def main() -> None:
    for name in _MENU_FILES:
        _touch(_ROOT / "menus" / name)
    for k in _NPC_KEYS:
        _touch(_ROOT / "npc" / f"{k}.png")
    for n in range(1, 51):
        _touch(_ROOT / "coliseum" / "fighters" / f"{n}.png")
    print("OK:", _ROOT)


if __name__ == "__main__":
    main()
