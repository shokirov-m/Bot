"""
Шаблоны ежедневных заданий по уровням (тирам).

Тир определяется по максимальному достигнутому этажу персонажа:
  Тир 1: этаж 1–10   (начинающий)
  Тир 2: этаж 11–20  (болота)
  Тир 3: этаж 21–30  (пещеры теней)
  Тир 4: этаж 31–50  (средние уровни)
  Тир 5: этаж 51–100 (высшие уровни)

Каждый тир содержит пул шаблонов.
Каждый день система выбирает 3 задания из пула (детерминировано по дате + character_id).

Типы заданий:
  kills_any   — убить N любых монстров
  kills_elite — убить N элитных монстров
  kills_boss  — победить N боссов (мини или мажор)
  battles_win — выиграть N боёв (любые)
  earn_gold   — собрать N золота в боях

Награды (gold, xp, rune_stones):
  Чем выше тир — тем жирнее.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DailyQuestTemplate:
    key: str          # уникальный ключ шаблона
    title: str        # заголовок
    desc: str         # описание (отображается игроку)
    type: str         # kills_any | kills_elite | kills_boss | battles_win | earn_gold
    target: int       # цель
    reward_gold: int
    reward_xp: int
    reward_rune: int  # рунные камни (0 = не выдаём)


# ── Тир 1: Этажи 1–10 ─────────────────────────────────────────────────────────
TIER_1: list[DailyQuestTemplate] = [
    DailyQuestTemplate("dq_t1_k5",   "Первые шаги",       "Победи 5 монстров в башне.",          "kills_any",   5,  90,  45, 0),
    DailyQuestTemplate("dq_t1_k10",  "Охотник новобранец","Победи 10 монстров в башне.",          "kills_any",  10, 140,  70, 0),
    DailyQuestTemplate("dq_t1_k15",  "Истребитель",       "Победи 15 монстров в башне.",          "kills_any",  15, 200, 100, 0),
    DailyQuestTemplate("dq_t1_e2",   "Вызов элите",       "Победи 2 элитных монстра.",            "kills_elite", 2, 130,  65, 0),
    DailyQuestTemplate("dq_t1_e3",   "Охота на сильнейших","Победи 3 элитных монстра.",           "kills_elite", 3, 170,  85, 0),
    DailyQuestTemplate("dq_t1_b1",   "Падение босса",     "Победи 1 мини-босса или босса.",       "kills_boss",  1, 160,  80, 0),
    DailyQuestTemplate("dq_t1_w8",   "Серия побед",       "Выиграй 8 боёв.",                     "battles_win", 8, 110,  55, 0),
    DailyQuestTemplate("dq_t1_g200", "Сборщик монет",     "Собери 200 золота в боях.",            "earn_gold", 200, 120,  60, 0),
]

# ── Тир 2: Этажи 11–20 ────────────────────────────────────────────────────────
TIER_2: list[DailyQuestTemplate] = [
    DailyQuestTemplate("dq_t2_k10",  "Болотный охотник",  "Победи 10 монстров болот.",            "kills_any",  10, 200, 100, 0),
    DailyQuestTemplate("dq_t2_k20",  "Чистильщик болот",  "Победи 20 монстров в башне.",          "kills_any",  20, 280, 140, 0),
    DailyQuestTemplate("dq_t2_k25",  "Опытный истребитель","Победи 25 монстров в башне.",         "kills_any",  25, 360, 180, 0),
    DailyQuestTemplate("dq_t2_e3",   "Охота на элиту",    "Победи 3 элитных монстра.",            "kills_elite", 3, 230, 115, 0),
    DailyQuestTemplate("dq_t2_e5",   "Элитный истребитель","Победи 5 элитных монстров.",          "kills_elite", 5, 330, 165, 0),
    DailyQuestTemplate("dq_t2_b2",   "Двойной удар",      "Победи 2 мини-боссов или боссов.",     "kills_boss",  2, 310, 155, 0),
    DailyQuestTemplate("dq_t2_b3",   "Охотник на боссов", "Победи 3 боссов (мини или мажор).",    "kills_boss",  3, 420, 210, 1),
    DailyQuestTemplate("dq_t2_w15",  "Боевая серия",      "Выиграй 15 боёв.",                    "battles_win",15, 250, 125, 0),
    DailyQuestTemplate("dq_t2_g500", "Золотая жила",      "Собери 500 золота в боях.",            "earn_gold", 500, 260, 130, 0),
]

# ── Тир 3: Этажи 21–30 ────────────────────────────────────────────────────────
TIER_3: list[DailyQuestTemplate] = [
    DailyQuestTemplate("dq_t3_k15",  "Следопыт теней",    "Победи 15 монстров Пещер Теней.",     "kills_any",  15, 310, 155, 0),
    DailyQuestTemplate("dq_t3_k25",  "Тенеборец",         "Победи 25 монстров в башне.",          "kills_any",  25, 430, 215, 0),
    DailyQuestTemplate("dq_t3_k35",  "Истребитель теней", "Победи 35 монстров в башне.",          "kills_any",  35, 560, 280, 1),
    DailyQuestTemplate("dq_t3_e4",   "Охота в темноте",   "Победи 4 элитных монстра.",            "kills_elite", 4, 340, 170, 0),
    DailyQuestTemplate("dq_t3_e6",   "Элита во тьме",     "Победи 6 элитных монстров.",           "kills_elite", 6, 480, 240, 1),
    DailyQuestTemplate("dq_t3_b2",   "Тёмный охотник",    "Победи 2 боссов.",                     "kills_boss",  2, 420, 210, 1),
    DailyQuestTemplate("dq_t3_b3",   "Падение теней",     "Победи 3 боссов.",                     "kills_boss",  3, 560, 280, 2),
    DailyQuestTemplate("dq_t3_w20",  "Боевой марш",       "Выиграй 20 боёв.",                    "battles_win",20, 370, 185, 0),
    DailyQuestTemplate("dq_t3_g800", "Добытчик пещер",    "Собери 800 золота в боях.",            "earn_gold", 800, 400, 200, 0),
]

# ── Тир 4: Этажи 31–50 ────────────────────────────────────────────────────────
TIER_4: list[DailyQuestTemplate] = [
    DailyQuestTemplate("dq_t4_k20",  "Воин среднего яруса","Победи 20 монстров.",                 "kills_any",  20, 460, 230, 0),
    DailyQuestTemplate("dq_t4_k35",  "Ветеран башни",      "Победи 35 монстров.",                  "kills_any",  35, 650, 325, 1),
    DailyQuestTemplate("dq_t4_k50",  "Покоритель ярусов",  "Победи 50 монстров.",                  "kills_any",  50, 860, 430, 2),
    DailyQuestTemplate("dq_t4_e5",   "Охота на чемпионов", "Победи 5 элитных монстров.",           "kills_elite", 5, 520, 260, 1),
    DailyQuestTemplate("dq_t4_e8",   "Чемпионская охота",  "Победи 8 элитных монстров.",           "kills_elite", 8, 740, 370, 2),
    DailyQuestTemplate("dq_t4_b3",   "Убийца боссов",      "Победи 3 боссов.",                     "kills_boss",  3, 650, 325, 2),
    DailyQuestTemplate("dq_t4_b4",   "Гроза башни",        "Победи 4 боссов.",                     "kills_boss",  4, 860, 430, 3),
    DailyQuestTemplate("dq_t4_w25",  "Боевой поток",       "Выиграй 25 боёв.",                    "battles_win",25, 560, 280, 1),
    DailyQuestTemplate("dq_t4_g1500","Золотой охотник",    "Собери 1500 золота в боях.",           "earn_gold",1500, 580, 290, 1),
]

# ── Тир 5: Этажи 51–100 ───────────────────────────────────────────────────────
TIER_5: list[DailyQuestTemplate] = [
    DailyQuestTemplate("dq_t5_k30",  "Ветеран высших ярусов","Победи 30 монстров.",                "kills_any",  30, 740, 370, 2),
    DailyQuestTemplate("dq_t5_k50",  "Легенда башни",        "Победи 50 монстров.",                "kills_any",  50,1050, 525, 3),
    DailyQuestTemplate("dq_t5_k70",  "Непобедимый",          "Победи 70 монстров.",                "kills_any",  70,1360, 680, 3),
    DailyQuestTemplate("dq_t5_e6",   "Охотник за элитой",    "Победи 6 элитных монстров.",         "kills_elite", 6, 800, 400, 2),
    DailyQuestTemplate("dq_t5_e10",  "Истребитель чемпионов","Победи 10 элитных монстров.",        "kills_elite",10,1200, 600, 3),
    DailyQuestTemplate("dq_t5_b4",   "Падение колоссов",     "Победи 4 боссов.",                   "kills_boss",  4,1050, 525, 3),
    DailyQuestTemplate("dq_t5_b5",   "Покоритель боссов",    "Победи 5 боссов.",                   "kills_boss",  5,1360, 680, 4),
    DailyQuestTemplate("dq_t5_w30",  "Неудержимый воин",     "Выиграй 30 боёв.",                   "battles_win",30, 860, 430, 2),
    DailyQuestTemplate("dq_t5_g3000","Золотой легион",       "Собери 3000 золота в боях.",         "earn_gold",3000, 920, 460, 3),
]

# ── Словарь: тир → пул ────────────────────────────────────────────────────────
_TIER_POOLS: dict[int, list[DailyQuestTemplate]] = {
    1: TIER_1,
    2: TIER_2,
    3: TIER_3,
    4: TIER_4,
    5: TIER_5,
}


def tier_for_floor(highest_floor: int) -> int:
    """Возвращает номер тира по максимальному достигнутому этажу."""
    f = int(highest_floor)
    if f <= 10:
        return 1
    if f <= 20:
        return 2
    if f <= 30:
        return 3
    if f <= 50:
        return 4
    return 5


def pool_for_tier(tier: int) -> list[DailyQuestTemplate]:
    return _TIER_POOLS.get(tier, TIER_1)


def type_label(quest_type: str) -> str:
    return {
        "kills_any":   "🗡️ Убийства",
        "kills_elite": "⚡ Элита",
        "kills_boss":  "👑 Боссы",
        "battles_win": "⚔️ Победы",
        "earn_gold":   "💰 Золото",
    }.get(quest_type, quest_type)
