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

    # --- Tier 2: Warrior specializations ---
    "grd_wall": SkillV2("grd_wall", "Стена щитов", "Мощная защитная стойка.", 28, 4, 0.0, "phys", effect_key="fortify", effect_chance=1.0),
    "grd_crush": SkillV2("grd_crush", "Сокрушение", "Тяжёлый удар с пробитием.", 24, 2, 1.9, "phys", effect_key="shred_armor", effect_chance=1.0),
    "brs_rend": SkillV2("brs_rend", "Рассечение", "Кровавый удар берсерка.", 22, 1, 2.0, "phys", effect_key="bleed", effect_chance=0.45),
    "brs_fury": SkillV2("brs_fury", "Бешеный напор", "Очень сильный удар без защиты.", 34, 3, 2.35, "phys"),

    # --- Tier 2: Mage specializations ---
    "pyro_flame": SkillV2("pyro_flame", "Пламенный взрыв", "Сильный огонь с шансом поджога.", 34, 2, 2.25, "mag", effect_key="burn", effect_chance=0.55),
    "pyro_ember": SkillV2("pyro_ember", "Тлеющая печать", "Ослабляет броню врага жаром.", 28, 3, 1.45, "mag", effect_key="shred_armor", effect_chance=1.0),
    "cryo_lance": SkillV2("cryo_lance", "Ледяное копьё", "Лёд пронзает цель.", 32, 2, 2.05, "mag", effect_key="freeze", effect_chance=0.45),
    "cryo_barrier": SkillV2("cryo_barrier", "Кристальный барьер", "Щит из льда.", 36, 5, 0.0, "mag", effect_key="shield", effect_chance=1.0),

    # --- Tier 2: Scout specializations ---
    "ass_shadow": SkillV2("ass_shadow", "Теневой выпад", "Удар по слабому месту.", 24, 2, 2.15, "phys", effect_key="backstab", effect_chance=1.0),
    "ass_venom": SkillV2("ass_venom", "Чёрный яд", "Сильное отравление.", 26, 3, 1.55, "phys", effect_key="poison", effect_chance=0.65),
    "rng_mark": SkillV2("rng_mark", "Метка охотника", "Точный дальний удар.", 22, 1, 2.0, "phys"),
    "rng_evasion": SkillV2("rng_evasion", "Побег сквозь туман", "Большой бонус уклонения.", 26, 4, 0.0, "phys", effect_key="dodge_buff", effect_chance=1.0),

    # --- Tier 2: Acolyte specializations ---
    "pal_smite": SkillV2("pal_smite", "Священный удар", "Световой удар паладина.", 28, 2, 1.95, "mag"),
    "pal_guard": SkillV2("pal_guard", "Обет защиты", "Защитная молитва.", 30, 4, 0.0, "mag", effect_key="block_next", effect_chance=1.0),
    "prp_radiance": SkillV2("prp_radiance", "Сияние", "Исцеляет раны.", 34, 3, 0.0, "mag", effect_key="heal", effect_chance=1.0),
    "prp_hymn": SkillV2("prp_hymn", "Гимн стойкости", "Долгое восстановление.", 38, 5, 0.0, "mag", effect_key="hot", effect_chance=1.0),
}

PASSIVES: dict[str, PassiveV2] = {
    "pas_war_tough": PassiveV2("pas_war_tough", "Закалка", "Увеличивает защиту на 15%.", {"def_bonus": 10.0}),
    "pas_mag_flow": PassiveV2("pas_mag_flow", "Поток маны", "Повышает силу магии на 15%.", {"mag_bonus_percent": 15}),
    "pas_sct_reflex": PassiveV2("pas_sct_reflex", "Рефлексы", "Повышает шанс уклонения на 10%.", {"dodge_bonus": 0.10}),
    "pas_aco_faith": PassiveV2("pas_aco_faith", "Вера", "Увеличивает регенерацию MP за ход.", {"mp_regen_turn": 5}),
    "pas_grd_bulwark": PassiveV2("pas_grd_bulwark", "Бастион", "Большой бонус защиты.", {"def_bonus": 22.0}),
    "pas_brs_frenzy": PassiveV2("pas_brs_frenzy", "Боевой транс", "Больше шанса крита.", {"crit_bonus": 0.08}),
    "pas_pyro_core": PassiveV2("pas_pyro_core", "Огненное ядро", "Сильнее магический урон.", {"mag_bonus_percent": 28}),
    "pas_cryo_focus": PassiveV2("pas_cryo_focus", "Холодный разум", "Мана восстанавливается быстрее.", {"mp_regen_turn": 8}),
    "pas_ass_precision": PassiveV2("pas_ass_precision", "Точный расчёт", "Крит и уклонение выше.", {"crit_bonus": 0.06, "dodge_bonus": 0.04}),
    "pas_rng_reflex": PassiveV2("pas_rng_reflex", "Следопыт", "Сильный бонус уклонения.", {"dodge_bonus": 0.14}),
    "pas_pal_oath": PassiveV2("pas_pal_oath", "Клятва", "Защита и вера.", {"def_bonus": 14.0, "mp_regen_turn": 3}),
    "pas_prp_grace": PassiveV2("pas_prp_grace", "Благодать", "Много регенерации маны.", {"mp_regen_turn": 10, "mag_bonus_percent": 8}),
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
    "guardian": Archetype(
        "guardian", "Страж", "🛡️", 2,
        "Воин, превративший защиту в оружие.",
        base_stats={"str": 22, "vit": 24},
        hp_multiplier=1.25,
        passives=(PASSIVES["pas_war_tough"], PASSIVES["pas_grd_bulwark"]),
        skills=("grd_wall", "grd_crush", "war_bash"),
        requirements={"level": 30, "str": 28, "vit": 24},
    ),
    "berserker": Archetype(
        "berserker", "Берсерк", "🩸", 2,
        "Воин, который давит врага яростью и критами.",
        base_stats={"str": 28, "vit": 18},
        hp_multiplier=1.18,
        passives=(PASSIVES["pas_brs_frenzy"],),
        skills=("brs_rend", "brs_fury", "war_heavy"),
        requirements={"level": 30, "str": 32},
    ),
    "pyromancer": Archetype(
        "pyromancer", "Пиромант", "🔥", 2,
        "Маг разрушительного огня.",
        base_stats={"int": 28, "luck": 14},
        mp_multiplier=1.25,
        passives=(PASSIVES["pas_mag_flow"], PASSIVES["pas_pyro_core"]),
        skills=("pyro_flame", "pyro_ember", "mag_fire"),
        requirements={"level": 30, "int": 32},
    ),
    "cryomancer": Archetype(
        "cryomancer", "Криомант", "❄️", 2,
        "Маг льда, контроля и выживания.",
        base_stats={"int": 24, "vit": 18},
        mp_multiplier=1.28,
        passives=(PASSIVES["pas_cryo_focus"],),
        skills=("cryo_lance", "cryo_barrier", "mag_frost"),
        requirements={"level": 30, "int": 28, "vit": 18},
    ),
    "assassin": Archetype(
        "assassin", "Ассасин", "🗡️", 2,
        "Убийца, который заканчивает бой до ответного удара.",
        base_stats={"dex": 28, "luck": 22},
        passives=(PASSIVES["pas_sct_reflex"], PASSIVES["pas_ass_precision"]),
        skills=("ass_shadow", "ass_venom", "sct_shot"),
        requirements={"level": 30, "dex": 30, "luck": 20},
    ),
    "ranger": Archetype(
        "ranger", "Следопыт", "🏹", 2,
        "Охотник, который переживает врага скоростью.",
        base_stats={"dex": 30, "vit": 16},
        passives=(PASSIVES["pas_rng_reflex"],),
        skills=("rng_mark", "rng_evasion", "sct_dodge"),
        requirements={"level": 30, "dex": 32},
    ),
    "paladin": Archetype(
        "paladin", "Паладин", "⚜️", 2,
        "Жрец в броне, держащий строй светом.",
        base_stats={"vit": 24, "int": 20, "str": 18},
        hp_multiplier=1.18,
        mp_multiplier=1.12,
        passives=(PASSIVES["pas_pal_oath"],),
        skills=("pal_smite", "pal_guard", "aco_bless"),
        requirements={"level": 30, "vit": 24, "int": 20},
    ),
    "prophet": Archetype(
        "prophet", "Пророк", "✨", 2,
        "Жрец чистой благодати и долгих боёв.",
        base_stats={"int": 26, "luck": 20},
        mp_multiplier=1.30,
        passives=(PASSIVES["pas_aco_faith"], PASSIVES["pas_prp_grace"]),
        skills=("prp_radiance", "prp_hymn", "aco_smite"),
        requirements={"level": 30, "int": 28, "luck": 18},
    ),
}
