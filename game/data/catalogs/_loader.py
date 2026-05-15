"""Общая загрузка JSON-каталогов (UTF-8, кэш, сброс)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_DIR = Path(__file__).resolve().parent
_CACHE: dict[str, Any] = {}


def catalog_path(name: str) -> Path:
    if not name.endswith(".json"):
        name = f"{name}.json"
    return _CATALOG_DIR / name


def load_catalog_json(name: str, *, reload: bool = False) -> dict[str, Any]:
    key = name if name.endswith(".json") else f"{name}.json"
    if not reload and key in _CACHE:
        cached = _CACHE[key]
        return cached if isinstance(cached, dict) else {}
    path = catalog_path(key)
    if not path.is_file():
        _CACHE[key] = {}
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _CACHE[key] = {}
        return {}
    data = raw if isinstance(raw, dict) else {}
    _CACHE[key] = data
    return data


def reload_all_catalogs() -> None:
    _CACHE.clear()


def entries_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ent = catalog.get("entries")
    if isinstance(ent, dict):
        return {str(k): dict(v) for k, v in ent.items() if isinstance(v, dict)}
    out: dict[str, dict[str, Any]] = {}
    for k, v in catalog.items():
        if str(k).startswith("_") or not isinstance(v, dict):
            continue
        out[str(k)] = dict(v)
    return out
