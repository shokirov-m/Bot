"""
Копирует PNG в assets/images/profile/ как male_1..3 и female_1..3.

1) Если в папке-источнике есть male_1.png … female_3.png — копируются они.
2) Иначе: первые 6 файлов *.png по сортировке имени (как в проводнике).

Пример:
  python scripts/copy_profile_portraits.py "D:\\my_portraits"
  python scripts/copy_profile_portraits.py
     (источник по умолчанию: ~/.cursor/projects/c-Users-Shokirov-Desktop-100/assets)
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

DEST_NAMES = ("male_1", "male_2", "male_3", "female_1", "female_2", "female_3")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    dest_dir = root / "assets" / "images" / "profile"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) >= 2:
        src_dir = Path(sys.argv[1]).expanduser()
    else:
        src_dir = (
            Path.home()
            / ".cursor"
            / "projects"
            / "c-Users-Shokirov-Desktop-100"
            / "assets"
        )

    if not src_dir.is_dir():
        print(f"Нет папки: {src_dir}")
        print("Укажи путь: python scripts/copy_profile_portraits.py <папка_с_png>")
        return 1

    explicit: list[Path] = []
    for name in DEST_NAMES:
        p = src_dir / f"{name}.png"
        if p.is_file():
            explicit.append(p)

    if len(explicit) == 6:
        for name, src in zip(DEST_NAMES, explicit, strict=True):
            shutil.copy2(src, dest_dir / f"{name}.png")
            print(f"OK {src.name} -> {name}.png")
        return 0

    pngs = sorted(src_dir.glob("*.png"))
    if len(pngs) < 6:
        print(
            f"Нужно 6 PNG: либо положи male_1.png…female_3.png в {src_dir}, "
            f"либо любые 6 *.png (сейчас найдено {len(pngs)}).",
        )
        return 1

    for name, src in zip(DEST_NAMES, pngs[:6], strict=True):
        shutil.copy2(src, dest_dir / f"{name}.png")
        print(f"OK {src.name} -> {name}.png (по порядку имени файла)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
