"""
Skill Tree Definitions for Archetypes 2.0.
Стоимость узлов растёт по глубине ветки (2→5 SP), чтобы нельзя было взять всё сразу.
"""
from __future__ import annotations
from game.archetypes.models import SkillTreeNode

TREES: dict[str, dict[str, SkillTreeNode]] = {
    "warrior": {
        # --- Guardian Branch ---
        "war_g1": SkillTreeNode("war_g1", "💪 Крепкая хватка", "+10 СИЛ.", "stat_boost", {"str": 10}, cost_sp=2),
        "war_g2": SkillTreeNode(
            "war_g2", "🛡️ Стойка защиты", "Снижает урон.", "passive_bonus", {"def_bonus": 5.0},
            cost_sp=3, parent_keys=("war_g1",),
        ),
        "war_g3": SkillTreeNode(
            "war_g3", "🔨 Удар щитом", "Шанс оглушения.", "active_skill", "war_bash",
            cost_sp=4, parent_keys=("war_g2",),
        ),
        "war_g4": SkillTreeNode(
            "war_g4", "🦾 Несокрушимость", "+15% к защите.", "passive_bonus", {"def_bonus": 15.0},
            cost_sp=5, parent_keys=("war_g3",),
        ),
        # --- Berserker Branch ---
        "war_b1": SkillTreeNode("war_b1", "🔥 Ярость", "+5% к урону.", "passive_bonus", {"atk_bonus_pct": 5}, cost_sp=2),
        "war_b2": SkillTreeNode(
            "war_b2", "🪓 Тяжелый удар", "Мощная атака.", "active_skill", "war_heavy",
            cost_sp=3, parent_keys=("war_b1",),
        ),
        "war_b3": SkillTreeNode(
            "war_b3", "🩸 Жажда крови", "Исцеление при убийстве.", "passive_bonus", {"lifesteal_percent": 5},
            cost_sp=4, parent_keys=("war_b2",),
        ),
        "war_b4": SkillTreeNode(
            "war_b4", "🌪️ Вихрь стали", "Сильный урон.", "active_skill", "war_whirlwind",
            cost_sp=5, parent_keys=("war_b3",),
        ),
    },
    "mage": {
        # --- Elemental Branch ---
        "mag_e1": SkillTreeNode("mag_e1", "🔥 Искра", "+5% маг. урона.", "passive_bonus", {"mag_bonus_percent": 5}, cost_sp=2),
        "mag_e2": SkillTreeNode(
            "mag_e2", "☄️ Огненный шар", "Поджигает цель.", "active_skill", "mag_fire",
            cost_sp=3, parent_keys=("mag_e1",),
        ),
        "mag_e3": SkillTreeNode(
            "mag_e3", "❄️ Обледенение", "Шанс заморозки.", "passive_bonus", {"on_hit_freeze_chance": 0.1},
            cost_sp=4, parent_keys=("mag_e2",),
        ),
        "mag_e4": SkillTreeNode(
            "mag_e4", "🌨️ Ледяная стрела", "Замедляет врага.", "active_skill", "mag_frost",
            cost_sp=5, parent_keys=("mag_e3",),
        ),
        # --- Arcane Branch ---
        "mag_a1": SkillTreeNode("mag_a1", "🧠 Ясный ум", "+10 ИНТ.", "stat_boost", {"int": 10}, cost_sp=2),
        "mag_a2": SkillTreeNode(
            "mag_a2", "🛡️ Энергощит", "Поглощает урон.", "active_skill", "mag_shield",
            cost_sp=3, parent_keys=("mag_a1",),
        ),
        "mag_a3": SkillTreeNode(
            "mag_a3", "🔄 Поток маны", "+5 MP реген.", "passive_bonus", {"mp_regen_turn": 5},
            cost_sp=4, parent_keys=("mag_a2",),
        ),
        "mag_a4": SkillTreeNode(
            "mag_a4", "🌀 Чароплет", "+3 реген маны за ход.", "passive_bonus", {"mp_regen_turn": 3},
            cost_sp=5, parent_keys=("mag_a3",),
        ),
    },
    "scout": {
        # --- Assassin Branch ---
        "sct_a1": SkillTreeNode("sct_a1", "🗡️ Заточка", "+5% шанс крита.", "passive_bonus", {"crit_bonus": 0.05}, cost_sp=2),
        "sct_a2": SkillTreeNode(
            "sct_a2", "🐍 Яд", "Наносит урон ядом.", "active_skill", "sct_poison",
            cost_sp=3, parent_keys=("sct_a1",),
        ),
        "sct_a3": SkillTreeNode(
            "sct_a3", "👁️ Слабое место", "+5% шанс крита.", "passive_bonus", {"crit_bonus": 0.05},
            cost_sp=4, parent_keys=("sct_a2",),
        ),
        "sct_a4": SkillTreeNode(
            "sct_a4", "💀 Удар в спину", "Критический урон.", "active_skill", "sct_shot",
            cost_sp=5, parent_keys=("sct_a3",),
        ),
        # --- Ranger Branch ---
        "sct_r1": SkillTreeNode("sct_r1", "👟 Легкость", "+5% уклонения.", "passive_bonus", {"dodge_bonus": 0.05}, cost_sp=2),
        "sct_r2": SkillTreeNode(
            "sct_r2", "🏹 Точный выстрел", "Сильный выстрел.", "active_skill", "sct_shot",
            cost_sp=3, parent_keys=("sct_r1",),
        ),
        "sct_r3": SkillTreeNode(
            "sct_r3", "🏃 Рефлексы", "+10 ЛОВ.", "stat_boost", {"dex": 10},
            cost_sp=4, parent_keys=("sct_r2",),
        ),
        "sct_r4": SkillTreeNode(
            "sct_r4", "💨 Увертливость", "Бафф уклонения.", "active_skill", "sct_dodge",
            cost_sp=5, parent_keys=("sct_r3",),
        ),
    },
    "acolyte": {
        # --- Light Branch ---
        "aco_l1": SkillTreeNode("aco_l1", "🙏 Молитва", "+5 реген HP за ход.", "passive_bonus", {"hp_regen_pct_turn": 0.02}, cost_sp=2),
        "aco_l2": SkillTreeNode(
            "aco_l2", "✨ Исцеление", "Восстанавливает HP.", "active_skill", "aco_heal",
            cost_sp=3, parent_keys=("aco_l1",),
        ),
        "aco_l3": SkillTreeNode(
            "aco_l3", "🛡️ Святой щит", "+5 защиты.", "passive_bonus", {"def_bonus": 5},
            cost_sp=4, parent_keys=("aco_l2",),
        ),
        "aco_l4": SkillTreeNode(
            "aco_l4", "🕊️ Благословение", "Реген HP/MP.", "active_skill", "aco_bless",
            cost_sp=5, parent_keys=("aco_l3",),
        ),
        # --- Wrath Branch ---
        "aco_w1": SkillTreeNode("aco_w1", "⚖️ Справедливость", "+10 УДА.", "stat_boost", {"luck": 10}, cost_sp=2),
        "aco_w2": SkillTreeNode(
            "aco_w2", "💥 Кара", "Урон светом.", "active_skill", "aco_smite",
            cost_sp=3, parent_keys=("aco_w1",),
        ),
        "aco_w3": SkillTreeNode(
            "aco_w3", "🔥 Гнев", "+10% маг. урона.", "passive_bonus", {"mag_bonus_percent": 10},
            cost_sp=4, parent_keys=("aco_w2",),
        ),
        "aco_w4": SkillTreeNode(
            "aco_w4", "⚡ Возмездие", "Сильный урон.", "active_skill", "aco_smite",
            cost_sp=5, parent_keys=("aco_w3",),
        ),
    },
}
