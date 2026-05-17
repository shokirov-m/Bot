"""
PNG-заглушки для всех монстров из ``game/data/monsters_catalog.json`` (stdlib, без Pillow).

Единый каталог ``assets/monsters/{key}.png`` — бой и ``monster_image_for_template()``.

Запуск из каталога tower_bot:
  python -m scripts.generate_monster_placeholder_pngs            # только отсутствующие
  python -m scripts.generate_monster_placeholder_pngs --force  # пересобрать все из каталога
  python -m scripts.generate_monster_placeholder_pngs --prune  # удалить *.png, которых нет в JSON
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import zlib
from pathlib import Path

from game.data.monsters import ALL_MONSTERS

W = H = 400

# Верх / низ градиента по стихии (приблизительно)
_ELEM_TOP: dict[str, tuple[int, int, int]] = {
    "fire": (255, 130, 70),
    "ice": (170, 220, 255),
    "lightning": (255, 245, 160),
    "dark": (90, 70, 120),
    "light": (255, 252, 230),
    "earth": (150, 130, 95),
    "poison": (120, 190, 110),
}


def _png_rgb(w: int, h: int, rows: list[bytes]) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _colors_for_key(element: str | None, key: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    el = (element or "earth").strip().lower()
    top = _ELEM_TOP.get(el)
    if top is None:
        h = hashlib.sha256(key.encode("utf-8")).digest()
        top = (int(h[0]), int(h[1]), int(h[2]))
    bot = tuple(max(0, int(c * 0.42)) for c in top)
    return top, bot


def _write_monster_png(path: Path, key: str, element: str | None) -> None:
    top, bot = _colors_for_key(element, key)
    rows: list[bytes] = []
    for y in range(H):
        t = y / max(H - 1, 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        rows.append(bytes([r, g, b]) * W)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png_rgb(W, H, rows))


def collect_monster_keys_and_elements() -> dict[str, str | None]:
    """Ключ из каталога → стихия (для цвета градиента)."""
    out: dict[str, str | None] = {}
    for key, row in ALL_MONSTERS.items():
        el = row.get("element")
        out[key] = str(el) if el is not None else "earth"
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Синхронизация PNG с monsters_catalog.json")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующие PNG (по умолчанию создаются только отсутствующие)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Удалить в assets/monsters PNG, ключа которого нет в monsters_catalog",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    meta = collect_monster_keys_and_elements()
    mon_dir = root / "assets" / "monsters"
    created = 0
    skipped = 0
    for key in sorted(meta.keys()):
        path = mon_dir / f"{key}.png"
        if path.is_file() and not args.force:
            skipped += 1
            continue
        _write_monster_png(path, key, meta[key])
        created += 1
        print(key)

    print(f"Создано/обновлено: {created}, пропущено (уже есть): {skipped}")

    if args.prune:
        allowed = set(meta.keys()) | {"default"}
        removed = 0
        for p in mon_dir.glob("*.png"):
            if p.stem not in allowed:
                p.unlink()
                removed += 1
                print(f"remove {p.name}")
        if removed:
            print(f"Удалено лишних: {removed}")

    # Заглушка по ключу без файла — fallback для monster_image_for_template
    default_top = (70, 75, 85)
    default_bot = (28, 30, 35)
    rows: list[bytes] = []
    for y in range(128):
        t = y / 127
        r = int(default_top[0] + (default_bot[0] - default_top[0]) * t)
        g = int(default_top[1] + (default_bot[1] - default_top[1]) * t)
        b = int(default_top[2] + (default_bot[2] - default_top[2]) * t)
        rows.append(bytes([r, g, b]) * 128)
    default_path = mon_dir / "default.png"
    default_path.parent.mkdir(parents=True, exist_ok=True)
    if not default_path.is_file() or args.force:
        default_path.write_bytes(_png_rgb(128, 128, rows))
        print("default.png")


if __name__ == "__main__":
    main()
