"""
Редактируемый каталог полей карточки башни (JSON).

Файл: tower_card_catalog.json рядом с этим модулем.
Ключи — template_key монстра (как в пуле этажей 1–20), можно задать базовый ключ и elite_*.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("tower_card_catalog.json")
_CACHE: dict[str, dict[str, Any]] | None = None


def _load_raw() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {}
    try:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def reload_card_catalog() -> None:
    """Сброс кэша (после правки JSON перезапусти бота или вызови reload)."""
    global _CACHE
    _CACHE = None


def _entries() -> dict[str, dict[str, Any]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    raw = _load_raw()
    ent: dict[str, dict[str, Any]] = {}
    if isinstance(raw.get("entries"), dict):
        for k, v in raw["entries"].items():
            if isinstance(v, dict):
                ent[str(k)] = v
    else:
        for k, v in raw.items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            ent[str(k)] = v
    _CACHE = ent
    return _CACHE


def merged_catalog_entry(template_key: str, base_template_key: str) -> dict[str, Any]:
    """Слияние: сначала запись для base (без elite_), затем точное совпадение template_key."""
    ent = _entries()
    a = dict(ent.get(base_template_key, {}) or {})
    b = dict(ent.get(template_key, {}) or {})
    out = {**a, **b}
    return out


def catalog_str(entry: dict[str, Any], key: str) -> str | None:
    v = entry.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s or None
