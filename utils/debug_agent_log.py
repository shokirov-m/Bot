"""Однократные NDJSON-логи для сессии отладки (не логируем PII, только флаги/счётчики)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# Корень репозитория: .../tower_bot/utils -> parents[2] = папка с tower_bot; нам нужен родитель tower_bot
_PROJECT = Path(__file__).resolve().parents[2]
DEBUG_LOG = _PROJECT / "debug-da2934.log"
SESSION_ID = "da2934"


def log_debug(
    location: str,
    message: str,
    data: dict[str, Any],
    *,
    hypothesis_id: str,
    run_id: str = "pre",
) -> None:
    # #region agent log
    payload: dict[str, Any] = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # #endregion
