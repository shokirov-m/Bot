"""
Удалить всех персонажей и связанные строки (инвентарь, прогресс этажей и т.д. по CASCADE).
Пользователи users остаются — можно снова пройти /start и создать героя.

Запуск из каталога tower_bot:
  python scripts/wipe_characters.py

Осторожно: без подтверждения. Сделай копию data/tower.db перед запуском.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from db.database import resolve_db_path  # noqa: E402


def main() -> None:
    p = resolve_db_path()
    if not p.exists():
        print(f"Файл БД не найден: {p}")
        return
    con = sqlite3.connect(str(p))
    try:
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.execute("SELECT COUNT(*) FROM characters").fetchone()
        n = int(cur[0]) if cur else 0
        con.execute("DELETE FROM characters")
        con.commit()
        print(f"Удалено персонажей: {n}. Файл: {p}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
