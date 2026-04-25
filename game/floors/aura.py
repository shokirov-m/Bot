"""
Floor Auras: unique mechanics for floors 21-30.
"""
from typing import Any

def get_floor_aura(floor: int) -> dict[str, Any] | None:
    # Floor 21-23: Chilling Fog
    if 21 <= floor <= 23:
        return {
            "name": "Ледяной туман",
            "emoji": "❄️",
            "desc": "Снижает вашу скорость и уклонение на 20%.",
            "stat_penalty": {"dex_mult": 0.8},
        }
    
    # Floor 24-26: Scorching Heat
    if 24 <= floor <= 26:
        return {
            "name": "Испепеляющий зной",
            "emoji": "🔥",
            "desc": "Каждый ход вы теряете 5% текущего здоровья.",
            "hp_loss_turn_pct": 0.05,
        }
        
    # Floor 27-29: Arcane Static
    if 27 <= floor <= 29:
        return {
            "name": "Магические помехи",
            "emoji": "⚡",
            "desc": "Расход маны на навыки увеличен в 1.5 раза.",
            "mp_cost_mult": 1.5,
        }
        
    # Floor 30: Boss Aura
    if floor == 30:
        return {
            "name": "Аура Владыки",
            "emoji": "👑",
            "desc": "Босс восстанавливает 5% здоровья в начале каждого хода.",
            "monster_regen_pct": 0.05,
        }

    # Floor 31-40: Blizzard
    if 31 <= floor <= 40:
        return {
            "name": "Снежный буран",
            "emoji": "🌨️",
            "desc": "Каждый 3-й ход ваша меткость снижается на 20%.",
            "miss_chance_mod_period": 3,
            "miss_chance_mod_value": 0.20,
        }
        
    return None

def apply_aura_to_combat_state(state: dict[str, Any]) -> None:
    floor = int(state.get("floor") or 0)
    aura = get_floor_aura(floor)
    if not aura: return
    
    state["floor_aura"] = aura
    
    # Apply flat multipliers if any
    if "stat_penalty" in aura:
        mods = state.get("passive_mods") or {}
        for k, v in aura["stat_penalty"].items():
            mods[k] = mods.get(k, 1.0) * v
        state["passive_mods"] = mods
        
    if "mp_cost_mult" in aura:
        state["player_mp_cost_mult"] = aura["mp_cost_mult"]
