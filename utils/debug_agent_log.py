"""Однократные NDJSON-логи для сессии отладки (не логируем PII, только флаги/счётчики)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Несколько путей: бот часто запускают не из корня репозитория Cursor.
_HERE = Path(__file__).resolve()
_CANDIDATE_LOGS = [
    _HERE.parents[2] / "debug-da2934.log",  # родитель tower_bot
    _HERE.parents[1] / "debug-da2934.log",  # пакет tower_bot/
    Path.cwd() / "debug-da2934.log",
]
_SESSION = "da2934"
_INGEST = "http://127.0.0.1:7267/ingest/9d5e6738-e7ec-42f9-bf5b-da2916039369"
DEBUG_LOG = _CANDIDATE_LOGS[0]
SESSION_ID = _SESSION


def _write_file(line: str) -> None:
    for p in _CANDIDATE_LOGS:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
            return
        except OSError:
            continue


def _post_ingest(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        _INGEST,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Debug-Session-Id": _SESSION,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            resp.read()
    except (urllib.error.URLError, OSError, TimeoutError):
        pass


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
        "sessionId": _SESSION,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    _write_file(line)
    _post_ingest(payload)
    # #endregion
