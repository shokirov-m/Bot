"""
Цепочки заданий от кузнеца в городских хабах.

Каждый хаб (этажи 3, 31, 61, 91) даёт свою цепочку из 3 шагов.
В конце — редкий/эпический предмет.

Шаги:
  1) Заработай N золота в боях       (earn_gold)
  2) Убей N элитных монстров         (kills_elite)
  3) Победи N боссов (мини/мажор)    (kills_boss)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ForgeQuestStep:
    step: int          # 1, 2, 3
    title: str
    desc: str
    quest_type: str    # earn_gold | kills_elite | kills_boss
    target: int
    reward_gold: int   # промежуточная награда за шаг
    reward_xp: int
    reward_fame: int


@dataclass(frozen=True, slots=True)
class ForgeQuestChain:
    hub_floor: int          # 3 | 31 | 61 | 91
    npc_name: str
    npc_emoji: str
    chain_title: str
    intro: str
    steps: tuple[ForgeQuestStep, ...]
    # Финальная награда
    final_gold: int
    final_xp: int
    final_fame: int
    final_item: dict        # item_data payload
    final_text: str         # диалог кузнеца при выдаче


# ── Хаб 3: Тихий Ручей — Кузнец Боран ────────────────────────────────────────
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
            reward_gold=50,
            reward_xp=30,
            reward_fame=5,
        ),
        ForgeQuestStep(
            step=2,
            title="Испытание стали",
            desc="Победи 3 элитных монстра.",
            quest_type="kills_elite",
            target=3,
            reward_gold=80,
            reward_xp=50,
            reward_fame=8,
        ),
        ForgeQuestStep(
            step=3,
            title="Падение стража",
            desc="Победи 1 мини-босса или сильного босса.",
            quest_type="kills_boss",
            target=1,
            reward_gold=120,
            reward_xp=80,
            reward_fame=12,
        ),
    ),
    final_gold=200,
    final_xp=150,
    final_fame=15,
    final_item={
        "name": "Кузнечный меч Борана",
        "kind": "weapon",
        "hand": "main",
        "weapon_type": "blade",
        "rarity": "uncommon",
        "attack": 18,
        "str": 3,
        "luck": 1,
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
            reward_gold=150,
            reward_xp=100,
            reward_fame=10,
        ),
        ForgeQuestStep(
            step=2,
            title="Охота на чемпионов",
            desc="Победи 6 элитных монстров.",
            quest_type="kills_elite",
            target=6,
            reward_gold=220,
            reward_xp=150,
            reward_fame=15,
        ),
        ForgeQuestStep(
            step=3,
            title="Голова стража",
            desc="Победи 2 мини-боссов или сильных боссов.",
            quest_type="kills_boss",
            target=2,
            reward_gold=300,
            reward_xp=200,
            reward_fame=20,
        ),
    ),
    final_gold=400,
    final_xp=300,
    final_fame=25,
    final_item={
        "name": "Боевой топор Гарта",
        "kind": "weapon",
        "hand": "main",
        "weapon_type": "axe",
        "rarity": "rare",
        "attack": 35,
        "str": 5,
        "vit": 2,
        "image_url": "",
        "desc": "Тяжёлый топор из айронфоллской стали. Рубит броню как масло.",
    },
    final_text=(
        "— Ты прошёл испытание Айронфолла. Немногие доходят до конца.\n"
        "Этот топор — моя лучшая работа. Он прослужит тебе до самой вершины."
    ),
)

# ── Хаб 61: Эмберхолл — Кузнец Вара ──────────────────────────────────────────
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
            reward_gold=300,
            reward_xp=220,
            reward_fame=18,
        ),
        ForgeQuestStep(
            step=2,
            title="Чемпионская охота",
            desc="Победи 10 элитных монстров.",
            quest_type="kills_elite",
            target=10,
            reward_gold=420,
            reward_xp=320,
            reward_fame=25,
        ),
        ForgeQuestStep(
            step=3,
            title="Трое стражей",
            desc="Победи 3 мини-боссов или сильных боссов.",
            quest_type="kills_boss",
            target=3,
            reward_gold=560,
            reward_xp=420,
            reward_fame=32,
        ),
    ),
    final_gold=700,
    final_xp=500,
    final_fame=35,
    final_item={
        "name": "Латы чемпиона Эмберхолла",
        "kind": "armor",
        "rarity": "rare",
        "defense": 22,
        "vit": 5,
        "hp_bonus": 40,
        "image_url": "",
        "desc": "Броня, закалённая в вулканическом огне. Не горит, не ржавеет.",
    },
    final_text=(
        "— Ты — один из немногих, кто прошёл испытание Эмберхолла.\n"
        "Эти латы я делала три дня без сна. Носи достойно."
    ),
)

# ── Хаб 91: Этернис — Архикузнец Соль ────────────────────────────────────────
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
            reward_gold=600,
            reward_xp=450,
            reward_fame=25,
        ),
        ForgeQuestStep(
            step=2,
            title="Пятнадцать чемпионов",
            desc="Победи 15 элитных монстров.",
            quest_type="kills_elite",
            target=15,
            reward_gold=850,
            reward_xp=640,
            reward_fame=35,
        ),
        ForgeQuestStep(
            step=3,
            title="Пять стражей вечности",
            desc="Победи 5 мини-боссов или сильных боссов.",
            quest_type="kills_boss",
            target=5,
            reward_gold=1100,
            reward_xp=850,
            reward_fame=45,
        ),
    ),
    final_gold=1000,
    final_xp=800,
    final_fame=50,
    final_item={
        "name": "Молот Вечности",
        "kind": "weapon",
        "hand": "main",
        "weapon_type": "hammer",
        "rarity": "epic",
        "attack": 70,
        "str": 10,
        "vit": 5,
        "luck": 3,
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
    """Возвращает этаж хаба, на котором находится персонаж (или None)."""
    if floor in HUB_FLOORS:
        return floor
    return None
