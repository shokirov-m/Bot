"""
PNG-заглушки для всех шаблонов монстров (stdlib, без Pillow).

Единый каталог ``assets/monsters/{key}.png`` — и бой (monster_portraits), и monster_image_for_template().

Запуск из каталога tower_bot:
  python -m scripts.generate_monster_placeholder_pngs
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

from game.floors import floor_data as fd
from game.floors import monsters as mf

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
    """Ключ шаблона → стихия (для цвета)."""
    out: dict[str, str | None] = {}

    def reg(t: mf.MonsterTemplate) -> None:
        out[t.key] = t.element

    for z in fd.ZONES:
        for t in mf.zone_monster_templates(z.key):
            reg(t)
    for t in mf.zone_monster_templates(fd.ZONE_FINAL.key):
        reg(t)

    for z in fd.ZONES:
        reg(mf.mini_boss_for_zone(z, z.floor_from))
        reg(mf.major_boss_for_zone(z, z.floor_from))

    reg(mf.mini_boss_for_zone(fd.ZONE_FINAL, 100))
    reg(mf.major_boss_for_zone(fd.ZONE_FINAL, 100))

    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    meta = collect_monster_keys_and_elements()
    mon_dir = root / "assets" / "monsters"
    for key in sorted(meta.keys()):
        el = meta[key]
        _write_monster_png(mon_dir / f"{key}.png", key, el)
        print(key)

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
    default_path.write_bytes(_png_rgb(128, 128, rows))
    print("default.png")


if __name__ == "__main__":
    main()
