from __future__ import annotations

import base64
from pathlib import Path


def _tiny_png_bytes() -> bytes:
    # 1x1 transparent PNG
    return base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/at6wY4AAAAASUVORK5CYII="
    )


def main() -> int:
    root = Path(__file__).resolve().parent
    out_dir = root / "assets" / "game_art" / "materials"
    out_dir.mkdir(parents=True, exist_ok=True)

    from game.items.craft_resources import RESOURCE_DEFS

    created = 0
    skipped = 0
    png = _tiny_png_bytes()

    for rid in sorted(RESOURCE_DEFS.keys()):
        p = out_dir / f"{rid}.png"
        if p.is_file():
            skipped += 1
            continue
        p.write_bytes(png)
        created += 1

    print(f"materials placeholders: created={created} skipped={skipped} dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

