"""
Ветки класса: 4 базовых по доминанту на 11 этаже (с 10 ур.), подклассы на 57 (×2 к статам),
скрытые классы при особых условиях.
"""

from __future__ import annotations

from db.models.character import Character

# Доминирующий стат → базовый класс (несколько при равенстве максимумов).
DOMINANT_TO_BASE: tuple[tuple[str, str], ...] = (
    ("str", "warrior"),
    ("dex", "archer"),
    ("int", "mage"),
    ("vit", "warden"),
)

SUBCLASS_NAME_RU: dict[str, str] = {
    "juggernaut": "Исполин",
    "arcane_lord": "Повелитель стихий",
    "wind_stalker": "Небесный охотник",
    "living_fortress": "Живая крепость",
}

# Варианты подкласса по базовому (или уникальному) class_key после 57 этажа.
SUBCLASS_BY_CLASS: dict[str, tuple[str, ...]] = {
    "warrior": ("juggernaut",),
    "mage": ("arcane_lord",),
    "archer": ("wind_stalker",),
    "warden": ("living_fortress",),
    "star_touched": ("arcane_lord",),
    "tower_reaper": ("juggernaut",),
}


def dominant_base_class_keys(character: Character) -> list[str]:
    """Какие из 4 базовых доступны (равны максимуму среди СИЛ/ЛОВ/ИНТ/ВЫН)."""
    stats = {
        "str": int(character.stat_strength),
        "dex": int(character.stat_dexterity),
        "int": int(character.stat_intelligence),
        "vit": int(character.stat_vitality),
    }
    mx = max(stats.values())
    out: list[str] = []
    for key, cls_key in DOMINANT_TO_BASE:
        if stats[key] == mx:
            if cls_key not in out:
                out.append(cls_key)
    return out


def secret_base_class_keys(character: Character) -> list[str]:
    """Скрытые классы у наставника (достижимы без внешней прокачки статов)."""
    out: list[str] = []
    luck = int(character.stat_luck)
    kills = int(character.total_kills)
    str_s = int(character.stat_strength)
    # Звёздный избранник — удача в боях (долгий фарм до перекрёстка).
    if kills >= 45 and luck >= 8:
        out.append("star_touched")
    # Жнец башни — охота без жалости.
    if kills >= 75 and str_s >= 10:
        out.append("tower_reaper")
    return out


def offered_base_class_keys(character: Character) -> list[str]:
    """Порядок: 4 базовых по доминанту, затем открытые секреты (без дублей)."""
    if not needs_base_class_choice(character):
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for k in dominant_base_class_keys(character) + secret_base_class_keys(character):
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def subclass_keys_for_character(character: Character) -> list[str]:
    if not needs_subclass_choice(character):
        return []
    return list(SUBCLASS_BY_CLASS.get(character.class_key, ()))


def needs_base_class_choice(character: Character) -> bool:
    """Странник 10+ уровня ещё без базового класса (выбор у наставника на 11 этаже)."""
    return (
        character.class_key == "wanderer"
        and int(character.class_tier) == 0
        and int(character.level) >= 10
    )


def can_pick_base_class_on_current_floor(character: Character) -> bool:
    """Кнопки выбора класса и наставник — только на 11 ярусе."""
    return needs_base_class_choice(character) and int(character.floor_number) == 11


def combat_blocked_for_missing_base_class(character: Character) -> bool:
    """С 11 яруса без класса в бой нельзя (до выбора можно сражаться ниже 11)."""
    return needs_base_class_choice(character) and int(character.floor_number) >= 11


def needs_subclass_choice(character: Character) -> bool:
    return (
        int(character.class_tier) == 1
        and character.subclass_key is None
        and int(character.floor_number) >= 57
    )


def combat_skill_class_key(character: Character) -> str:
    """Ключ для skills_for_class и боевой клавиатуры."""
    return character.class_key
