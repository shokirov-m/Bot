"""Дневной лимит вылазок и стоимость стамины на испытаниях (из JSON пака)."""

from __future__ import annotations

from datetime import date
from typing import Any

from db.models.character import Character
from game.tower.trials.pack_config import get_trial_config

_META_VENTURES = "trial_ventures_v1"


def _venture_cfg(cfg: dict[str, Any]) -> tuple[int, int]:
    """(stamina_per_fight, daily_cap). 0 cap = без лимита."""
    cost = max(1, int(cfg.get("stamina_per_venture") or 1))
    cap = max(0, int(cfg.get("daily_venture_cap") or 0))
    return cost, cap


def stamina_cost_for_trial_fight(character: Character) -> int:
    cfg = get_trial_config(int(character.floor_number))
    cost, _ = _venture_cfg(cfg)
    return cost


def daily_cap_for_floor(floor: int) -> int:
    cfg = get_trial_config(int(floor))
    _, cap = _venture_cfg(cfg)
    return cap


def _ventures_meta(character: Character) -> dict[str, Any]:
    raw = (character.meta_progress or {}).get(_META_VENTURES)
    return dict(raw) if isinstance(raw, dict) else {}


def _save_ventures_meta(character: Character, data: dict[str, Any]) -> None:
    meta = dict(character.meta_progress or {})
    meta[_META_VENTURES] = data
    character.meta_progress = meta


def ventures_used_today(character: Character, floor: int | None = None) -> int:
    fl = int(floor if floor is not None else character.floor_number)
    today = date.today().isoformat()
    root = _ventures_meta(character)
    day_row = root.get(today)
    if not isinstance(day_row, dict):
        return 0
    return max(0, int(day_row.get(str(fl), 0) or 0))


def record_venture(character: Character) -> None:
    fl = int(character.floor_number)
    today = date.today().isoformat()
    root = dict(_ventures_meta(character))
    day_row = dict(root.get(today) or {})
    day_row[str(fl)] = max(0, int(day_row.get(str(fl), 0) or 0)) + 1
    root[today] = day_row
    # Храним только последние 7 дней
    keys = sorted(root.keys())[-7:]
    root = {k: root[k] for k in keys}
    _save_ventures_meta(character, root)


def check_can_fight(character: Character) -> tuple[bool, str]:
    """Перед боем на испытании: лимит вылазок и стамина."""
    fl = int(character.floor_number)
    cfg = get_trial_config(fl)
    cost, cap = _venture_cfg(cfg)
    if cap > 0:
        used = ventures_used_today(character, fl)
        if used >= cap:
            return (
                False,
                f"Лимит вылазок на сегодня: <b>{cap}</b>. Вернись завтра или в Эмберхолл.",
            )
    need_st = cost
    if int(character.stamina or 0) < need_st:
        return False, f"Нужно <b>{need_st}</b> ⚡ для вылазки (сейчас {int(character.stamina or 0)})."
    return True, ""


def format_venture_line_html(character: Character) -> str:
    fl = int(character.floor_number)
    cfg = get_trial_config(fl)
    cost, cap = _venture_cfg(cfg)
    if cap <= 0 and cost <= 1:
        return ""
    used = ventures_used_today(character, fl)
    cap_txt = f"<b>{used}/{cap}</b>" if cap > 0 else "∞"
    return f"Вылазки сегодня: {cap_txt} · стоимость боя: <b>{cost}</b> ⚡"
