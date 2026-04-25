"""
Raw data for Archetypes and Skills 2.0.
"""
from __future__ import annotations
from game.archetypes.models import Archetype, SkillV2, PassiveV2

SKILLS: dict[str, SkillV2] = {
    # --- Wanderer (Tier 0) ---
    "wn_strike": SkillV2("wn_strike", "Простой удар", "Базовая атака оружием.", 5, 0, 1.1, "phys"),
    "wn_block": SkillV2("wn_block", "Блок", "Снижает входящий урон.", 8, 2, 0.0, "phys", effect_key="block_next", effect_chance=1.0),
    
    # --- Warrior (Tier 1) ---
    "war_heavy": SkillV2("war_heavy", "Тяжелый удар", "Мощный замах, игнорирующий часть брони.", 15, 0, 1.6, "phys"),
    "war_bash": SkillV2("war_bash", "Удар щитом", "Шанс оглушить врага.", 20, 3, 1.2, "phys", effect_key="stun", effect_chance=0.3),
    "war_roar": SkillV2("war_roar", "Боевой клич", "Усиливает защиту.", 18, 4, 0.0, "phys", effect_key="fortify", effect_chance=1.0),
    
    # --- Mage (Tier 1) ---
    "mag_fire": SkillV2("mag_fire", "Огненный шар", "Поджигает цель.", 22, 0, 1.8, "mag", effect_key="burn", effect_chance=0.4),
    "mag_frost": SkillV2("mag_frost", "Ледяная стрела", "Замедляет врага.", 25, 2, 1.5, "mag", effect_key="freeze", effect_chance=0.3),
    "mag_shield": SkillV2("mag_shield", "Магический щит", "Поглощает урон за счет маны.", 30, 4, 0.0, "mag", effect_key="shield", effect_chance=1.0),
    
    # --- Scout (Tier 1) ---
    "sct_shot": SkillV2("sct_shot", "Точный выстрел", "Высокий шанс критического удара.", 12, 0, 1.7, "phys"),
    "sct_poison": SkillV2("sct_poison", "Отравленный нож", "Наносит периодический урон ядом.", 18, 3, 1.3, "phys", effect_key="poison", effect_chance=0.5),
    "sct_dodge": SkillV2("sct_dodge", "Увертливость", "Значительно повышает шанс уклонения.", 20, 4, 0.0, "phys", effect_key="dodge_buff", effect_chance=1.0),
    
    # --- Acolyte (Tier 1) ---
    "aco_smite": SkillV2("aco_smite", "Кара", "Святой свет поражает врага.", 16, 0, 1.5, "mag"),
    "aco_heal": SkillV2("aco_heal", "Лечение", "Восстанавливает HP.", 25, 0, 0.0, "mag", effect_key="heal", effect_chance=1.0),
    "aco_bless": SkillV2("aco_bless", "Благословение", "Регенерация HP и MP.", 30, 5, 0.0, "mag", effect_key="hot", effect_chance=1.0),
}

PASSIVES: dict[str, PassiveV2] = {
    "pas_war_tough": PassiveV2("pas_war_tough", "Закалка", "Увеличивает защиту на 15%.", {"def_bonus": 10.0}),
    "pas_mag_flow": PassiveV2("pas_mag_flow", "Поток маны", "Повышает силу магии на 15%.", {"mag_bonus_percent": 15}),
    "pas_sct_reflex": PassiveV2("pas_sct_reflex", "Рефлексы", "Повышает шанс уклонения на 10%.", {"dodge_bonus": 0.10}),
    "pas_aco_faith": PassiveV2("pas_aco_faith", "Вера", "Увеличивает регенерацию MP за ход.", {"mp_regen_turn": 5}),
}

ARCHETYPES: dict[str, Archetype] = {
    "wanderer": Archetype(
        "wanderer", "Странник", "🎒", 0, 
        "Новичок, ищущий свой путь в Башне.",
        base_stats={"str": 10, "dex": 10, "int": 10, "vit": 10, "luck": 10},
        skills=("wn_strike", "wn_block"),
    ),
    "warrior": Archetype(
        "warrior", "Воин", "🗡️", 1,
        "Мастер ближнего боя и тяжелых доспехов.",
        base_stats={"str": 15, "vit": 14},
        hp_multiplier=1.15,
        passives=(PASSIVES["pas_war_tough"],),
        skills=("war_heavy", "war_bash", "war_roar"),
        requirements={"level": 10, "str": 15},
    ),
    "mage": Archetype(
        "mage", "Маг", "🔮", 1,
        "Повелитель стихий и тайных знаний.",
        base_stats={"int": 16, "vit": 8},
        mp_multiplier=1.20,
        passives=(PASSIVES["pas_mag_flow"],),
        skills=("mag_fire", "mag_frost", "mag_shield"),
        requirements={"level": 10, "int": 15},
    ),
    "scout": Archetype(
        "scout", "Убийца", "🗡️", 1,
        "Мастер скрытных атак, полагающийся на яды и критические удары.",
        base_stats={"dex": 16, "luck": 12},
        passives=(PASSIVES["pas_sct_reflex"],),
        skills=("sct_shot", "sct_poison", "sct_dodge"),
        requirements={"level": 10, "dex": 15},
    ),
    "acolyte": Archetype(
        "acolyte", "Жрец", "⛪", 1,
        "Могущественный служитель богов, повелевающий силой исцеления.",
        base_stats={"int": 14, "vit": 12, "luck": 12},
        mp_multiplier=1.10,
        passives=(PASSIVES["pas_aco_faith"],),
        skills=("aco_smite", "aco_heal", "aco_bless"),
        requirements={"level": 10, "int": 12, "vit": 12},
    ),
}
