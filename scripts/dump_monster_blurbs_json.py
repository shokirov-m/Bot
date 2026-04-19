"""Blurbs теперь в ``monsters_catalog.json`` — делегирует ``dump_monster_meta_json.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> None:
    p = Path(__file__).with_name("dump_monster_meta_json.py")
    spec = importlib.util.spec_from_file_location("_monster_meta_dump", p)
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(mod)
    mod.main()


if __name__ == "__main__":
    main()
