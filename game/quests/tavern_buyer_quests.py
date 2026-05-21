"""
Цепочки заданий от Скупщика Орина в таверне.
Награды увеличены в 3 раза, редкость предметов повышена на 1 ранг.

uncommon → rare, rare → epic, epic → legendary
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuyerQuestStep:
    step: int
    title: str
    desc: str
    quest_type: str
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


# ── Хаб 3 — редкость: uncommon → rare ────────────────────────────────────────
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
            reward_gold=180,
            reward_xp=105,
            reward_fame=4,
        ),
        BuyerQuestStep(
            step=2,
            title="Наполни кошелёк",
            desc="Заработай 200 золота в боях.",
            quest_type="earn_gold",
            target=200,
            reward_gold=240,
            reward_xp=135,
            reward_fame=6,
        ),
        BuyerQuestStep(
            step=3,
            title="Редкий товар",
            desc="Победи 2 элитных монстра.",
            quest_type="kills_elite",
            target=2,
            reward_gold=300,
            reward_xp=180,
            reward_fame=8,
        ),
    ),
    final_gold=450,
    final_xp=300,
    final_fame=12,
    final_item={
        "name": "Кольцо удачи Орина",
        "kind": "ring",
        "rarity": "rare",           # повышено: uncommon → rare
        "luck": 8,
        "dex": 4,
        "image_url": "",
        "desc": "Особое кольцо от скупщика Орина. Удача любит таких, как ты.",
    },
    final_text=(
        "— Ха! Ты справился лучше, чем я ожидал.\n"
        "Это кольцо я берёг для особого клиента. Похоже, это ты.\n"
        "Заходи ещё — у Орина всегда найдётся работа."
    ),
)

# ── Хаб 31 — редкость: rare → epic ───────────────────────────────────────────
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
            reward_gold=480,
            reward_xp=330,
            reward_fame=10,
        ),
        BuyerQuestStep(
            step=2,
            title="Серьёзный капитал",
            desc="Заработай 600 золота в боях.",
            quest_type="earn_gold",
            target=600,
            reward_gold=600,
            reward_xp=420,
            reward_fame=14,
        ),
        BuyerQuestStep(
            step=3,
            title="Трофеи с чемпионов",
            desc="Победи 4 элитных монстра.",
            quest_type="kills_elite",
            target=4,
            reward_gold=780,
            reward_xp=540,
            reward_fame=18,
        ),
    ),
    final_gold=1050,
    final_xp=750,
    final_fame=22,
    final_item={
        "name": "Амулет скупщика",
        "kind": "amulet",
        "rarity": "epic",           # повышено: rare → epic
        "luck": 12,
        "dex": 5,
        "int": 4,
        "image_url": "",
        "desc": "Амулет с рынка Айронфолла. Торговцы чуют удачу за версту.",
    },
    final_text=(
        "— Отличная работа. Мои заказчики довольны.\n"
        "Этот амулет — из партии редких товаров с верхних ярусов.\n"
        "Носи с пользой."
    ),
)

# ── Хаб 61 — редкость: rare → epic ───────────────────────────────────────────
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
            reward_gold=1050,
            reward_xp=780,
            reward_fame=18,
        ),
        BuyerQuestStep(
            step=2,
            title="Огненное золото",
            desc="Заработай 1200 золота в боях.",
            quest_type="earn_gold",
            target=1200,
            reward_gold=1350,
            reward_xp=990,
            reward_fame=24,
        ),
        BuyerQuestStep(
            step=3,
            title="Чемпионы огня",
            desc="Победи 6 элитных монстров.",
            quest_type="kills_elite",
            target=6,
            reward_gold=1680,
            reward_xp=1260,
            reward_fame=30,
        ),
    ),
    final_gold=1800,
    final_xp=1350,
    final_fame=32,
    final_item={
        "name": "Шлем торговца",
        "kind": "helmet",
        "rarity": "epic",           # повышено: rare → epic
        "defense": 22,
        "dex": 7,
        "luck": 9,
        "image_url": "",
        "desc": "Шлем с огненными рунами. Торговцы Эмберхолла ценят острый ум.",
    },
    final_text=(
        "— Превосходно. Огненный рынок принял тебя.\n"
        "Этот шлем привезли с самого верхнего яруса — специально для тебя."
    ),
)

# ── Хаб 91 — редкость: epic → legendary ──────────────────────────────────────
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
            reward_gold=2100,
            reward_xp=1650,
            reward_fame=30,
        ),
        BuyerQuestStep(
            step=2,
            title="Золото вечности",
            desc="Заработай 2000 золота в боях.",
            quest_type="earn_gold",
            target=2000,
            reward_gold=2700,
            reward_xp=2100,
            reward_fame=40,
        ),
        BuyerQuestStep(
            step=3,
            title="Десять чемпионов",
            desc="Победи 10 элитных монстров.",
            quest_type="kills_elite",
            target=10,
            reward_gold=3300,
            reward_xp=2550,
            reward_fame=50,
        ),
    ),
    final_gold=2400,
    final_xp=1950,
    final_fame=45,
    final_item={
        "name": "Печать Орина",
        "kind": "ring",
        "rarity": "legendary",      # повышено: epic → legendary
        "luck": 22,
        "dex": 12,
        "int": 8,
        "image_url": "",
        "desc": "Личная печать великого скупщика Орина. Удача сопровождает носителя в любой схватке.",
    },
    final_text=(
        "— Это всё, что я могу дать тебе, герой.\n"
        "Печать Орина — мой последний подарок. Используй её с умом.\n"
        "Иди к вершине. Я буду ждать новостей."
    ),
)

_CHAINS: dict[int, BuyerQuestChain] = {
    0: _CHAIN_3,
    30: _CHAIN_31,
    60: _CHAIN_61,
    90: _CHAIN_91,
}

_LEGACY_HUB_ANCHOR: dict[int, int] = {3: 0, 31: 30, 61: 60, 91: 90}


def normalize_hub_anchor(hub_floor: int) -> int:
    k = int(hub_floor)
    return _LEGACY_HUB_ANCHOR.get(k, k)


def chain_for_hub(hub_floor: int) -> BuyerQuestChain | None:
    return _CHAINS.get(normalize_hub_anchor(hub_floor))
