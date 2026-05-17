"""Синхронизирует display_name, emoji, element, blurb из AST (MonsterTemplate) в ``monsters_catalog.json``."""
from __future__ import annotations

import ast
import json
import pathlib


def _scan(path: pathlib.Path) -> dict[str, dict[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    meta: dict[str, dict[str, str]] = {}

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name) and node.func.id == "MonsterTemplate":
                args = node.args
                if len(args) >= 5:
                    k, nm, emo, el, bl = args[:5]
                    if all(isinstance(a, ast.Constant) for a in (k, nm, emo, el, bl)):
                        meta[str(k.value)] = {
                            "display_name": str(nm.value),
                            "emoji": str(emo.value),
                            "element": str(el.value),
                            "blurb": str(bl.value),
                        }
            self.generic_visit(node)

    V().visit(tree)
    return meta


def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    catalog_path = root / "game" / "data" / "monsters_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    scanned: dict[str, dict[str, str]] = {}
    scanned.update(_scan(root / "game" / "floors" / "monsters.py"))
    scanned.update(_scan(root / "game" / "floors" / "long_floor.py"))
    monsters = catalog.setdefault("monsters", {})
    for key, meta in scanned.items():
        if key not in monsters:
            continue
        entry = monsters[key]
        entry["display_name"] = meta["display_name"]
        entry["emoji"] = meta["emoji"]
        entry["element"] = meta["element"]
        entry["blurb"] = meta["blurb"]
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Обновлено шаблонов в каталоге: {len(scanned)} → {catalog_path}")


if __name__ == "__main__":
    main()
