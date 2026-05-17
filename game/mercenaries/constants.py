"""Экономика и пороги чёрного рынка «Тени Башни»."""

from __future__ import annotations

BLACK_MARKET_PRICE_MULT = 10
MARKET_MIN_LEVEL = 1
MARKET_ENTRY_COST_GOLD = 300
MARKET_FLOOR = 26

FEATURE_BLACK_MARKET_COMBAT = True

# Боевой множитель наёмников (к итоговым HP/ATK в бою).
# Используется только в боевых расчётах; «база в карточке» (поля Mercenary.hp_max/atk) не меняется.
MERC_COMBAT_POWER_MULT = 5.0

# Покои наёмников: подарок (раз в сутки UTC, +преданность из mercenary_loyalty)
MERC_QUARTERS_GIFT_GOLD = 250

# Тренировка: раз в сутки UTC, рост базовых статов в БД
MERC_TRAIN_GOLD = 120
MERC_TRAIN_ATK_ADD = 2
MERC_TRAIN_HP_ADD = 4
MERC_TRAIN_LOYALTY = 1

# Экипировка: уровни в merc.extra (даёт плоский бонус в бою)
MERC_GEAR_BLADE_MAX = 5
MERC_GEAR_ARMOR_MAX = 5
MERC_GEAR_BLADE_ATK_EACH = 4
MERC_GEAR_ARMOR_HP_EACH = 15


def merc_gear_blade_upgrade_cost(current_lv: int) -> int:
    lv = max(0, min(MERC_GEAR_BLADE_MAX - 1, int(current_lv)))
    return 260 + lv * 130


def merc_gear_armor_upgrade_cost(current_lv: int) -> int:
    lv = max(0, min(MERC_GEAR_ARMOR_MAX - 1, int(current_lv)))
    return 220 + lv * 110


# Работа (оффлайн-таймер): длительность и награда при сдаче
MERC_WORK_DURATION_SEC = 2 * 3600  # 2 часа
MERC_WORK_GOLD_BASE = 72
MERC_WORK_GOLD_PER_LEVEL = 11
MERC_WORK_LOYALTY_CLAIM = 1

# Опыт наёмников за победу в башне: доля отнимается у героя и копится в merc.extra
MERC_EXTRA_XP_KEY = "merc_xp"
# XP до уровня — та же кривая, что у героя (experience_needed_for_next_level).
MERC_XP_LEVEL_NEED_MULT = 1.0
# Кап уровня наёмника отключён (практически без лимита).
MERC_MAX_LEVELS_ABOVE_HERO = 9999
# Прирост карточных статов за уровень (как при генерации лота в mercenary_data).
MERC_PER_LEVEL_HP = 8
MERC_PER_LEVEL_ATK = 2
