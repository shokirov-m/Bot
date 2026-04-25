"""
Цепочки заданий от кузнеца в городских хабах.

Каждый хаб (этажи 3, 31, 61, 91) даёт свою цепочку из 3 шагов.
В конце — редкий/эпический предмет (редкость повышена на 1 ранг).
Награды за шаги увеличены в 3 раза.

Шаги:
  1) Заработай N золота в боях       (earn_gold)
  2) Убей N элитных монстров         (kills_elite)
  3) Победи N боссов (мини/мажор)    (kills_boss)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ForgeQuestStep:
    step: int
    title: str
    desc: str
    quest_type: str
    target: int
    reward_gold: int
    reward_xp: int
    reward_fame: int


@dataclass(frozen=True, slots=True)
class ForgeQuestChain:
    hub_floor: int
    npc_name: str
    npc_emoji: str
    chain_title: str
    intro: str
    steps: tuple[ForgeQuestStep, ...]
    final_gold: int
    final_xp: int
    final_fame: int
    final_item: dict
    final_text: str


# ── Хаб 3: Тихий Ручей — Кузнец Боран ────────────────────────────────────────
# Награды ×3, редкость: uncommon → rare
_CHAIN_3 = ForgeQuestChain(
    hub_floor=3,
    npc_name="Кузнец Боран",
    npc_emoji="⚒️",
    chain_title="Испытание стали",
    intro=(
        "— А, новый герой. Видал я таких — приходят, уходят...\n"
        "Хочешь, чтоб я сделал тебе хорошее оружие? Сначала докажи, что достоин.\n"
        "Выполни три задания — и я скую тебе клинок, что не подведёт."
    ),
    steps=(
        ForgeQuestStep(
            step=1,
            title="Монеты на материалы",
            desc="Заработай 300 золота в боях.",
            quest_type="earn_gold",
            target=300,
            reward_gold=150,
            reward_xp=90,
            reward_fame=5,
        ),
        ForgeQuestStep(
            step=2,
            title="Испытание стали",
            desc="Победи 3 элитных монстра.",
            quest_type="kills_elite",
            target=3,
            reward_gold=240,
            reward_xp=150,
            reward_fame=8,
        ),
        ForgeQuestStep(
            step=3,
            title="Падение стража",
            desc="Победи 1 мини-босса или сильного босса.",
            quest_type="kills_boss",
            target=1,
            reward_gold=360,
            reward_xp=240,
            reward_fame=12,
        ),
    ),
    final_gold=600,
    final_xp=450,
    final_fame=15,
    final_item={
        "name": "Кузнечный меч Борана",
        "kind": "weapon",
        "hand": "main",
        "weapon_type": "blade",
        "rarity": "rare",           # повышено: uncommon → rare
        "attack": 26,
        "str": 5,
        "luck": 2,
        "image_url": "",
        "desc": "Выкован опытным кузнецом Бораном в Тихом Ручье.",
    },
    final_text=(
        "— Хм. Ты прошёл все испытания. Даже я удивлён.\n"
        "Держи — это лучший клинок, что я сковал за последний год.\n"
        "Не потеряй его в какой-нибудь яме."
    ),
)

# ── Хаб 31: Айронфолл — Кузнец Гарт ──────────────────────────────────────────
# Награды ×3, редкость: rare → epic
_CHAIN_31 = ForgeQuestChain(
    hub_floor=31,
    npc_name="Кузнец Гарт",
    npc_emoji="🔨",
    chain_title="Кровь и железо",
    intro=(
        "— В Айронфолле кузнецы куют оружие для настоящих воинов.\n"
        "Ты хочешь мой лучший топор? Тогда заслужи его.\n"
        "Три задания. Без скидок."
    ),
    steps=(
        ForgeQuestStep(
            step=1,
            title="Руда и монеты",
            desc="Заработай 800 золота в боях.",
            quest_type="earn_gold",
            target=800,
            reward_gold=450,
            reward_xp=300,
            reward_fame=10,
        ),
        ForgeQuestStep(
            step=2,
            title="Охота на чемпионов",
            desc="Победи 6 элитных монстров.",
            quest_type="kills_elite",
            target=6,
            reward_gold=660,
            reward_xp=450,
            reward_fame=15,
        ),
        ForgeQuestStep(
            step=3,
            title="Голова стража",
            desc="Победи 2 мини-боссов или сильных боссов.",
            quest_type="kills_boss",
            target=2,
            reward_gold=900,
            reward_xp=600,
            reward_fame=20,
        ),
    ),
    final_gold=1200,
    final_xp=900,
    final_fame=25,
    final_item={
        "name": "Боевой топор Гарта",
        "kind": "weapon",
        "hand": "main",
        "weapon_type": "axe",
        "rarity": "epic",           # повышено: rare → epic
        "attack": 50,
        "str": 8,
        "vit": 4,
        "image_url": "",
        "desc": "Тяжёлый топор из айронфоллской стали. Рубит броню как масло.",
    },
    final_text=(
        "— Ты прошёл испытание Айронфолла. Немногие доходят до конца.\n"
        "Этот топор — моя лучшая работа. Он прослужит тебе до самой вершины."
    ),
)

# ── Хаб 61: Эмберхолл — Кузнец Вара ──────────────────────────────────────────
# Награды ×3, редкость: rare → epic
_CHAIN_61 = ForgeQuestChain(
    hub_floor=61,
    npc_name="Мастер Вара",
    npc_emoji="🌋",
    chain_title="Латы чемпиона",
    intro=(
        "— Эмберхолл — город огня и пепла. Здесь только лучшие.\n"
        "Я слышала о тебе. Но имя — это ничто.\n"
        "Докажи делами — и я скую тебе броню, что остановит саму смерть."
    ),
    steps=(
        ForgeQuestStep(
            step=1,
            title="Огненное золото",
            desc="Заработай 1500 золота в боях.",
            quest_type="earn_gold",
            target=1500,
            reward_gold=900,
            reward_xp=660,
            reward_fame=18,
        ),
        ForgeQuestStep(
            step=2,
            title="Чемпионская охота",
            desc="Победи 10 элитных монстров.",
            quest_type="kills_elite",
            target=10,
            reward_gold=1260,
            reward_xp=960,
            reward_fame=25,
        ),
        ForgeQuestStep(
            step=3,
            title="Трое стражей",
            desc="Победи 3 мини-боссов или сильных боссов.",
            quest_type="kills_boss",
            target=3,
            reward_gold=1680,
            reward_xp=1260,
            reward_fame=32,
        ),
    ),
    final_gold=2100,
    final_xp=1500,
    final_fame=35,
    final_item={
        "name": "Латы чемпиона Эмберхолла",
        "kind": "armor",
        "rarity": "epic",           # повышено: rare → epic
        "defense": 32,
        "vit": 8,
        "hp_bonus": 60,
        "image_url": "",
        "desc": "Броня, закалённая в вулканическом огне. Не горит, не ржавеет.",
    },
    final_text=(
        "— Ты — один из немногих, кто прошёл испытание Эмберхолла.\n"
        "Эти латы я делала три дня без сна. Носи достойно."
    ),
)

# ── Хаб 91: Этернис — Архикузнец Соль ────────────────────────────────────────
# Награды ×3, редкость: epic → legendary
_CHAIN_91 = ForgeQuestChain(
    hub_floor=91,
    npc_name="Архикузнец Соль",
    npc_emoji="⚡",
    chain_title="Молот Вечности",
    intro=(
        "— Ты дошёл до Этерниса. Значит, ты — нечто большее, чем просто герой.\n"
        "У меня есть для тебя работа. Три задания — каждое сложнее предыдущего.\n"
        "Завершишь — получишь оружие, которое не знает себе равных."
    ),
    steps=(
        ForgeQuestStep(
            step=1,
            title="Золото вечности",
            desc="Заработай 2500 золота в боях.",
            quest_type="earn_gold",
            target=2500,
            reward_gold=1800,
            reward_xp=1350,
            reward_fame=25,
        ),
        ForgeQuestStep(
            step=2,
            title="Пятнадцать чемпионов",
            desc="Победи 15 элитных монстров.",
            quest_type="kills_elite",
            target=15,
            reward_gold=2550,
            reward_xp=1920,
            reward_fame=35,
        ),
        ForgeQuestStep(
            step=3,
            title="Пять стражей вечности",
            desc="Победи 5 мини-боссов или сильных боссов.",
            quest_type="kills_boss",
            target=5,
            reward_gold=3300,
            reward_xp=2550,
            reward_fame=45,
        ),
    ),
    final_gold=3000,
    final_xp=2400,
    final_fame=50,
    final_item={
        "name": "Молот Вечности",
        "kind": "weapon",
        "hand": "main",
        "weapon_type": "hammer",
        "rarity": "legendary",      # повышено: epic → legendary
        "attack": 95,
        "str": 15,
        "vit": 8,
        "luck": 5,
        "image_url": "",
        "desc": "Легендарное оружие архикузнеца Соля. Каждый удар звучит как гром.",
    },
    final_text=(
        "— Это... впечатляет. Я не думал, что кто-то пройдёт все испытания Этерниса.\n"
        "Молот Вечности — твой. Он будет служить тебе до конца башни и дальше."
    ),
)

# ── Словарь цепочек по этажу хаба ─────────────────────────────────────────────
_CHAINS: dict[int, ForgeQuestChain] = {
    3: _CHAIN_3,
    31: _CHAIN_31,
    61: _CHAIN_61,
    91: _CHAIN_91,
}

HUB_FLOORS: tuple[int, ...] = (3, 31, 61, 91)


def chain_for_hub(hub_floor: int) -> ForgeQuestChain | None:
    return _CHAINS.get(hub_floor)


def hub_floor_for_character_floor(floor: int) -> int | None:
    if floor in HUB_FLOORS:
        return floor
    return None
