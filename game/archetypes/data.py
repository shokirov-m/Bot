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
    "war_heavy": SkillV2("war_heavy", "Тяжелый удар", "Мощный замах, игнорирующий часть брони.", 15, 0, 1.9, "phys"),
    "war_bash": SkillV2("war_bash", "Удар щитом", "Шанс оглушить врага.", 20, 3, 1.5, "phys", effect_key="stun", effect_chance=0.35),
    "war_roar": SkillV2("war_roar", "Боевой клич", "Усиливает защиту.", 18, 4, 0.0, "phys", effect_key="fortify", effect_chance=1.0),
    
    # --- Mage (Tier 1) ---
    "mag_fire": SkillV2("mag_fire", "Огненный шар", "Поджигает цель.", 22, 0, 2.1, "mag", effect_key="burn", effect_chance=0.45),
    "mag_frost": SkillV2("mag_frost", "Ледяная стрела", "Замедляет врага.", 25, 2, 1.8, "mag", effect_key="freeze", effect_chance=0.35),
    "mag_shield": SkillV2("mag_shield", "Магический щит", "Поглощает урон за счет маны.", 30, 4, 0.0, "mag", effect_key="shield", effect_chance=1.0),
    
    # --- Scout (Tier 1) ---
    "sct_shot": SkillV2("sct_shot", "Точный выстрел", "Высокий шанс критического удара.", 12, 0, 2.0, "phys"),
    "sct_poison": SkillV2("sct_poison", "Отравленный нож", "Наносит периодический урон ядом.", 18, 3, 1.6, "phys", effect_key="poison", effect_chance=0.55),
    "sct_dodge": SkillV2("sct_dodge", "Увертливость", "Значительно повышает шанс уклонения.", 20, 4, 0.0, "phys", effect_key="dodge_buff", effect_chance=1.0),
    
    # --- Acolyte (Tier 1) ---
    "aco_smite": SkillV2("aco_smite", "Кара", "Святой свет поражает врага.", 16, 0, 1.8, "mag"),
    "aco_heal": SkillV2("aco_heal", "Лечение", "Восстанавливает HP.", 25, 0, 0.0, "mag", effect_key="heal", effect_chance=1.0),
    "aco_bless": SkillV2("aco_bless", "Благословение", "Регенерация HP и MP.", 30, 5, 0.0, "mag", effect_key="hot", effect_chance=1.0),

    # --- Tier 2: Warrior specializations ---
    "grd_wall": SkillV2("grd_wall", "Стена щитов", "Мощная защитная стойка.", 28, 4, 0.0, "phys", effect_key="fortify", effect_chance=1.0),
    "grd_crush": SkillV2("grd_crush", "Сокрушение", "Тяжёлый удар с пробитием.", 24, 2, 3.8, "phys", effect_key="shred_armor", effect_chance=1.0),
    "brs_rend": SkillV2("brs_rend", "Рассечение", "Кровавый удар берсерка.", 22, 1, 4.0, "phys", effect_key="bleed", effect_chance=0.55),
    "brs_fury": SkillV2("brs_fury", "Бешеный напор", "Очень сильный удар без защиты.", 34, 3, 5.0, "phys"),

    # --- Tier 2: Mage specializations ---
    "pyro_flame": SkillV2("pyro_flame", "Пламенный взрыв", "Сильный огонь с шансом поджога.", 34, 2, 4.8, "mag", effect_key="burn", effect_chance=0.65),
    "pyro_ember": SkillV2("pyro_ember", "Тлеющая печать", "Ослабляет броню врага жаром.", 28, 3, 2.9, "mag", effect_key="shred_armor", effect_chance=1.0),
    "cryo_lance": SkillV2("cryo_lance", "Ледяное копьё", "Лёд пронзает цель.", 32, 2, 4.1, "mag", effect_key="freeze", effect_chance=0.55),
    "cryo_barrier": SkillV2("cryo_barrier", "Кристальный барьер", "Щит из льда.", 36, 5, 0.0, "mag", effect_key="shield", effect_chance=1.0),

    # --- Tier 2: Scout specializations ---
    "ass_shadow": SkillV2("ass_shadow", "Теневой выпад", "Удар по слабому месту.", 24, 2, 4.3, "phys", effect_key="backstab", effect_chance=1.0),
    "ass_venom": SkillV2("ass_venom", "Чёрный яд", "Сильное отравление.", 26, 3, 3.1, "phys", effect_key="poison", effect_chance=0.75),
    "rng_mark": SkillV2("rng_mark", "Метка охотника", "Точный дальний удар.", 22, 1, 4.0, "phys"),
    "rng_evasion": SkillV2("rng_evasion", "Побег сквозь туман", "Большой бонус уклонения.", 26, 4, 0.0, "phys", effect_key="dodge_buff", effect_chance=1.0),

    # --- Tier 2: Acolyte specializations ---
    "pal_smite": SkillV2("pal_smite", "Священный удар", "Световой удар паладина.", 28, 2, 3.9, "mag"),
    "pal_guard": SkillV2("pal_guard", "Обет защиты", "Защитная молитва.", 30, 4, 0.0, "mag", effect_key="block_next", effect_chance=1.0),
    "prp_radiance": SkillV2("prp_radiance", "Сияние", "Исцеляет раны.", 34, 3, 0.0, "mag", effect_key="heal", effect_chance=1.0),
    "prp_hymn": SkillV2("prp_hymn", "Гимн стойкости", "Долгое восстановление.", 38, 5, 0.0, "mag", effect_key="hot", effect_chance=1.0),
}

PASSIVES: dict[str, PassiveV2] = {
    "pas_war_tough": PassiveV2("pas_war_tough", "Закалка", "Увеличивает защиту.", {"def_bonus": 6.0}),
    "pas_mag_flow": PassiveV2("pas_mag_flow", "Поток маны", "Повышает силу магии на 18%.", {"mag_bonus_percent": 18}),
    "pas_sct_reflex": PassiveV2("pas_sct_reflex", "Рефлексы", "Повышает шанс уклонения на 12%.", {"dodge_bonus": 0.12}),
    "pas_aco_faith": PassiveV2("pas_aco_faith", "Вера", "Увеличивает регенерацию MP за ход.", {"mp_regen_turn": 6}),
    "pas_grd_bulwark": PassiveV2("pas_grd_bulwark", "Бастион", "Большой бонус защиты.", {"def_bonus": 44.0}),
    "pas_brs_frenzy": PassiveV2("pas_brs_frenzy", "Боевой транс", "Больше шанса крита.", {"crit_bonus": 0.16}),
    "pas_pyro_core": PassiveV2("pas_pyro_core", "Огненное ядро", "Сильнее магический урон.", {"mag_bonus_percent": 56}),
    "pas_cryo_focus": PassiveV2("pas_cryo_focus", "Холодный разум", "Мана восстанавливается быстрее.", {"mp_regen_turn": 16}),
    "pas_ass_precision": PassiveV2("pas_ass_precision", "Точный расчёт", "Крит и уклонение выше.", {"crit_bonus": 0.12, "dodge_bonus": 0.08}),
    "pas_rng_reflex": PassiveV2("pas_rng_reflex", "Следопыт", "Сильный бонус уклонения.", {"dodge_bonus": 0.28}),
    "pas_pal_oath": PassiveV2("pas_pal_oath", "Клятва", "Защита и вера.", {"def_bonus": 28.0, "mp_regen_turn": 6}),
    "pas_prp_grace": PassiveV2("pas_prp_grace", "Благодать", "Много регенерации маны.", {"mp_regen_turn": 20, "mag_bonus_percent": 16}),
    # --- Tier 2 distinguishing passives (×2 delta from 1.0 for multipliers) ---
    "pas_grd_titan": PassiveV2("pas_grd_titan", "Гроза боссов", "Урон по боссам выше на 20%.", {"boss_dmg_mult": 1.20}),
    "pas_brs_blood": PassiveV2("pas_brs_blood", "Жажда крови", "+30% шанс кровотечения при ударе.", {"on_hit_bleed_chance": 0.30}),
    "pas_pyro_burn": PassiveV2("pas_pyro_burn", "Полыхание", "+30% шанс поджога при ударе.", {"on_hit_burn_chance": 0.30}),
    "pas_cryo_freeze": PassiveV2("pas_cryo_freeze", "Хладнокровие", "+24% шанс заморозить врага при ударе.", {"on_hit_freeze_chance": 0.24}),
    "pas_ass_mortal": PassiveV2("pas_ass_mortal", "Смертельный удар", "+24% шанс отравить врага при ударе.", {"on_hit_poison_chance": 0.24}),
    "pas_rng_focus": PassiveV2("pas_rng_focus", "Фокус охотника", "Урон по элитам выше на 20%.", {"elite_dmg_mult": 1.20}),
    "pas_pal_aegis": PassiveV2("pas_pal_aegis", "Эгида", "Получаемый урон ниже на 16%.", {"dmg_taken_mult": 0.84}),
    "pas_prp_blessing": PassiveV2("pas_prp_blessing", "Дар", "Восстанавливает 4% HP за ход.", {"hp_regen_pct_turn": 0.04}),
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
        base_stats={"str": 18, "vit": 16},
        hp_multiplier=1.18,
        passives=(PASSIVES["pas_war_tough"],),
        skills=("war_heavy", "war_bash", "war_roar"),
        requirements={"level": 10, "str": 15},
    ),
    "mage": Archetype(
        "mage", "Маг", "🔮", 1,
        "Повелитель стихий и тайных знаний.",
        base_stats={"int": 19, "vit": 10},
        mp_multiplier=1.25,
        passives=(PASSIVES["pas_mag_flow"],),
        skills=("mag_fire", "mag_frost", "mag_shield"),
        requirements={"level": 10, "int": 15},
    ),
    "scout": Archetype(
        "scout", "Убийца", "🗡️", 1,
        "Мастер скрытных атак, полагающийся на яды и критические удары.",
        base_stats={"dex": 19, "luck": 14},
        passives=(PASSIVES["pas_sct_reflex"],),
        skills=("sct_shot", "sct_poison", "sct_dodge"),
        requirements={"level": 10, "dex": 15},
    ),
    "acolyte": Archetype(
        "acolyte", "Жрец", "⛪", 1,
        "Могущественный служитель богов, повелевающий силой исцеления.",
        base_stats={"int": 17, "vit": 14, "luck": 14},
        mp_multiplier=1.15,
        passives=(PASSIVES["pas_aco_faith"],),
        skills=("aco_smite", "aco_heal", "aco_bless"),
        requirements={"level": 10, "int": 12, "vit": 12},
    ),
    "guardian": Archetype(
        "guardian", "Страж", "🛡️", 2,
        "Воин, превративший защиту в оружие.",
        base_stats={"str": 34, "vit": 38},
        hp_multiplier=1.40,
        passives=(PASSIVES["pas_war_tough"], PASSIVES["pas_grd_bulwark"], PASSIVES["pas_grd_titan"]),
        skills=("grd_wall", "grd_crush", "war_bash"),
        requirements={"level": 50, "str": 28, "vit": 24},
    ),
    "berserker": Archetype(
        "berserker", "Берсерк", "🩸", 2,
        "Воин, который давит врага яростью и критами.",
        base_stats={"str": 46, "vit": 26},
        hp_multiplier=1.30,
        passives=(PASSIVES["pas_brs_frenzy"], PASSIVES["pas_brs_blood"]),
        skills=("brs_rend", "brs_fury", "war_heavy"),
        requirements={"level": 50, "str": 32},
    ),
    "pyromancer": Archetype(
        "pyromancer", "Пиромант", "🔥", 2,
        "Маг разрушительного огня.",
        base_stats={"int": 46, "luck": 18},
        mp_multiplier=1.40,
        passives=(PASSIVES["pas_mag_flow"], PASSIVES["pas_pyro_core"], PASSIVES["pas_pyro_burn"]),
        skills=("pyro_flame", "pyro_ember", "mag_fire"),
        requirements={"level": 50, "int": 32},
    ),
    "cryomancer": Archetype(
        "cryomancer", "Криомант", "❄️", 2,
        "Маг льда, контроля и выживания.",
        base_stats={"int": 38, "vit": 26},
        mp_multiplier=1.46,
        passives=(PASSIVES["pas_cryo_focus"], PASSIVES["pas_cryo_freeze"]),
        skills=("cryo_lance", "cryo_barrier", "mag_frost"),
        requirements={"level": 50, "int": 28, "vit": 18},
    ),
    "assassin": Archetype(
        "assassin", "Ассасин", "🗡️", 2,
        "Убийца, который заканчивает бой до ответного удара.",
        base_stats={"dex": 46, "luck": 34},
        passives=(PASSIVES["pas_sct_reflex"], PASSIVES["pas_ass_precision"], PASSIVES["pas_ass_mortal"]),
        skills=("ass_shadow", "ass_venom", "sct_shot"),
        requirements={"level": 50, "dex": 30, "luck": 20},
    ),
    "ranger": Archetype(
        "ranger", "Следопыт", "🏹", 2,
        "Охотник, который переживает врага скоростью.",
        base_stats={"dex": 50, "vit": 22},
        passives=(PASSIVES["pas_rng_reflex"], PASSIVES["pas_rng_focus"]),
        skills=("rng_mark", "rng_evasion", "sct_dodge"),
        requirements={"level": 50, "dex": 32},
    ),
    "paladin": Archetype(
        "paladin", "Паладин", "⚜️", 2,
        "Жрец в броне, держащий строй светом.",
        base_stats={"vit": 38, "int": 30, "str": 26},
        hp_multiplier=1.30,
        mp_multiplier=1.24,
        passives=(PASSIVES["pas_pal_oath"], PASSIVES["pas_pal_aegis"]),
        skills=("pal_smite", "pal_guard", "aco_bless"),
        requirements={"level": 50, "vit": 24, "int": 20},
    ),
    "prophet": Archetype(
        "prophet", "Пророк", "✨", 2,
        "Жрец чистой благодати и долгих боёв.",
        base_stats={"int": 42, "luck": 30},
        mp_multiplier=1.50,
        passives=(PASSIVES["pas_aco_faith"], PASSIVES["pas_prp_grace"], PASSIVES["pas_prp_blessing"]),
        skills=("prp_radiance", "prp_hymn", "aco_smite"),
        requirements={"level": 50, "int": 28, "luck": 18},
    ),
}
