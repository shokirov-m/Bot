"""
Achievement Service: Defines and processes player achievements.
Rewards are stored and applied once. Claimed keys are in character.meta_progress['achievements_claimed'].
"""
from __future__ import annotations
import html
from typing import Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.character import Character

ACHIEVEMENTS: dict[str, dict[str, Any]] = {
    "icy_conqueror": {
        "name": "Покоритель льдов",
        "desc": "Достичь 40-го этажа",
        "condition": lambda c: int(c.highest_floor_reached or c.floor_number) >= 40,
        "reward_stats": {"str": 5},
    },
    "alchemist_apprentice": {
        "name": "Ученик алхимика",
        "desc": "Приготовить 10 эликсиров",
        "condition": lambda c: int((c.meta_progress or {}).get("elixirs_brewed", 0)) >= 10,
        "reward_stats": {"int": 2},
    },
    "monster_scholar": {
        "name": "Исследователь монстров",
        "desc": "Победить 500 монстров",
        "condition": lambda c: int(c.total_kills) >= 500,
        "reward_stats": {"luck": 3},
    },
    "wealthy_adventurer": {
        "name": "Богатый странник",
        "desc": "Накопить 100 000 золота",
        "condition": lambda c: int(c.gold) >= 100000,
        "reward_gold_bonus": 0.05,
    },
    "tower_initiate": {
        "name": "Посвященный башни",
        "desc": "Достичь 10-го уровня",
        "condition": lambda c: int(c.level) >= 10,
        "reward_gold": 2000,
        "reward_xp": 1000,
    },
    "boss_hunter": {
        "name": "Охотник на боссов",
        "desc": "Победить 10 боссов",
        "condition": lambda c: int((c.meta_progress or {}).get("bosses_killed", 0)) >= 10,
        "reward_gold": 10000,
        "reward_stats": {"str": 2},
    },
    "rich_merchant": {
        "name": "Богатый торговец",
        "desc": "Продать предметов на 50 000 золота",
        "condition": lambda c: int((c.meta_progress or {}).get("total_gold_from_sales", 0)) >= 50000,
        "reward_gold_bonus": 0.02,
    },
    "legendary_climber": {
        "name": "Легендарный альпинист",
        "desc": "Достичь 80-го этажа",
        "condition": lambda c: int(c.highest_floor_reached or c.floor_number) >= 80,
        "reward_stats": {"vit": 10},
        "reward_gold": 50000,
    },
    "stamina_master": {
        "name": "Мастер выносливости",
        "desc": "Потратить 1000 ед. стамины",
        "condition": lambda c: int((c.meta_progress or {}).get("total_stamina_spent", 0)) >= 1000,
        "reward_stats": {"vit": 5},
    },
    "arena_contender": {
        "name": "Претендент арены",
        "desc": "Участвовать в 10 боях на арене",
        "condition": lambda c: int((c.meta_progress or {}).get("arena_battles", 0)) >= 10,
        "reward_gold": 5000,
    },
    "pet_master": {
        "name": "Хозяин питомцев",
        "desc": "Получить первого питомца",
        "condition": lambda c: (c.meta_progress or {}).get("pet_active") is not None,
        "reward_stats": {"luck": 2},
    },
    "steady_hand": {
        "name": "Твердая рука",
        "desc": "Совершить 20 успешных улучшений предметов",
        "condition": lambda c: int((c.meta_progress or {}).get("successful_enchants", 0)) >= 20,
        "reward_stats": {"dex": 5},
    },
    "traveler": {
        "name": "Путешественник",
        "desc": "Посетить таверну 20 раз",
        "condition": lambda c: int(c.tavern_visits) >= 20,
        "reward_gold": 3000,
    },
    "legendary_crafter": {
        "name": "Легендарный ремесленник",
        "desc": "Совершить успешную заточку на +7",
        "condition": lambda c: int((c.meta_progress or {}).get("max_enchant_level", 0)) >= 7,
        "reward_stats": {"luck": 10},
    },
    "monster_nemesis": {
        "name": "Заклятый враг монстров",
        "desc": "Победить 5000 монстров",
        "condition": lambda c: int(c.total_kills) >= 5000,
        "reward_xp_bonus": 0.05,
    },
    "tower_legend": {
        "name": "Легенда башни",
        "desc": "Достичь 100-го этажа",
        "condition": lambda c: int(c.highest_floor_reached or c.floor_number) >= 100,
        "reward_stats": {"str": 20, "dex": 20, "int": 20, "vit": 20, "luck": 20},
    },
    "millionaire": {
        "name": "Миллионер",
        "desc": "Накопить 1 000 000 золота",
        "condition": lambda c: int(c.gold) >= 1000000,
        "reward_gold_bonus": 0.10,
    }
}

def get_claimed_keys(character: Character) -> list[str]:
    return list((character.meta_progress or {}).get("achievements_claimed", []))

def check_and_apply_achievements(character: Character) -> list[str]:
    """
    Checks all achievements and applies rewards for newly completed ones.
    Returns list of names of newly completed achievements.
    """
    claimed = get_claimed_keys(character)
    newly_completed = []
    mp = dict(character.meta_progress or {})
    
    changed = False
    for key, ach in ACHIEVEMENTS.items():
        if key in claimed:
            continue
        
        if ach["condition"](character):
            # Apply rewards
            if "reward_gold" in ach:
                character.gold = int(character.gold) + ach["reward_gold"]
            if "reward_xp" in ach:
                character.experience = int(character.experience) + ach["reward_xp"]
            
            # Stats are added to base stats permanently
            if "reward_stats" in ach:
                stats = ach["reward_stats"]
                character.stat_strength = int(character.stat_strength) + stats.get("str", 0)
                character.stat_dexterity = int(character.stat_dexterity) + stats.get("dex", 0)
                character.stat_intelligence = int(character.stat_intelligence) + stats.get("int", 0)
                character.stat_vitality = int(character.stat_vitality) + stats.get("vit", 0)
                character.stat_luck = int(character.stat_luck) + stats.get("luck", 0)
            
            # Gold bonus is stored in meta for service lookup
            if "reward_gold_bonus" in ach:
                current_bonus = float(mp.get("achievement_gold_bonus", 0.0))
                mp["achievement_gold_bonus"] = current_bonus + ach["reward_gold_bonus"]

            # XP bonus is stored in meta for service lookup
            if "reward_xp_bonus" in ach:
                current_bonus_xp = float(mp.get("achievement_xp_bonus", 0.0))
                mp["achievement_xp_bonus"] = current_bonus_xp + ach["reward_xp_bonus"]
                
            claimed.append(key)
            newly_completed.append(ach["name"])
            changed = True
            
    if changed:
        mp["achievements_claimed"] = claimed
        character.meta_progress = mp
        
    return newly_completed

def summarize_achievement_bonuses(character: Character) -> dict[str, float | int]:
    """Сводка по «активным» бонусам с достижений: считается из meta_progress."""
    mp = dict(character.meta_progress or {})
    claimed = list(mp.get("achievements_claimed") or [])
    return {
        "claimed_count": int(len(claimed)),
        "gold_bonus": float(mp.get("achievement_gold_bonus", 0.0) or 0.0),
        "xp_bonus": float(mp.get("achievement_xp_bonus", 0.0) or 0.0),
    }


def format_achievement_bonuses_html(character: Character) -> str:
    """Однострочник для блока «От достижений» в полных хар-ках."""
    s = summarize_achievement_bonuses(character)
    cnt = int(s["claimed_count"])
    gb = float(s["gold_bonus"]) * 100.0
    xb = float(s["xp_bonus"]) * 100.0
    if cnt <= 0 and gb <= 0 and xb <= 0:
        return ""
    parts = [f"🏆 закрыто: {cnt}"]
    if gb > 0:
        parts.append(f"💰 +{gb:.0f}% золота")
    if xb > 0:
        parts.append(f"✨ +{xb:.0f}% опыта")
    return " · ".join(parts)


def format_achievements_html(character: Character) -> str:
    """Returns HTML listing only COMPLETED achievements."""
    claimed = get_claimed_keys(character)
    if not claimed:
        return "🏆 <b>Твои достижения</b>\n\n<i>Пока нет выполненных достижений. Продолжай путь!</i>"
    
    lines = ["🏆 <b>Выполненные достижения</b>", ""]
    for key in claimed:
        ach = ACHIEVEMENTS.get(key)
        if not ach: continue
        lines.append(f"✅ <b>{ach['name']}</b>")
        lines.append(f"└ <i>{ach['desc']}</i>")
        
    return "\n".join(lines)
