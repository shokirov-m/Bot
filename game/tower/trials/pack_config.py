"""Чтение конфигов испытаний из JSON-паков зон."""

from __future__ import annotations

from typing import Any

from game.data.packs import trial_for_floor
from game.tower.progression import floor_data
from game.tower.trials.default_config import (
    build_default_trial_config,
    is_trial_eligible_floor,
)


def get_trial_config(floor_number: int) -> dict[str, Any]:
    from game.tower.trials.boss_chambers import apply_boss_chamber_trial, is_boss_floor

    fl = int(floor_number)
    if not is_trial_eligible_floor(fl):
        return {}
    zone = floor_data.get_zone_for_floor(fl)
    cfg = trial_for_floor(zone.key, fl)
    if not str(cfg.get("trial_type") or "").strip():
        cfg = build_default_trial_config(fl, zone)
    if is_boss_floor(fl):
        cfg = apply_boss_chamber_trial(fl, cfg)
    return cfg


def trial_type_for_floor(floor_number: int) -> str:
    cfg = get_trial_config(floor_number)
    return str(cfg.get("trial_type") or "")


def trial_grounds_count(floor_number: int) -> int:
    cfg = get_trial_config(floor_number)
    return int(cfg.get("grounds_count") or 0)


def format_trial_progress_line(floor_number: int, *, progress_pct: int | None = None) -> str:
    cfg = get_trial_config(floor_number)
    if not cfg:
        return ""
    ttype = str(cfg.get("trial_type") or "trial")
    labels = {
        "hunt": "Охота",
        "search": "Поиск",
        "rescue": "Спасение",
        "capture": "Захват",
        "defense": "Оборона",
        "escort": "Эскорт",
        "ritual": "Ритуал",
    }
    name = labels.get(ttype, ttype)
    grounds = int(cfg.get("grounds_count") or 0)
    pct = progress_pct if progress_pct is not None else int(cfg.get("progress_default") or 0)
    line = f"⚔️ <b>Испытание:</b> {name}"
    if grounds:
        line += f" · угодий <b>{grounds}</b>"
    if pct:
        line += f" · прогресс <b>{pct}%</b>"
    hard = cfg.get("hardcore")
    if hard:
        line += " · <i>хардкор</i>"
    return line
