# -*- coding: utf-8 -*-
"""Fill empty dialog fields in monsters_catalog.json. Run: python scripts/seed_monster_dialog.py"""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
CATALOG = ROOT / "game" / "data" / "monsters_catalog.json"
def _name(entry):
    return str(entry.get("display_name") or entry.get("name") or entry.get("id") or "враг").strip()
def main():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    monsters = data.get("monsters") or {}
    n_open = n_vict = n_def = 0
    for mid, entry in monsters.items():
        if not isinstance(entry, dict): continue
        name = _name(entry)
        blurb = str(entry.get("blurb") or "").strip()
        if not str(entry.get("opening_phrase") or "").strip():
            entry["opening_phrase"] = blurb or f"«{name}» выходит навстречу — бой начинается."
            n_open += 1
        if not str(entry.get("victory_phrase") or "").strip():
            entry["victory_phrase"] = f"«{name}» повержен. Трибуна запомнит этот удар."
            n_vict += 1
        if not str(entry.get("defeat_phrase") or "").strip():
            entry["defeat_phrase"] = f"«{name}» одерживает верх… на этот раз."
            n_def += 1
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"opening +{n_open}, victory +{n_vict}, defeat +{n_def}")
if __name__ == "__main__": main()
