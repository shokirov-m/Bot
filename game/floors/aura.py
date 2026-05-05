"""
Floor Auras: unique mechanics for floors 21-30.
"""
from typing import Any

def get_floor_aura(floor: int) -> dict[str, Any] | None:
    # Этажи 21–30: события-«ауры» (часть дебаффы, часть баффы).
    f = int(floor)
    if f == 21:
        return {
            "name": "Ледяной туман",
            "emoji": "❄️",
            "desc": "Холод сковывает движения: ЛОВ ×0.85.",
            "stat_penalty": {"dex_mult": 0.85},
        }
    if f == 22:
        return {
            "name": "Эхо удачи",
            "emoji": "🍀",
            "desc": "Башня подбрасывает монеты: +15% золота и опыта за победу.",
            "reward_gold_mult": 1.15,
            "reward_xp_mult": 1.15,
        }
    if f == 23:
        return {
            "name": "Туман призраков",
            "emoji": "🌫️",
            "desc": "Видимость падает: ЛОВ ×0.9 и каждые 3 хода шанс промаха +20%.",
            "stat_penalty": {"dex_mult": 0.9},
            "miss_chance_mod_period": 3,
            "miss_chance_mod_value": 0.20,
        }
    if f == 24:
        return {
            "name": "Испепеляющий зной",
            "emoji": "🔥",
            "desc": "Жар выжигает силы: каждый ход −4% текущего HP.",
            "hp_loss_turn_pct": 0.04,
        }
    if f == 25:
        return {
            "name": "Тёплый источник",
            "emoji": "💧",
            "desc": "Скрытый родник лечит: +3% от макс. HP каждый ход.",
            "player_regen_turn_pct_max": 0.03,
        }
    if f == 26:
        return {
            "name": "Пепельный воздух",
            "emoji": "🫧",
            "desc": "Тяжёлое дыхание: каждый ход −3% текущего HP, но +10% XP за победу.",
            "hp_loss_turn_pct": 0.03,
            "reward_xp_mult": 1.10,
        }
    if f == 27:
        return {
            "name": "Магические помехи",
            "emoji": "⚡",
            "desc": "Навыки дорожают: расход MP ×1.4.",
            "mp_cost_mult": 1.4,
        }
    if f == 28:
        return {
            "name": "Стабильный поток",
            "emoji": "🔷",
            "desc": "Мана течёт ровно: расход MP ×0.85.",
            "mp_cost_mult": 0.85,
        }
    if f == 29:
        return {
            "name": "Разряд в рунах",
            "emoji": "🗲",
            "desc": "Срывает концентрацию: расход MP ×1.35, каждые 4 хода шанс промаха +15%.",
            "mp_cost_mult": 1.35,
            "miss_chance_mod_period": 4,
            "miss_chance_mod_value": 0.15,
        }
    if f == 30:
        return {
            "name": "Аура Владыки",
            "emoji": "👑",
            "desc": "Враг крепнет: восстанавливает 5% HP в начале хода, но награды +20%.",
            "monster_regen_pct": 0.05,
            "reward_gold_mult": 1.20,
            "reward_xp_mult": 1.20,
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
