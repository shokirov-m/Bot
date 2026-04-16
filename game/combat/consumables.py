"""
Расходники в бою: зелья HP/MP, снятие яда (синхронно с item_data.use_tag из лавки).
"""

from __future__ import annotations

from typing import Any

from game.combat import effects

# Допустимые use_tag в бою. Пайок (stamina_flat) — только из сумки вне боя.
COMBAT_USE_TAGS = frozenset(
    {"heal_hp_pct", "heal_mp_pct", "heal_hp_flat", "heal_mp_flat", "cure_poison"},
)


def apply_consumable(state: dict[str, Any], item_data: dict[str, Any]) -> list[str]:
    """Изменяет combat state; возвращает строки лога боя."""
    tag = str(item_data.get("use_tag", ""))
    val = int(item_data.get("use_value", 0))
    logs: list[str] = []

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
    else:
        raise ValueError(f"Неизвестный расходник в бою: {tag}")

    return logs
