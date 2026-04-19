"""Одноразово: вытащить key->blurb из game/floors/monsters.py."""
from __future__ import annotations

import ast
import pathlib


def main() -> None:
    path = pathlib.Path(__file__).resolve().parents[1] / "game" / "floors" / "monsters.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    blurbs: dict[str, str] = {}

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name) and node.func.id == "MonsterTemplate":
                args = node.args
                if len(args) >= 5:
                    k = args[0]
                    bl = args[4]
                    if isinstance(k, ast.Constant) and isinstance(bl, ast.Constant):
                        blurbs[str(k.value)] = str(bl.value)
            self.generic_visit(node)

    V().visit(tree)
    print(len(blurbs))
    for k in sorted(blurbs):
        print(repr(k), repr(blurbs[k]))


if __name__ == "__main__":
    main()
