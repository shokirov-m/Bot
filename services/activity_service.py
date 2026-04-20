"""
Учёт активности игрока для админки: последнее действие и оценка времени в игре (meta_progress).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from db.models.character import Character

META_ACTIVITY = "activity_v1"
# Не более стольки секунд «игры» между двумя событиями за один интервал (анти-накрутка при долгом AFK).
_MAX_DELTA_SEC = 12 * 60
# Игнорировать разрывы длиннее этого — как новый заход (не прибавляем часы простоя).
_MAX_GAP_FOR_COUNT = 48 * 3600


def record_interaction(character: Character) -> None:
    """Вызывать при каждом входящем апдейте от игрока с персонажем (после регистрации)."""
    mp = dict(character.meta_progress or {})
    act: dict[str, Any] = dict(mp.get(META_ACTIVITY) or {})
    now = time.time()
    last_raw = act.get("last_ts")
    play = int(act.get("play_sec", 0) or 0)

    if isinstance(last_raw, (int, float)):
        delta = now - float(last_raw)
        if 0 < delta <= _MAX_GAP_FOR_COUNT:
            play += int(min(delta, _MAX_DELTA_SEC))

    act["last_ts"] = now
    act["play_sec"] = max(0, play)
    act["last_iso"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    mp[META_ACTIVITY] = act
    character.meta_progress = mp


def activity_admin_lines(character: Character) -> dict[str, Any]:
    """Поля для карточки админки."""
    mp = character.meta_progress or {}
    act = mp.get(META_ACTIVITY) if isinstance(mp.get(META_ACTIVITY), dict) else {}
    play_sec = int(act.get("play_sec", 0) or 0)
    last_iso = act.get("last_iso")
    last_ts = act.get("last_ts")
    return {
        "play_sec": play_sec,
        "last_activity_iso": str(last_iso) if last_iso else None,
        "last_ts": float(last_ts) if isinstance(last_ts, (int, float)) else None,
    }


def format_duration_ru(total_sec: int) -> str:
    """Человекочитаемая длительность."""
    s = max(0, int(total_sec))
    if s < 60:
        return f"{s} с"
    m = s // 60
    if m < 60:
        return f"{m} мин"
    h, rem = divmod(m, 60)
    if h < 48:
        return f"{h} ч {rem} мин"
    d, rh = divmod(h, 24)
    return f"{d} дн. {rh} ч"


def format_dt_utc(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%d %H:%M UTC")
