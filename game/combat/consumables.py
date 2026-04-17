"""
Расходники в бою: зелья HP/MP, снятие яда (синхронно с item_data.use_tag из лавки).
"""

from __future__ import annotations

import json
from typing import Any

from game.combat import effects

# Допустимые use_tag в бою. Пайок (stamina_flat) — только из сумки вне боя.
COMBAT_USE_TAGS = frozenset(
    {"heal_hp_pct", "heal_mp_pct", "heal_hp_flat", "heal_mp_flat", "cure_poison"},
)


def item_data_as_dict(raw: Any) -> dict[str, Any]:
    """Нормализация JSON из БД: dict или редкая строка с JSON."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def normalize_combat_use_tag(item_data: dict[str, Any]) -> str:
    """Единый формат тега (лавка/лут могли сохранить регистр иначе)."""
    return str(item_data.get("use_tag") or item_data.get("USE_TAG") or "").strip().lower()


def apply_consumable(state: dict[str, Any], item_data: dict[str, Any]) -> list[str]:
    """Изменяет combat state; возвращает строки лога боя."""
    tag = normalize_combat_use_tag(item_data)
    raw_v = item_data.get("use_value", 0)
    try:
        val = int(raw_v) if raw_v is not None else 0
    except (TypeError, ValueError):
        val = 0
    logs: list[str] = []

    if tag not in COMBAT_USE_TAGS:
        raise ValueError(f"unknown_use_tag:{tag}")

    if tag == "heal_hp_pct":
        pct = max(1, min(100, val))
        mx = int(state["player_hp_max"])
        cur = int(state["player_hp"])
        heal = max(1, int(mx * pct / 100))
        new_hp = min(mx, cur + heal)
        state["player_hp"] = new_hp
        logs.append(f"💚 {item_data.get('name', 'Зелье')}: +{new_hp - cur} HP")
    elif tag == "heal_mp_pct":
        pct = max(1, min(100, val))
        mx = int(state["player_mp_max"])
        cur = int(state["player_mp"])
        gain = max(1, int(mx * pct / 100))
        new_mp = min(mx, cur + gain)
        state["player_mp"] = new_mp
        logs.append(f"💙 {item_data.get('name', 'Зелье')}: +{new_mp - cur} MP")
    elif tag == "heal_hp_flat":
        heal = max(1, val)
        mx = int(state["player_hp_max"])
        cur = int(state["player_hp"])
        new_hp = min(mx, cur + heal)
        state["player_hp"] = new_hp
        logs.append(f"🍞 {item_data.get('name', 'Хлеб')}: +{new_hp - cur} HP")
    elif tag == "heal_mp_flat":
        gain = max(1, val)
        mx = int(state["player_mp_max"])
        cur = int(state["player_mp"])
        new_mp = min(mx, cur + gain)
        state["player_mp"] = new_mp
        logs.append(f"💠 {item_data.get('name', 'Эликсир')}: +{new_mp - cur} MP")
    elif tag == "cure_poison":
        had = effects.remove_effects_with_key("player", state, "poison")
        name = item_data.get("name", "Противоядие")
        if had:
            logs.append(f"🧴 {name}: яд снят.")
        else:
            logs.append(f"🧴 {name}: яда не было — зелье выпито впустую.")

    return logs
