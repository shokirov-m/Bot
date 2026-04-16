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

RUNE_CHANCE_NORMAL = 0.04
RUNE_CHANCE_ELITE = 0.12
RUNE_CHANCE_MINI = 0.22
RUNE_CHANCE_MAJOR = 0.45

DROP_CHANCE_NORMAL = 0.15
DROP_CHANCE_ELITE = 0.28
DROP_CHANCE_MINI = 0.40
DROP_CHANCE_MAJOR = 0.65

# --- Базовые статы монстра (до множителей типа элита/босс) ---
MONSTER_HP_RAW_BASE = 36
MONSTER_HP_RAW_PER_FLOOR = 9
MONSTER_HP_CURVE_MULT = 1.95

MONSTER_ATK_RAW_BASE = 4
MONSTER_ATK_RAW_DIV_FLOOR = 2
MONSTER_ATK_CURVE_MULT = 1.55

MONSTER_DEF_BASE = 2
MONSTER_DEF_DIV_FLOOR = 4
MONSTER_DEF_CURVE_MULT = 1.45

MONSTER_MULT_ELITE_HP = 1.5
MONSTER_MULT_ELITE_ATK = 1.5
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

# Мини-босс на 5 этаже — дополнительно ×2,2 к HP/атаке/защите (поверх множителя этажа).
MONSTER_FLOOR5_MINIBOSS_EXTRA_MULT = 2.2

# С 6-го этажа: к итоговым HP/атаке/защите врага (+mult за каждый этаж выше 5-го).
MONSTER_POST_FLOOR5_EXTRA_MULT_PER_FLOOR = 0.03

# Главный босс 10-го яруса — дополнительно ×2.5 к HP/атаке/защите (после прочих множителей).
MONSTER_FLOOR10_MAJOR_BOSS_MULT = 2.5

# Сумка: верхняя граница слота для проверок (фактически без лимита ячеек).
BAG_MAX_SLOT_INDEX = 9_999_999


def monster_tower_floor_strength_multiplier(floor_number: int) -> float:
    """Множитель силы врага от номера этажа (этаж 1 → 1.0)."""
    f = max(0, int(floor_number) - 1)
    raw = MONSTER_TOWER_SCALING_BASE**f
    return float(min(raw, MONSTER_TOWER_SCALING_CAP))

MONSTER_ATK_FLAT_NORMAL = 20
MONSTER_ATK_FLAT_ELITE = 30

# --- Масштаб монстров от уровня персонажа (кроме учебного боя) ---
# На каждый уровень героя выше 1-го: чуть больше HP / атака / защита врага.
MONSTER_PLAYER_LEVEL_HP_PER_LEVEL = 0.022
MONSTER_PLAYER_LEVEL_ATK_PER_LEVEL = 0.018
MONSTER_PLAYER_LEVEL_DEF_PER_LEVEL = 0.012

# Плоский бонус к защите игрока от уровня (добавляется в бою поверх экипировки).
PLAYER_DEFENSE_BONUS_PER_LEVEL = 1
