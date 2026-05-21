"""
Библиотека гримуаров между 18-м и 19-м ярусами (якорь after_floor=18).
Книги навыков: 10 000–100 000 💰, один раз на героя, без передачи и продажи.
"""

from __future__ import annotations

from dataclasses import dataclass

from db.models.character import Character
from game.archetypes.data import ARCHETYPES
from game.archetypes.grimoires import (
    SKILL_GRIMOIRES,
    SkillGrimoireDef,
    grimoire_usable_by_character,
    inventory_keys,
    learned_keys,
)
from game.archetypes.trees import TREES

LIBRARY_ANCHOR_FLOOR = 18
LIBRARY_COMBAT_FLOORS: tuple[int, ...] = (18, 19)

META_LIBRARY_PURCHASES = "library_grimoire_purchases_v1"

# cost_sp из древа → цена в библиотеке
_SP_GOLD: dict[int, int] = {
    2: 10_000,
    3: 35_000,
    4: 60_000,
    5: 100_000,
}

LIBRARY_ARCHETYPES: tuple[str, ...] = ("warrior", "mage", "scout", "acolyte")


@dataclass(frozen=True, slots=True)
class LibraryOffer:
    grimoire_key: str
    archetype_key: str
    gold_price: int
    sort_index: int


def library_unlocked(character: Character) -> bool:
    """Доступ после прохождения 18-го яруса (как город-хаб: highest > anchor)."""
    return int(character.highest_floor_reached) > LIBRARY_ANCHOR_FLOOR


def library_visible_on_floor(floor_number: int) -> bool:
    return int(floor_number) in LIBRARY_COMBAT_FLOORS


def library_floor_ok(character: Character, floor_number: int) -> bool:
    return (
        library_unlocked(character)
        and library_visible_on_floor(int(floor_number))
        and int(character.floor_number) == int(floor_number)
    )


def _purchased_keys(character: Character) -> set[str]:
    raw = (character.meta_progress or {}).get(META_LIBRARY_PURCHASES)
    if not isinstance(raw, list):
        return set()
    return {str(x) for x in raw if x}


def _gold_for_grimoire(g: SkillGrimoireDef) -> int:
    tree = TREES.get(g.archetype_key) or {}
    node = tree.get(g.source_node_key)
    sp = int(getattr(node, "cost_sp", 2) or 2)
    return _SP_GOLD.get(sp, 10_000)


def _node_sort_index(archetype_key: str, node_key: str) -> int:
    tree = TREES.get(archetype_key) or {}
    keys = list(tree.keys())
    if node_key in keys:
        return keys.index(node_key)
    return 999


def offers_for_archetype(archetype_key: str) -> list[LibraryOffer]:
    arch = str(archetype_key).lower().strip()
    out: list[LibraryOffer] = []
    for gkey, g in SKILL_GRIMOIRES.items():
        if g.archetype_key != arch:
            continue
        out.append(
            LibraryOffer(
                grimoire_key=gkey,
                archetype_key=arch,
                gold_price=_gold_for_grimoire(g),
                sort_index=_node_sort_index(arch, g.source_node_key),
            ),
        )
    out.sort(key=lambda o: (o.sort_index, o.grimoire_key))
    return out


def archetype_label_ru(archetype_key: str) -> str:
    arch = ARCHETYPES.get(str(archetype_key).lower())
    if arch:
        return f"{arch.emoji} {arch.name_ru}"
    return archetype_key


def offer_status(character: Character, grimoire_key: str) -> str:
    """Короткий статус для списка: owned / learned / price."""
    if grimoire_key in learned_keys(character):
        return "изучен"
    if grimoire_key in _purchased_keys(character):
        return "куплен"
    if grimoire_key in inventory_keys(character):
        return "в сумке"
    return ""


def can_purchase(
    character: Character,
    grimoire_key: str,
) -> tuple[bool, str]:
    g = SKILL_GRIMOIRES.get(grimoire_key)
    if not g:
        return False, "Такой книги нет в каталоге."
    if not library_unlocked(character):
        return False, "Библиотека откроется после 18-го яруса."
    if grimoire_key in learned_keys(character):
        return False, "Гримуар уже изучен — повторно не продаётся."
    if grimoire_key in _purchased_keys(character):
        return False, "Вы уже покупали эту книгу здесь."
    if grimoire_key in inventory_keys(character):
        return False, "Книга уже у вас — прочитайте в «Гримуарах»."
    if not grimoire_usable_by_character(character, grimoire_key):
        return (
            False,
            "Книга другого пути. Сначала выберите базовый класс в «Специализация» "
            f"({archetype_label_ru(g.archetype_key)}).",
        )
    price = _gold_for_grimoire(g)
    if int(character.gold) < price:
        return False, f"Недостаточно золота. Нужно {price:,} 💰."
    return True, ""


def mark_purchased(character: Character, grimoire_key: str) -> None:
    mp = dict(character.meta_progress or {})
    bought = sorted(_purchased_keys(character) | {str(grimoire_key)})
    mp[META_LIBRARY_PURCHASES] = bought
    character.meta_progress = mp
