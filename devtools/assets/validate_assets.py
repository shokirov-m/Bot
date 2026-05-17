"""Проверка наличия PNG по путям из кода. Запуск из tower_bot/: python devtools/assets/validate_assets.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from game.core.paths import assets_root, game_art_root, images_root, ui_assets_root

    roots = {
        "assets": assets_root(),
        "game_art": game_art_root(),
        "images": images_root(),
        "ui": ui_assets_root(),
    }
    missing: list[str] = []

    try:
        from utils.media import game_art

        for name in (
            "menu_locations_photo_path",
            "menu_city_photo_path",
            "menu_shop_photo_path",
        ):
            fn = getattr(game_art, name, None)
            if callable(fn):
                p = fn()
                if p and not Path(p).is_file():
                    missing.append(p)
    except Exception as exc:
        print("warn: game_art scan skipped:", exc)

    print("Asset roots:")
    for label, p in roots.items():
        print(f"  {label}: {p} ({'ok' if p.is_dir() else 'MISSING DIR'})")

    if missing:
        print(f"\nMissing files ({len(missing)}):")
        for m in missing[:40]:
            print(" ", m)
        if len(missing) > 40:
            print(f"  ... and {len(missing) - 40} more")
        return 1

    print("\nNo critical missing paths in sample scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
