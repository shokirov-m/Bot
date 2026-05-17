"""
Создаёт PNG-заглушки 1×1 во всех путях из assets/images/README.md.
Запуск: из папки tower_bot —  python scripts/generate_image_placeholders.py
"""

from __future__ import annotations

import base64
from pathlib import Path

# Минимальный валидный PNG 1×1 (красный пиксель — проверенный chunk)
_MIN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==",
)

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "images"

ZONE_KEYS = (
    "forest_beginnings",
    "rotten_swamps",
    "shadow_caves",
    "icy_peaks",
    "desert_oblivion",
    "volcanic_ruins",
    "sky_citadel",
    "chaos_abyss",
    "eternity_hall",
    "tower_warden",
    "default",
)


def main() -> None:
    loc = IMG / "locations"
    mon = IMG / "monsters"
    itm = IMG / "items"
    for d in (loc, mon, itm):
        d.mkdir(parents=True, exist_ok=True)
    for key in ZONE_KEYS:
        (loc / f"{key}.png").write_bytes(_MIN_PNG)
    (mon / "default.png").write_bytes(_MIN_PNG)
    (itm / "default.png").write_bytes(_MIN_PNG)
    print("OK:", IMG)


if __name__ == "__main__":
    main()
