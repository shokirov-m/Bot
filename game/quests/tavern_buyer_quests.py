"""
Цепочки заданий от Скупщика в таверне.

Скупщик Орин — торговец, который скупает трофеи с монстров.
Есть в каждом городском хабе (этажи 3, 31, 61, 91).
Даёт 3-шаговую цепочку. Финальная награда — кольцо/амулет.

Шаги:
  1) Победи N монстров (любых)    (kills_any)
  2) Заработай N золота в боях    (earn_gold)
  3) Убей N элитных монстров      (kills_elite)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuyerQuestStep:
    step: int
    title: str
    desc: str
    quest_type: str    # kills_any | earn_gold | kills_elite | kills_boss | battles_win
    target: int
    reward_gold: int
    reward_xp: int
    reward_fame: int


@dataclass(frozen=True, slots=True)
class BuyerQuestChain:
    hub_floor: int
    npc_name: str
    npc_emoji: str
    chain_title: str
    intro: str
    steps: tuple[BuyerQuestStep, ...]
    final_gold: int
    final_xp: int
    final_fame: int
    final_item: dict
    final_text: str


# ── Хаб 3: Скупщик Орин ───────────────────────────────────────────────────────
_CHAIN_3 = BuyerQuestChain(
    hub_floor=3,
    npc_name="Скупщик Орин",
    npc_emoji="🪙",
    chain_title="Первые поставки",
    intro=(
        "— О, новый герой! Я Орин, скупщик редкостей.\n"
        "Мне нужны трофеи, золото и... интересные клиенты.\n"
        "Выполни три поручения — и получишь кое-что ценное из моей коллекции."
    ),
    steps=(
        BuyerQuestStep(
            step=1,
            title="Первые трофеи",
            desc="Убей 5 монстров в башне.",
            quest_type="kills_any",
            target=5,
            reward_gold=60,
            reward_xp=35,
            reward_fame=4,
        ),
        BuyerQuestStep(
            step=2,
            title="Наполни кошелёк",
            desc="Заработай 200 золота в боях.",
            quest_type="earn_gold",
            target=200,
            reward_gold=80,
            reward_xp=45,
            reward_fame=6,
        ),
        BuyerQuestStep(
            step=3,
            title="Редкий товар",
            desc="Победи 2 элитных монстра.",
            quest_type="kills_elite",
            target=2,
            reward_gold=100,
            reward_xp=60,
            reward_fame=8,
        ),
    ),
    final_gold=150,
    final_xp=100,
    final_fame=12,
    final_item={
        "name": "Кольцо удачи Орина",
        "kind": "ring",
        "rarity": "uncommon",
        "luck": 5,
        "dex": 2,
        "image_url": "",
        "desc": "Особое кольцо от скупщика Орина. Удача любит таких, как ты.",
    },
    final_text=(
        "— Ха! Ты справился лучше, чем я ожидал.\n"
        "Это кольцо я берёг для особого клиента. Похоже, это ты.\n"
        "Заходи ещё — у Орина всегда найдётся работа."
    ),
)

# ── Хаб 31: Скупщик Орин в Айронфолле ────────────────────────────────────────
_CHAIN_31 = BuyerQuestChain(
    hub_floor=31,
    npc_name="Скупщик Орин",
    npc_emoji="🪙",
    chain_title="Выгодная торговля",
    intro=(
        "— А, снова ты! Значит, добрался до Айронфолла.\n"
        "Тут у меня особые заказчики — им нужны серьёзные трофеи.\n"
        "Три задания. Сложнее, чем раньше. Но и награда лучше."
    ),
    steps=(
        BuyerQuestStep(
            step=1,
            title="Улов среднего яруса",
            desc="Убей 10 монстров в башне.",
            quest_type="kills_any",
            target=10,
            reward_gold=160,
            reward_xp=110,
            reward_fame=10,
        ),
        BuyerQuestStep(
            step=2,
            title="Серьёзный капитал",
            desc="Заработай 600 золота в боях.",
            quest_type="earn_gold",
            target=600,
            reward_gold=200,
            reward_xp=140,
            reward_fame=14,
        ),
        BuyerQuestStep(
            step=3,
            title="Трофеи с чемпионов",
            desc="Победи 4 элитных монстра.",
            quest_type="kills_elite",
            target=4,
            reward_gold=260,
            reward_xp=180,
            reward_fame=18,
        ),
    ),
    final_gold=350,
    final_xp=250,
    final_fame=22,
    final_item={
        "name": "Амулет скупщика",
        "kind": "amulet",
        "rarity": "rare",
        "luck": 8,
        "dex": 3,
        "int": 2,
        "image_url": "",
        "desc": "Амулет с рынка Айронфолла. Торговцы чуют удачу за версту.",
    },
    final_text=(
        "— Отличная работа. Мои заказчики довольны.\n"
        "Этот амулет — из партии редких товаров с верхних ярусов.\n"
        "Носи с пользой."
    ),
)

# ── Хаб 61: Скупщик Орин в Эмберхолле ────────────────────────────────────────
_CHAIN_61 = BuyerQuestChain(
    hub_floor=61,
    npc_name="Скупщик Орин",
    npc_emoji="🪙",
    chain_title="Огненный рынок",
    intro=(
        "— Ты дошёл до Эмберхолла! Я уже слышал о твоих подвигах.\n"
        "Огненный рынок — особое место. Здесь ценятся только лучшие трофеи.\n"
        "Три задания. Покажи, чего ты стоишь."
    ),
    steps=(
        BuyerQuestStep(
            step=1,
            title="Охота в огненной зоне",
            desc="Убей 15 монстров в башне.",
            quest_type="kills_any",
            target=15,
            reward_gold=350,
            reward_xp=260,
            reward_fame=18,
        ),
        BuyerQuestStep(
            step=2,
            title="Огненное золото",
            desc="Заработай 1200 золота в боях.",
            quest_type="earn_gold",
            target=1200,
            reward_gold=450,
            reward_xp=330,
            reward_fame=24,
        ),
        BuyerQuestStep(
            step=3,
            title="Чемпионы огня",
            desc="Победи 6 элитных монстров.",
            quest_type="kills_elite",
            target=6,
            reward_gold=560,
            reward_xp=420,
            reward_fame=30,
        ),
    ),
    final_gold=600,
    final_xp=450,
    final_fame=32,
    final_item={
        "name": "Шлем торговца",
        "kind": "helmet",
        "rarity": "rare",
        "defense": 15,
        "dex": 4,
        "luck": 6,
        "image_url": "",
        "desc": "Шлем с огненными рунами. Торговцы Эмберхолла ценят острый ум.",
    },
    final_text=(
        "— Превосходно. Огненный рынок принял тебя.\n"
        "Этот шлем привезли с самого верхнего яруса — специально для тебя."
    ),
)

# ── Хаб 91: Скупщик Орин в Этернисе ──────────────────────────────────────────
_CHAIN_91 = BuyerQuestChain(
    hub_floor=91,
    npc_name="Скупщик Орин",
    npc_emoji="🪙",
    chain_title="Печать Вечности",
    intro=(
        "— Этернис. Я не думал, что ты доберётся сюда, герой.\n"
        "Последняя цепочка. Самая сложная. Но и награда — легендарная.\n"
        "Это последнее задание Орина для тебя. Сделай его."
    ),
    steps=(
        BuyerQuestStep(
            step=1,
            title="Бойня у врат",
            desc="Убей 20 монстров в башне.",
            quest_type="kills_any",
            target=20,
            reward_gold=700,
            reward_xp=550,
            reward_fame=30,
        ),
        BuyerQuestStep(
            step=2,
            title="Золото вечности",
            desc="Заработай 2000 золота в боях.",
            quest_type="earn_gold",
            target=2000,
            reward_gold=900,
            reward_xp=700,
            reward_fame=40,
        ),
        BuyerQuestStep(
            step=3,
            title="Десять чемпионов",
            desc="Победи 10 элитных монстров.",
            quest_type="kills_elite",
            target=10,
            reward_gold=1100,
            reward_xp=850,
            reward_fame=50,
        ),
    ),
    final_gold=800,
    final_xp=650,
    final_fame=45,
    final_item={
        "name": "Печать Орина",
        "kind": "ring",
        "rarity": "epic",
        "luck": 15,
        "dex": 8,
        "int": 5,
        "image_url": "",
        "desc": "Личная печать великого скупщика Орина. Удача сопровождает носителя в любой схватке.",
    },
    final_text=(
        "— Это всё, что я могу дать тебе, герой.\n"
        "Печать Орина — мой последний подарок. Используй её с умом.\n"
        "Иди к вершине. Я буду ждать новостей."
    ),
)

# ── Словарь ────────────────────────────────────────────────────────────────────
_CHAINS: dict[int, BuyerQuestChain] = {
    3: _CHAIN_3,
    31: _CHAIN_31,
    61: _CHAIN_61,
    91: _CHAIN_91,
}


def chain_for_hub(hub_floor: int) -> BuyerQuestChain | None:
    return _CHAINS.get(hub_floor)
