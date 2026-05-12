"""Разложить assets/monsters/*.png по подпапкам зон (KEY_TO_ZONE). Запуск: python scripts/move_monsters_into_zone_folders.py"""
from __future__ import annotations
import shutil
from pathlib import Path
from game.data.monsters import KEY_TO_ZONE

def main() -> None:
    root = Path(__file__).resolve().parent.parent / "assets" / "monsters"
    if not root.is_dir():
        raise SystemExit(f"Missing {root}")

    def move_file(src: Path, dst: Path) -> None:
        if not src.is_file():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.resolve() == src.resolve():
            return
        if dst.is_file():
            if src.parent == root:
                src.unlink()
            return
        shutil.move(str(src), str(dst))

    for f in list(root.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".png":
            continue
        if f.parent != root:
            continue
        if f.name == "default.png":
            continue
        stem = f.stem
        template_key = "golden_goblin" if stem == "golden" else stem
        zone = KEY_TO_ZONE.get(template_key)
        if zone is None:
            continue
        move_file(f, root / zone / f.name)

    move_file(root / "wolf.png", root / "forest_beginnings" / "timber_wolf.png")
    move_file(root / "snake.png", root / "rotten_swamps" / "snake.png")
    move_file(root / "wyvern.png", root / "sky_citadel" / "wyvern.png")
    move_file(root / "thorn_lurker.png", root / "shadow_caves" / "thorn_lurker.png")
    print("OK")

if __name__ == "__main__":
    main()
