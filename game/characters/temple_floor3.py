"""
Храм призыва на 3 этаже: один бесплатный ритуал с до 3 перебросов (базовый пул питомцев).
Состояние в meta_progress['temple_f3_v1'].
"""

from __future__ import annotations

import random
from typing import Any

from db.models.character import Character

from game.characters import pets as pets_mod

META = "temple_f3_v1"
REROLLS_MAX = 3


def _meta(character: Character) -> tuple[dict[str, Any], dict[str, Any]]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META)
    if not isinstance(raw, dict):
        raw = {}
    return mp, raw


def _save(character: Character, mp: dict[str, Any], st: dict[str, Any]) -> None:
    mp[META] = st
    character.meta_progress = mp


def temple_normalize_legacy(character: Character) -> None:
    """Персонажи с питомцами до храма — помечаем ритуал как исчерпанный."""
    if not pets_mod.owned_keys(character):
        return
    mp, st = _meta(character)
    if st.get("completed"):
        return
    st = dict(st)
    st["completed"] = True
    st["session"] = None
    _save(character, dict(mp), st)


def temple_ritual_done(character: Character) -> bool:
    """Ритуал храма уже завершён (или есть питомцы с прошлой логики)."""
    _, st = _meta(character)
    if st.get("completed"):
        return True
    if pets_mod.owned_keys(character):
        return True
    return False


def _roll_basic() -> str:
    p = random.choice(list(pets_mod.PET_BASIC_POOL))
    return p.key


def ensure_temple_session(character: Character) -> dict[str, Any]:
    """Создать или вернуть активную сессию {candidate_key, rerolls_left}."""
    mp, st = _meta(character)
    if temple_ritual_done(character):
        return {}
    sess = st.get("session")
    if isinstance(sess, dict) and str(sess.get("candidate_key") or ""):
        return sess
    cand = _roll_basic()
    sess = {"candidate_key": cand, "rerolls_left": REROLLS_MAX}
    st = dict(st)
    st["session"] = sess
    _save(character, dict(mp), st)
    return sess


def temple_session(character: Character) -> dict[str, Any] | None:
    _, st = _meta(character)
    sess = st.get("session")
    if isinstance(sess, dict) and str(sess.get("candidate_key") or ""):
        return sess
    return None


def try_reroll(character: Character) -> tuple[bool, str]:
    if temple_ritual_done(character):
        return False, "Ритуал храма уже не действует."
    mp, st = _meta(character)
    sess = st.get("session")
    if not isinstance(sess, dict):
        return False, "Сначала зайди в храм."
    left = int(sess.get("rerolls_left", 0))
    if left <= 0:
        return False, "Перебросы закончились — прими дар или уйди."
    sess = dict(sess)
    sess["candidate_key"] = _roll_basic()
    sess["rerolls_left"] = left - 1
    st = dict(st)
    st["session"] = sess
    _save(character, dict(mp), st)
    return True, "Судьба дрогнула — новое видение."


def try_accept_temple_pet(character: Character) -> tuple[bool, str]:
    if temple_ritual_done(character):
        return False, "Уже нечего принимать."
    mp, st = _meta(character)
    sess = st.get("session")
    if not isinstance(sess, dict):
        return False, "Нет активного призыва."
    key = str(sess.get("candidate_key") or "")
    if not key:
        return False, "Пусто."
    defs = pets_mod._all_defs()
    if key not in defs:
        return False, "Неверный дар."
    chosen = defs[key]
    msg = pets_mod._apply_pet_pull_after_payment(character, chosen, cost_for_refund=0)
    st = dict(st)
    st["session"] = None
    st["completed"] = True
    _save(character, dict(mp), st)
    return True, msg


def abandon_session(character: Character) -> None:
    """Сбросить незавершённую сессию (например при выходе в город без принятия)."""
    mp, st = _meta(character)
    if st.get("completed"):
        return
    st = dict(st)
    st["session"] = None
    _save(character, dict(mp), st)
