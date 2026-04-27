"""
Числовой баланс: опыт, награды за бой, статы монстров.
Менять кривые — здесь, а не размазанно по модулям.
"""

from __future__ import annotations

# --- Прогрессия (уровни / зоны) ---
PROGRESSION_BASE_EXP = 80
PROGRESSION_LEVEL1_XP_NEEDED = 100
# После расчёта по формуле ТЗ делим порог (активно с уровня 2 → 3 и выше)
PROGRESSION_XP_NEED_DIVISOR_FROM_LEVEL_2 = 4

# Верхняя граница этажа зоны → множитель опыта (как в ТЗ)
ZONE_MULTIPLIER_BY_MAX_FLOOR: tuple[tuple[int, float], ...] = (
    (15, 1.0),
    (25, 2.5),
    (40, 4.0),
    (60, 7.0),
    (80, 12.0),
    (99, 20.0),
    (10_000, 25.0),
)

# --- Награды за победу (золото / опыт / шансы) ---
GOLD_BASE_OFFSET = 8
GOLD_PER_FLOOR = 3
GOLD_MAJOR_MULT = 8
GOLD_MAJOR_EXTRA_RANGE = (20, 80)
GOLD_MINI_MULT = 4
GOLD_MINI_EXTRA_RANGE = (10, 40)
GOLD_ELITE_MULT = 1.8
GOLD_ELITE_EXTRA_RANGE = (5, 20)
GOLD_NORMAL_EXTRA_RANGE = (0, 8)

XP_BASE_OFFSET = 12
XP_PER_FLOOR = 4
XP_MAJOR_MULT = 10
XP_MINI_MULT = 5
XP_ELITE_MULT = 2.2

RUNE_CHANCE_NORMAL = 0.04   # 4%
RUNE_CHANCE_ELITE  = 0.08   # 8%
RUNE_CHANCE_MINI   = 0.10   # 10%
RUNE_CHANCE_MAJOR  = 0.15   # 15%

# Доля золота, теряемая при смерти на этаже (после боя; не учебный бой).
DEATH_GOLD_LOSS_FRACTION = 0.10
# Верхний предел потери за одну смерть (после расчёта доли и обрезки по текущему балансу).
MAX_DEATH_GOLD_LOSS = 8_000

# Шанс дропа предмета: этажи 1-5 / этажи 6+  (+25–27 п.п. к исходным значениям)
DROP_CHANCE_FLOOR_LOW_MAX = 5

DROP_CHANCE_NORMAL_LOW  = 0.305   # 30.5%
DROP_CHANCE_ELITE_LOW   = 0.310   # 31.0%
DROP_CHANCE_MINI_LOW    = 0.340   # 34.0%
DROP_CHANCE_MAJOR_LOW   = 0.370   # 37.0%

DROP_CHANCE_NORMAL_HIGH = 0.270   # 27.0%
DROP_CHANCE_ELITE_HIGH  = 0.285   # 28.5%
DROP_CHANCE_MINI_HIGH   = 0.315   # 31.5%
DROP_CHANCE_MAJOR_HIGH  = 0.345   # 34.5%

# --- Базовые статы монстра (до множителей типа элита/босс) ---
MONSTER_HP_RAW_BASE = 72
MONSTER_HP_RAW_PER_FLOOR = 18
MONSTER_HP_CURVE_MULT = 1.95

MONSTER_ATK_RAW_BASE = 8
MONSTER_ATK_RAW_DIV_FLOOR = 2
MONSTER_ATK_CURVE_MULT = 1.55

MONSTER_DEF_BASE = 4
MONSTER_DEF_DIV_FLOOR = 4
MONSTER_DEF_CURVE_MULT = 1.45

MONSTER_MULT_ELITE_HP = 1.62
MONSTER_MULT_ELITE_ATK = 1.62
MONSTER_MULT_MINI_HP = 1.65
MONSTER_MULT_MINI_ATK = 1.35
MONSTER_MULT_MAJOR_HP = 2.1
MONSTER_MULT_MAJOR_ATK = 1.65

MONSTER_LATE_FLOOR_THRESHOLD = 90
MONSTER_LATE_HP_MULT = 1.15
MONSTER_LATE_ATK_MULT = 1.1

# Доп. усиление монстров с этажом (на каждый этаж выше 1-го)
MONSTER_FLOOR_POWER_PER_LEVEL = 0.0075
MONSTER_FLOOR_DEF_PER_LEVEL = 0.0045

# Сверх базовых кривых: рост с этажом ~×1,4 к ~10 этажу (1.035^9 ≈ 1.36), с потолком на высоких ярусах.
MONSTER_TOWER_SCALING_BASE = 1.035
MONSTER_TOWER_SCALING_CAP = 5.0

# Мини-босс на 5 этаже — дополнительно ×2,2 к атаке/защите (поверх множителя этажа); HP — фикс ниже.
MONSTER_FLOOR5_MINIBOSS_EXTRA_MULT = 2.2
# HP мини-босса 5-го этажа (волна «босс» на ×5, не ×10): явное значение для баланса ранней башни.
MONSTER_FLOOR5_MINIBOSS_HP_CAP = 550

# С 6-го этажа: к итоговым HP/атаке/защите врага (+mult за каждый этаж выше 5-го).
MONSTER_POST_FLOOR5_EXTRA_MULT_PER_FLOOR = 0.03

# Главный босс 10-го яруса — дополнительно ×2.5 к HP/атаке/защите (после прочих множителей).
MONSTER_FLOOR10_MAJOR_BOSS_MULT = 2.5

# Босс 20-го (Царь слизней, зона болот): ×3 к HP/атаке/защите; в бою — игнор брони 50 % и яд по ударам.
MONSTER_FLOOR20_SLIME_KING_TEMPLATE_KEY = "boss_slime_king"
MONSTER_FLOOR20_SLIME_KING_STAT_MULT = 3.0
MONSTER_FLOOR20_SLIME_KING_ARMOR_PENETRATION = 0.50

# С 12-го этажа: дополнительный множитель к HP всех врагов (атака без изменений).
MONSTER_HP_FLOOR12_MULT = 1.12
MONSTER_HP_FLOOR12_THRESHOLD = 12

# Этажи 18–19: дополнительная сложность (HP / атака / защита).
MONSTER_FLOOR18_19_MULT = 1.8
MONSTER_FLOOR18_19_FLOORS = frozenset({18, 19})

# Сумка: верхняя граница слота для проверок (фактически без лимита ячеек).
BAG_MAX_SLOT_INDEX = 9_999_999


def monster_tower_floor_strength_multiplier(floor_number: int) -> float:
    """Множитель силы врага от номера этажа (этаж 1 → 1.0)."""
    f = max(0, int(floor_number) - 1)
    raw = MONSTER_TOWER_SCALING_BASE**f
    return float(min(raw, MONSTER_TOWER_SCALING_CAP))

MONSTER_ATK_FLAT_NORMAL = 20
MONSTER_ATK_FLAT_ELITE = 30

# Итоговый урон монстра по игроку в бою: множатель к «base» до вычитания брони.
MONSTER_DAMAGE_DEALT_MULT = 1.12

# Доля брони игрока, которую удар монстра игнорирует (остальное вычитается из урона как раньше).
MONSTER_ARMOR_PENETRATION = 0.20
# Мини-босс и главный босс (в бою оба помечены is_mini_boss / is_major_boss).
MONSTER_ARMOR_PENETRATION_MAJOR_BOSS = 0.25

# Монстры масштабируются только этажем/типом спавна (см. combat_service._monster_stat_bundle).

# Плоский бонус к защите игрока от уровня (добавляется в бою поверх экипировки).
PLAYER_DEFENSE_BONUS_PER_LEVEL = 1


# ─── BALANCE V2: ребаланс ВЫН/ЛОВ/УДА (фаза 4.2) ──────────────────────────────
# Все коэффициенты, относящиеся к ребалансу, лежат здесь — чтобы откат был
# одной правкой (выставить флаг в False и/или вернуть значения).
# Ссылки в коде:
#   game/combat/formulas.py — crit/dodge/miss
#   services/character_service.py — _compute_hp_max
#   services/combat_service.py / engine.py — статус-сопротивление от ВЫН
BALANCE_V2_ENABLED: bool = True

# Удача: каждые 5 УДА = +1% крита, шапка повышена с 40% до 50%.
LUCK_CRIT_CAP: float = 0.50
LUCK_CRIT_PER_5: float = 0.01

# Ловкость:
#   - шапка уклонения 40 → 45
#   - база промаха 20 → 15 (минимум по-прежнему 3%)
DEX_DODGE_CAP: float = 0.45
DEX_DODGE_PER_5: float = 0.01
DEX_MISS_BASE: float = 0.15

# Выносливость:
#   - HP на ВЫН: было 6 → стало 4 (только для персонажей, чей HP пересчитывается:
#     новые/респек/арки. Старым игрокам hp_max не меняем).
#   - Долгие статусы: за каждые 10 ВЫН — −5% длительности кровотечения/яда,
#     до общей шапки −50%.
HP_PER_VIT: int = 4
VIT_STATUS_RESIST_PER_10: float = 0.05
VIT_STATUS_RESIST_CAP: float = 0.50


def vit_status_resist_fraction(vitality: int) -> float:
    """Доля сокращения длительности кровотечения/яда от ВЫН (0..0.50)."""
    if not BALANCE_V2_ENABLED:
        return 0.0
    raw = (max(0, int(vitality)) // 10) * float(VIT_STATUS_RESIST_PER_10)
    return min(float(VIT_STATUS_RESIST_CAP), raw)
