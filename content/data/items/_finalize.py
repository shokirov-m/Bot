"""Обёртка для списков каталога: те же дефолты, что были в catalog/_stub_utils."""

from __future__ import annotations

import copy
from typing import Any


def finalize_stub_list(build: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from game.items.equipment.defaults import apply_item_payload_defaults

    out: list[dict[str, Any]] = []
    for d in build:
        x = copy.deepcopy(d)
        apply_item_payload_defaults(x)
        out.append(x)
    return out
