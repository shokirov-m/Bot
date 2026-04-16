"""
Десять классов: базовые статы, пассив, три активных скилла (описания для UI).
Ключи классов — латиница для БД и callback.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    """Описание класса для создания персонажа и справки в боте."""

    key: str
    name_ru: str
    emoji: str
    strength: int
    dexterity: int
    intelligence: int
    vitality: int
    luck: int
    passive_ru: str
    skill_1: str
    skill_2: str
    skill_3: str
    default_element: str | None
    # Множитель к расчётному HP после базы (пассивы вроде +15% HP у воина)
    hp_multiplier: float = 1.0
    mp_multiplier: float = 1.0


# Базовые формулы HP/MP задаются в character_service; здесь только множители пассивов.
CLASSES: dict[str, ClassDefinition] = {
    "wanderer": ClassDefinition(
        key="wanderer",
        name_ru="Странник",
        emoji="🎒",
        strength=10,
        dexterity=10,
        intelligence=10,
        vitality=10,
        luck=8,
        passive_ru="Универсал до 17 этажа: на перекрёстке откроется истинный путь по твоим статам.",
        skill_1="⚔️ Простой удар",
        skill_2="🛡️ Отход в защиту",
        skill_3="💨 Рывок",
        default_element=None,
    ),
    "star_touched": ClassDefinition(
        key="star_touched",
        name_ru="Звёздный избранник",
        emoji="✨",
        strength=8,
        dexterity=10,
        intelligence=12,
        vitality=10,
        luck=16,
        passive_ru="Скрытый путь: удача выше остальных статов. Редкое откровение на 17 этаже.",
        skill_1="✨ Звёздный укол",
        skill_2="🌠 Уклонение судьбы",
        skill_3="💫 Пульс эфира",
        default_element="light",
    ),
    "tower_reaper": ClassDefinition(
        key="tower_reaper",
        name_ru="Жнец башни",
        emoji="☠️",
        strength=16,
        dexterity=11,
        intelligence=8,
        vitality=11,
        luck=9,
        passive_ru="Скрытый путь: сотня побед и железная воля. Удар, выносливость, охота.",
        skill_1="☠️ Режущий ветер",
        skill_2="🩸 Сбор долга",
        skill_3="💀 Круг усталости",
        default_element="dark",
    ),
    "warrior": ClassDefinition(
        key="warrior",
        name_ru="Воин",
        emoji="🗡️",
        strength=15,
        dexterity=10,
        intelligence=6,
        vitality=14,
        luck=8,
        passive_ru="+15% к макс. HP, +10 к базовой защите (в бою)",
        skill_1="🗡️ Мощный удар",
        skill_2="🛡️ Щитовой блок",
        skill_3="💢 Сокрушение",
        default_element=None,
        hp_multiplier=1.15,
    ),
    "mage": ClassDefinition(
        key="mage",
        name_ru="Маг",
        emoji="🔮",
        strength=5,
        dexterity=8,
        intelligence=18,
        vitality=8,
        luck=8,
        passive_ru="+20% маг. урон, +8 MP за ход (в бою)",
        skill_1="🔥 Огненный шар",
        skill_2="❄️ Ледяные оковы",
        skill_3="⚡ Цепная молния",
        default_element="fire",
        mp_multiplier=1.1,
    ),
    "archer": ClassDefinition(
        key="archer",
        name_ru="Лучник",
        emoji="🏹",
        strength=10,
        dexterity=16,
        intelligence=7,
        vitality=10,
        luck=10,
        passive_ru="+15% дальний урон, +10% шанс второй выстрел (в бою)",
        skill_1="🎯 Прицельный выстрел",
        skill_2="💨 Отступление",
        skill_3="🌧️ Залп стрел",
        default_element=None,
    ),
    "priest": ClassDefinition(
        key="priest",
        name_ru="Жрец",
        emoji="✝️",
        strength=6,
        dexterity=8,
        intelligence=16,
        vitality=12,
        luck=9,
        passive_ru="+25% исцеление, +5% сопротивление дебаффам",
        skill_1="💚 Исцеление",
        skill_2="🛡️ Святой щит",
        skill_3="☀️ Кара нечисти",
        default_element="light",
    ),
    "assassin": ClassDefinition(
        key="assassin",
        name_ru="Убийца",
        emoji="🗡️",
        strength=11,
        dexterity=17,
        intelligence=7,
        vitality=9,
        luck=12,
        passive_ru="+20% крит, +15% уклонение",
        skill_1="🗡️ Удар в спину",
        skill_2="💨 Дымовая завеса",
        skill_3="☠️ Отравленный клинок",
        default_element=None,
    ),
    "berserker": ClassDefinition(
        key="berserker",
        name_ru="Берсерк",
        emoji="🪓",
        strength=18,
        dexterity=9,
        intelligence=5,
        vitality=12,
        luck=8,
        passive_ru="Чем ниже HP — тем выше урон (до +30%)",
        skill_1="🩸 Кровожадность",
        skill_2="💥 Яростный вихрь",
        skill_3="🔥 Жертва крови",
        default_element=None,
        hp_multiplier=1.05,
    ),
    "necromancer": ClassDefinition(
        key="necromancer",
        name_ru="Некромант",
        emoji="💀",
        strength=6,
        dexterity=9,
        intelligence=17,
        vitality=10,
        luck=11,
        passive_ru="+15% урон тьмой, дроп душ с врагов",
        skill_1="☠️ Касание смерти",
        skill_2="🦴 Призыв скелета",
        skill_3="🌑 Пожирание жизни",
        default_element="dark",
    ),
    "warden": ClassDefinition(
        key="warden",
        name_ru="Страж",
        emoji="🛡️",
        strength=12,
        dexterity=8,
        intelligence=8,
        vitality=18,
        luck=7,
        passive_ru="+20% броня, +10% HP союзникам (партийный контент)",
        skill_1="🛡️ Удар щитом",
        skill_2="⛓️ Оковы",
        skill_3="🏔️ Несокрушимый",
        default_element="earth",
    ),
    "shaman": ClassDefinition(
        key="shaman",
        name_ru="Шаман",
        emoji="🔔",
        strength=9,
        dexterity=10,
        intelligence=14,
        vitality=11,
        luck=11,
        passive_ru="+10% к стихийным эффектам, двойной шанс тотема",
        skill_1="⚡ Удар духов",
        skill_2="🌿 Тотем исцеления",
        skill_3="🌩️ Шторм предков",
        default_element="lightning",
    ),
    "hunter": ClassDefinition(
        key="hunter",
        name_ru="Охотник",
        emoji="🐺",
        strength=11,
        dexterity=14,
        intelligence=8,
        vitality=11,
        luck=11,
        passive_ru="+15% урон по зверям, следы на карте башни",
        skill_1="🏹 Укус волка",
        skill_2="🪤 Капкан",
        skill_3="🌲 Звериный натиск",
        default_element=None,
    ),
}


def get_class_or_none(key: str) -> ClassDefinition | None:
    """Возвращает описание класса по ключу или None."""
    return CLASSES.get(key)


def all_classes_ordered() -> list[ClassDefinition]:
    """Порядок отображения в меню регистрации."""
    order = [
        "warrior",
        "mage",
        "archer",
        "priest",
        "assassin",
        "berserker",
        "necromancer",
        "warden",
        "shaman",
        "hunter",
    ]
    return [CLASSES[k] for k in order if k in CLASSES]
