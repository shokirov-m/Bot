"""
Skill Tree Definitions for Archetypes 2.0.
Стоимость узлов растёт по глубине ветки (2→5 SP), чтобы нельзя было взять всё сразу.
"""
from __future__ import annotations
from game.archetypes.models import SkillTreeNode

_BUILTIN_TREES: dict[str, dict[str, SkillTreeNode]] = {
    "warrior": {
        # --- Guardian Branch ---
        "war_g1": SkillTreeNode(
            "war_g1",
            "💪 Крепкая хватка",
            "База защитной ветки: сила хвата помогает удерживать оружие и щит под ударом.",
            "stat_boost",
            {"str": 10},
            cost_sp=2,
        ),
        "war_g2": SkillTreeNode(
            "war_g2",
            "🛡️ Стойка защиты",
            "Пассивно укрепляет позицию: входящий урон по тебе немного снижается (бонус к защите).",
            "passive_bonus",
            {"def_bonus": 5.0},
            cost_sp=3,
            parent_keys=("war_g1",),
        ),
        "war_g3": SkillTreeNode(
            "war_g3",
            "🔨 Удар щитом",
            "Открывает активный навык: удар щитом с шансом оглушить врага.",
            "active_skill",
            "war_bash",
            cost_sp=4,
            parent_keys=("war_g2",),
        ),
        "war_g4": SkillTreeNode(
            "war_g4",
            "🦾 Несокрушимость",
            "Глубокая выдержка: заметно больше снижение входящего урона через защиту.",
            "passive_bonus",
            {"def_bonus": 15.0},
            cost_sp=5,
            parent_keys=("war_g3",),
        ),
        # --- Berserker Branch ---
        "war_b1": SkillTreeNode(
            "war_b1",
            "🔥 Ярость",
            "Натиск без компромиссов: все физические удары чуть сильнее.",
            "passive_bonus",
            {"atk_bonus_pct": 5},
            cost_sp=2,
        ),
        "war_b2": SkillTreeNode(
            "war_b2",
            "🪓 Тяжелый удар",
            "Открывает активный навык: медленный, но жёсткий удар с высоким множителем силы.",
            "active_skill",
            "war_heavy",
            cost_sp=3,
            parent_keys=("war_b1",),
        ),
        "war_b3": SkillTreeNode(
            "war_b3",
            "🩸 Жажда крови",
            "После ранения врага часть нанесённого урона возвращается тебе как HP.",
            "passive_bonus",
            {"lifesteal_percent": 5},
            cost_sp=4,
            parent_keys=("war_b2",),
        ),
        "war_b4": SkillTreeNode(
            "war_b4",
            "🌪️ Вихрь стали",
            "Финал ветки: активный навык с уроном по области (вихрь ударов).",
            "active_skill",
            "war_whirlwind",
            cost_sp=5,
            parent_keys=("war_b3",),
        ),
    },
    "mage": {
        # --- Elemental Branch ---
        "mag_e1": SkillTreeNode(
            "mag_e1",
            "🔥 Искра",
            "Первый шаг стихии: все заклинательские атаки немного сильнее.",
            "passive_bonus",
            {"mag_bonus_percent": 5},
            cost_sp=2,
        ),
        "mag_e2": SkillTreeNode(
            "mag_e2",
            "☄️ Огненный шар",
            "Открывает активный навык: огненный урон и шанс поджога.",
            "active_skill",
            "mag_fire",
            cost_sp=3,
            parent_keys=("mag_e1",),
        ),
        "mag_e3": SkillTreeNode(
            "mag_e3",
            "❄️ Обледенение",
            "Ледяная искра в ударе: при автоатаках и умениях иногда накладывает заморозку.",
            "passive_bonus",
            {"on_hit_freeze_chance": 0.1},
            cost_sp=4,
            parent_keys=("mag_e2",),
        ),
        "mag_e4": SkillTreeNode(
            "mag_e4",
            "🌨️ Ледяная стрела",
            "Открывает активный навык: ледяной болт с шансом замедлить или затормозить врага.",
            "active_skill",
            "mag_frost",
            cost_sp=5,
            parent_keys=("mag_e3",),
        ),
        # --- Arcane Branch ---
        "mag_a1": SkillTreeNode(
            "mag_a1",
            "🧠 Ясный ум",
            "Чистый запас интеллекта — основа маны и силы заклинаний.",
            "stat_boost",
            {"int": 10},
            cost_sp=2,
        ),
        "mag_a2": SkillTreeNode(
            "mag_a2",
            "🛡️ Энергощит",
            "Открывает активный навык: временный магический щит, гасящий часть входящего урона.",
            "active_skill",
            "mag_shield",
            cost_sp=3,
            parent_keys=("mag_a1",),
        ),
        "mag_a3": SkillTreeNode(
            "mag_a3",
            "🔄 Поток маны",
            "Узел контроля энергии: в начале каждого твоего хода восстанавливается +5 MP (складывается с другими источниками).",
            "passive_bonus",
            {"mp_regen_turn": 5},
            cost_sp=4,
            parent_keys=("mag_a2",),
        ),
        "mag_a4": SkillTreeNode(
            "mag_a4",
            "🌀 Чароплет",
            "Ещё один резерв маны: дополнительно +3 MP за ход (итого с «Потоком маны» — +8 MP/ход).",
            "passive_bonus",
            {"mp_regen_turn": 3},
            cost_sp=5,
            parent_keys=("mag_a3",),
        ),
    },
    "scout": {
        # --- Assassin Branch ---
        "sct_a1": SkillTreeNode(
            "sct_a1",
            "🗡️ Заточка",
            "Базовая точность клинка: выше шанс нанести критический удар.",
            "passive_bonus",
            {"crit_bonus": 0.05},
            cost_sp=2,
        ),
        "sct_a2": SkillTreeNode(
            "sct_a2",
            "🐍 Яд",
            "Открывает активный навык: наложение яда с периодическим уроном.",
            "active_skill",
            "sct_poison",
            cost_sp=3,
            parent_keys=("sct_a1",),
        ),
        "sct_a3": SkillTreeNode(
            "sct_a3",
            "👁️ Слабое место",
            "Учишься бить туда, где больнее: ещё +5% к шансу крита (в сумме с «Заточкой» — +10%).",
            "passive_bonus",
            {"crit_bonus": 0.05},
            cost_sp=4,
            parent_keys=("sct_a2",),
        ),
        "sct_a4": SkillTreeNode(
            "sct_a4",
            "💀 Удар в спину",
            "Открывает доступ к приёму «Точный выстрел» из ветки убийцы: высокий множитель и упор на крит (тот же боевой навык, что у следопыта, но узел из линии скрытности).",
            "active_skill",
            "sct_shot",
            cost_sp=5,
            parent_keys=("sct_a3",),
        ),
        # --- Ranger Branch ---
        "sct_r1": SkillTreeNode(
            "sct_r1",
            "👟 Легкость",
            "Подвижность на дистанции: проще увернуться от выпадов.",
            "passive_bonus",
            {"dodge_bonus": 0.05},
            cost_sp=2,
        ),
        "sct_r2": SkillTreeNode(
            "sct_r2",
            "🏹 Точный выстрел",
            "Открывает активный навык маршевого следопыта: один мощный выстрел с упором на критический эффект.",
            "active_skill",
            "sct_shot",
            cost_sp=3,
            parent_keys=("sct_r1",),
        ),
        "sct_r3": SkillTreeNode(
            "sct_r3",
            "🏃 Рефлексы",
            "Тренировка реакций — заметный прирост ловкости.",
            "stat_boost",
            {"dex": 10},
            cost_sp=4,
            parent_keys=("sct_r2",),
        ),
        "sct_r4": SkillTreeNode(
            "sct_r4",
            "💨 Увертливость",
            "Открывает активный навык: резкий рывок в сторону и большой временный бонус к уклонению.",
            "active_skill",
            "sct_dodge",
            cost_sp=5,
            parent_keys=("sct_r3",),
        ),
    },
    "acolyte": {
        # --- Light Branch ---
        "aco_l1": SkillTreeNode(
            "aco_l1",
            "🙏 Молитва",
            "Тихая поддержка света: каждый ход восстанавливаешь долю от максимального HP.",
            "passive_bonus",
            {"hp_regen_pct_turn": 0.02},
            cost_sp=2,
        ),
        "aco_l2": SkillTreeNode(
            "aco_l2",
            "✨ Исцеление",
            "Открывает активный навык: разовый мощный отлив HP за ману.",
            "active_skill",
            "aco_heal",
            cost_sp=3,
            parent_keys=("aco_l1",),
        ),
        "aco_l3": SkillTreeNode(
            "aco_l3",
            "🛡️ Святой щит",
            "Благословение укрепляет стойкость: немного больше защиты против физических ударов.",
            "passive_bonus",
            {"def_bonus": 5},
            cost_sp=4,
            parent_keys=("aco_l2",),
        ),
        "aco_l4": SkillTreeNode(
            "aco_l4",
            "🕊️ Благословение",
            "Открывает активный навык: длительное восстановление HP (HoT) на несколько ходов.",
            "active_skill",
            "aco_bless",
            cost_sp=5,
            parent_keys=("aco_l3",),
        ),
        # --- Wrath Branch ---
        "aco_w1": SkillTreeNode(
            "aco_w1",
            "⚖️ Справедливость",
            "Удача склоняется к тем, кто бьёт по нечести: прирост показателя удачи.",
            "stat_boost",
            {"luck": 10},
            cost_sp=2,
        ),
        "aco_w2": SkillTreeNode(
            "aco_w2",
            "💥 Кара",
            "Открывает активный навык «Кара» — быстрый магический удар светом по одной цели.",
            "active_skill",
            "aco_smite",
            cost_sp=3,
            parent_keys=("aco_w1",),
        ),
        "aco_w3": SkillTreeNode(
            "aco_w3",
            "🔥 Гнев",
            "Свет не только лечит: все магические атаки заметно усилены.",
            "passive_bonus",
            {"mag_bonus_percent": 10},
            cost_sp=4,
            parent_keys=("aco_w2",),
        ),
        "aco_w4": SkillTreeNode(
            "aco_w4",
            "⚡ Возмездие",
            "Вершина карательной ветви: тот же активный навык «Кара», но узел отражает гневную школу — выше урон за счёт предыдущих пассивов ветки (один слот в бою, эффект суммируется с маг. бонусами).",
            "active_skill",
            "aco_smite",
            cost_sp=5,
            parent_keys=("aco_w3",),
        ),
    },
    "necromancer": {
        "nec_n1": SkillTreeNode(
            "nec_n1",
            "💀 Костяной резонанс",
            "Сила нежити в отряде растёт.",
            "passive_bonus",
            {"companion_atk_pct": 8},
            cost_sp=2,
        ),
        "nec_n2": SkillTreeNode(
            "nec_n2",
            "🛡️ Страж склепа",
            "Укрепляет призванных танков.",
            "stat_boost",
            {"vit": 8},
            cost_sp=3,
            parent_keys=("nec_n1",),
        ),
        "nec_n3": SkillTreeNode(
            "nec_n3",
            "🔮 Пепельный культ",
            "Открывает пепельного культиста в ковчеге.",
            "passive_bonus",
            {"mag_bonus_percent": 10},
            cost_sp=4,
            parent_keys=("nec_n2",),
        ),
        "nec_n4": SkillTreeNode(
            "nec_n4",
            "⚡ Плеть душ",
            "Усиленная тёмная магия.",
            "active_skill",
            "nec_bolt",
            cost_sp=5,
            parent_keys=("nec_n3",),
        ),
        "nec_n5": SkillTreeNode(
            "nec_n5",
            "🛡️ Защитный барьер",
            "Щит из тёмной энергии: сила растёт с интеллектом.",
            "active_skill",
            "nec_barrier",
            cost_sp=4,
            parent_keys=("nec_n2",),
        ),
    },
}


def _load_trees() -> dict[str, dict[str, SkillTreeNode]]:
    merged = dict(_BUILTIN_TREES)
    try:
        from game.data.catalogs.archetypes_catalog import catalog_trees

        cat = catalog_trees()
        if cat:
            for arch, nodes in cat.items():
                base = dict(merged.get(arch, {}))
                base.update(nodes)
                merged[arch] = base
    except Exception:
        pass
    return merged


# JSON-каталог перекрывает узлы Python при совпадении ключей архетипа/узла.
TREES: dict[str, dict[str, SkillTreeNode]] = _load_trees()
