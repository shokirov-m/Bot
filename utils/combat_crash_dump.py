"""
Запись дампа сбоя боя на диск: тип/сообщение исключения, действие, трассировка
и последнее известное combat_state. Помогает быстро находить причину сбоев,
которые иначе видны только как «состояние сброшено».

Файлы пишутся в logs/combat_crashes/ относительно корня tower_bot.
Хранится не более CRASH_KEEP последних файлов.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path
from typing import Any

from loguru import logger

CRASH_DIR = Path(__file__).resolve().parent.parent / "logs" / "combat_crashes"
CRASH_KEEP = 50


def _make_safe(value: Any, depth: int = 0) -> Any:
    """Сделать значение JSON-сериализуемым (обрезаем глубину и кастуем экзотику в str)."""
    if depth > 6:
        return f"<truncated:{type(value).__name__}>"
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in list(value.items())[:200]:
            try:
                out[str(k)] = _make_safe(v, depth + 1)
            except Exception:
                out[str(k)] = f"<unsafe:{type(v).__name__}>"
        return out
    if isinstance(value, (list, tuple, set)):
        return [_make_safe(v, depth + 1) for v in list(value)[:200]]
    try:
        return str(value)
    except Exception:
        return f"<unrepr:{type(value).__name__}>"


def write_crash_dump(
    *,
    exc: BaseException,
    action: str | None = None,
    skill_index: int | None = None,
    item_id: int | None = None,
    user_id: int | None = None,
    character_id: int | None = None,
    combat_state: dict[str, Any] | None = None,
) -> Path | None:
    try:
        CRASH_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("combat crash dump: не удалось создать каталог логов")
        return None

    payload: dict[str, Any] = {
        "ts": int(time.time()),
        "exc_type": type(exc).__name__,
        "exc_msg": str(exc),
        "traceback": traceback.format_exc(),
        "action": action,
        "skill_index": skill_index,
        "item_id": item_id,
        "user_id": user_id,
        "character_id": character_id,
        "combat_state": _make_safe(combat_state) if combat_state is not None else None,
    }

    name = f"combat_crash_{int(payload['ts'])}_{type(exc).__name__}.json"
    path = CRASH_DIR / name
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.warning("combat crash dump записан: {}", path)
    except Exception:
        logger.exception("combat crash dump: запись на диск не удалась")
        return None

    try:
        files = sorted(CRASH_DIR.glob("combat_crash_*.json"), key=lambda p: p.stat().st_mtime)
        for old in files[:-CRASH_KEEP]:
            try:
                old.unlink()
            except OSError:
                continue
    except Exception:
        pass
    return path
