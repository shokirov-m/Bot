"""Преданность наёмников: «hard mode» — заниженные дельты относительно классического ТЗ."""

from __future__ import annotations

# Подарок: было бы +5..+15 — режем примерно вдвое
GIFT_LOYALTY_DELTA = 3
# Победа в бою рядом с героем
BATTLE_WIN_LOYALTY = 1
# Диалог в Покоях (раз в сутки лимит снимается в сервисе)
DIALOG_LOYALTY = 1
# Снятие экипа / оскорбление — не используем в v1
WORK_SEND_LOYALTY_PENALTY = -1

LOYALTY_MIN = 0
LOYALTY_MAX = 100


def loyalty_stat_multiplier(loyalty: int) -> float:
    """Грубая кривая: 50+ даёт небольшой бонус к эффективности удара."""
    lv = max(LOYALTY_MIN, min(LOYALTY_MAX, int(loyalty)))
    if lv >= 80:
        return 1.12
    if lv >= 60:
        return 1.08
    if lv >= 40:
        return 1.04
    if lv < 20:
        return 0.92
    return 1.0
