"""
Передышка: полное восстановление HP/MP через фиксированное время (реальные секунды).
"""

from __future__ import annotations

import time

from db.models.character import Character

REST_DURATION_SEC = 60
_META_KEY = "rest_until_ts"


def apply_completed_rest_if_needed(character: Character) -> bool:
    """
    Если срок передышки прошёл — восстановить HP/MP и снять таймер.
    Возвращает True, если было применено восстановление.
    """
    mp = dict(character.meta_progress or {})
    raw = mp.get(_META_KEY)
    if raw is None:
        return False
    try:
        until = float(raw)
    except (TypeError, ValueError):
        del mp[_META_KEY]
        character.meta_progress = mp
        return False
    if time.time() < until:
        return False
    character.hp_current = int(character.hp_max)
    character.mp_current = int(character.mp_max)
    del mp[_META_KEY]
    character.meta_progress = mp
    return True


def is_rest_in_progress(character: Character) -> bool:
    """Идёт ли отдых (таймер ещё не истёк). Сначала забирает готовый отдых, если время вышло."""
    apply_completed_rest_if_needed(character)
    mp = dict(character.meta_progress or {})
    raw = mp.get(_META_KEY)
    if raw is None:
        return False
    try:
        return time.time() < float(raw)
    except (TypeError, ValueError):
        return False


def rest_seconds_left(character: Character) -> int:
    """Секунд до конца передышки; 0 если отдыха нет."""
    mp = character.meta_progress or {}
    raw = mp.get(_META_KEY)
    if raw is None:
        return 0
    try:
        left = int(float(raw) - time.time())
    except (TypeError, ValueError):
        return 0
    return max(0, left)


def try_begin_or_claim_rest(character: Character) -> tuple[bool, str, float | None]:
    """
    Обработка кнопки «Передышка»:
    - таймер истёк → восстановить HP/MP;
    - таймер идёт → отказ с оставшимся временем;
    - таймера нет → начать новую передышку на REST_DURATION_SEC.

    Третье значение — Unix timestamp окончания новой передышки, если она только что
    начата; иначе None (для планирования уведомления).
    """
    if apply_completed_rest_if_needed(character):
        return (
            True,
            "HP и MP восстановлены до максимума.",
            None,
        )

    mp = dict(character.meta_progress or {})
    raw = mp.get(_META_KEY)
    now = time.time()
    if raw is not None:
        try:
            until = float(raw)
        except (TypeError, ValueError):
            until = 0.0
        if now < until:
            return False, f"Отдых… осталось {int(until - now)} с.", None

    # Учитываем бонус дома (−25% на ур.3+, −50% на ур.5)
    try:
        from services.home_service import home_rest_duration_sec
        duration = home_rest_duration_sec(character, REST_DURATION_SEC)
    except Exception:
        duration = REST_DURATION_SEC

    until_ts = now + duration
    mp[_META_KEY] = until_ts
    character.meta_progress = mp
    return (
        True,
        (
            f"Передышка! Через {duration} с HP и MP восстановятся до максимума — "
            "снова нажми кнопку или открой профиль."
        ),
        until_ts,
    )


def format_rest_status_line_html(character: Character) -> str:
    """Строка для карточки профиля (HTML)."""
    apply_completed_rest_if_needed(character)
    try:
        from services.home_service import home_rest_duration_sec
        duration_hint = home_rest_duration_sec(character, REST_DURATION_SEC)
    except Exception:
        duration_hint = REST_DURATION_SEC
    mp = character.meta_progress or {}
    raw = mp.get(_META_KEY)
    if raw is None:
        return (
            f"🛏️ <b>Передышка:</b> не активна — кнопка ниже ({duration_hint} с до полного HP/MP)."
        )
    try:
        until = float(raw)
    except (TypeError, ValueError):
        return "🛏️ <b>Передышка:</b> не активна — кнопка ниже."
    left = int(until - time.time())
    return f"🛏️ <b>Передышка:</b> отдых… <b>~{max(0, left)}</b> с до полного HP/MP."
