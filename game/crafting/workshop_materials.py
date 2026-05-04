"""
Ресурсы мастерской (руда, травы, самоцветы) — расширение: kind=\"workshop_res\" в item_data.

Основная экономика рецептов: recipes_data.craft_cost (именованные материалы, см. game/items/craft_resources.py)
и при необходимости пустой recipes_data.cost {{}}. Этот модуль — задел под отдельные id workshop_res.
"""

from __future__ import annotations

from typing import Any


def workshop_resource_payload(*, res_id: str, name: str, count: int = 1, rarity: str = "common") -> dict[str, Any]:
    return {
        "name": name,
        "kind": "workshop_res",
        "res_id": str(res_id),
        "rarity": str(rarity).lower().strip(),
        "count": max(1, int(count)),
        "summary": f"Ресурс мастерской: {res_id}.",
    }
