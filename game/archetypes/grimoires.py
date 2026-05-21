"""
Гримуары навыков и высшие гримуары (смена специализации tier‑2).
Древо SP снято — прогресс из узлов мигрирует в изученные гримуары.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.archetypes.data import ARCHETYPES, SKILLS
from game.archetypes.models import PassiveV2, SkillTreeNode
from game.archetypes.trees import TREES

META_INVENTORY = "grimoire_inventory_v1"
META_LEARNED = "learned_grimoires_v1"
META_MIGRATED = "grimoire_tree_migrated_v1"

_TIER2_PARENT: dict[str, str] = {
    "guardian": "warrior",
    "berserker": "warrior",
    "pyromancer": "mage",
    "cryomancer": "mage",
    "assassin": "scout",
    "ranger": "scout",
    "paladin": "acolyte",
    "prophet": "acolyte",
}


@dataclass(frozen=True, slots=True)
class SkillGrimoireDef:
    key: str
    name_ru: str
    description_ru: str
    archetype_key: str
    node_type: str
    value: Any
    source_node_key: str = ""


@dataclass(frozen=True, slots=True)
class SupremeGrimoireDef:
    key: str
    name_ru: str
    description_ru: str
    tier2_class_key: str
    parent_class_key: str
    emoji: str = "📜"


def _build_skill_grimoires() -> dict[str, SkillGrimoireDef]:
    out: dict[str, SkillGrimoireDef] = {}
    for arch_key, tree in TREES.items():
        for node_key, node in tree.items():
            gkey = f"grim_{arch_key}_{node_key}"
            out[gkey] = SkillGrimoireDef(
                key=gkey,
                name_ru=f"📖 {node.name_ru}",
                description_ru=node.description_ru,
                archetype_key=arch_key,
                node_type=node.node_type,
                value=node.value,
                source_node_key=node_key,
            )
    return out


SKILL_GRIMOIRES: dict[str, SkillGrimoireDef] = _build_skill_grimoires()

SUPREME_GRIMOIRES: dict[str, SupremeGrimoireDef] = {
    "supreme_guardian": SupremeGrimoireDef(
        "supreme_guardian",
        "Высший гримуар: Страж",
        "Ритуал стража. Открывает путь Guardian и все его силы.",
        "guardian",
        "warrior",
        "🛡️",
    ),
    "supreme_berserker": SupremeGrimoireDef(
        "supreme_berserker",
        "Высший гримуар: Берсерк",
        "Клятва ярости. Открывает путь Berserker.",
        "berserker",
        "warrior",
        "🪓",
    ),
    "supreme_pyromancer": SupremeGrimoireDef(
        "supreme_pyromancer",
        "Высший гримуар: Пиромант",
        "Пламя без границ. Открывает путь Pyromancer.",
        "pyromancer",
        "mage",
        "🔥",
    ),
    "supreme_cryomancer": SupremeGrimoireDef(
        "supreme_cryomancer",
        "Высший гримуар: Криомант",
        "Лёд вечной ночи. Открывает путь Cryomancer.",
        "cryomancer",
        "mage",
        "❄️",
    ),
    "supreme_assassin": SupremeGrimoireDef(
        "supreme_assassin",
        "Высший гримуар: Убийца",
        "Клинок из тени. Открывает путь Assassin.",
        "assassin",
        "scout",
        "🗡️",
    ),
    "supreme_ranger": SupremeGrimoireDef(
        "supreme_ranger",
        "Высший гримуар: Рейнджер",
        "Зов диких земель. Открывает путь Ranger.",
        "ranger",
        "scout",
        "🏹",
    ),
    "supreme_paladin": SupremeGrimoireDef(
        "supreme_paladin",
        "Высший гримуар: Паладин",
        "Свет клятвы. Открывает путь Paladin.",
        "paladin",
        "acolyte",
        "⚔️",
    ),
    "supreme_prophet": SupremeGrimoireDef(
        "supreme_prophet",
        "Высший гримуар: Пророк",
        "Голос вечности. Открывает путь Prophet.",
        "prophet",
        "acolyte",
        "✨",
    ),
}


def _meta(character: Character) -> dict[str, Any]:
    return dict(character.meta_progress or {})


def _save_meta(character: Character, mp: dict[str, Any]) -> None:
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass


def inventory_keys(character: Character) -> list[str]:
    raw = _meta(character).get(META_INVENTORY)
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if x]


def learned_keys(character: Character) -> set[str]:
    raw = _meta(character).get(META_LEARNED)
    if not isinstance(raw, list):
        return set()
    return {str(x) for x in raw if x}


def _archetype_for_grimoires(character: Character) -> str:
    ck = str(character.class_key or "wanderer").lower()
    if ck == "necromancer":
        return "necromancer"
    parent = _TIER2_PARENT.get(ck)
    if parent:
        return parent
    if ck in TREES:
        return ck
    if ck == "wanderer":
        return ""
    arch = ARCHETYPES.get(ck)
    if arch and arch.tier == 1:
        return ck
    return ck


def grimoire_usable_by_character(character: Character, grimoire_key: str) -> bool:
    g = SKILL_GRIMOIRES.get(grimoire_key)
    if not g:
        s = SUPREME_GRIMOIRES.get(grimoire_key)
        if not s:
            return False
        cur = str(character.class_key or "wanderer").lower()
        return cur == s.parent_class_key
    arch = _archetype_for_grimoires(character)
    if not arch:
        return False
    return g.archetype_key == arch


def migrate_tree_to_grimoires(character: Character) -> int:
    """Один раз: unlocked_nodes → изученные гримуары."""
    mp = _meta(character)
    if mp.get(META_MIGRATED):
        return 0
    arch = _archetype_for_grimoires(character)
    if not arch:
        mp[META_MIGRATED] = True
        _save_meta(character, mp)
        return 0
    tree = TREES.get(arch) or {}
    unlocked = set(mp.get("unlocked_nodes") or [])
    learned = set(learned_keys(character))
    added = 0
    for node_key in unlocked:
        gkey = f"grim_{arch}_{node_key}"
        if gkey in SKILL_GRIMOIRES and gkey not in learned:
            learned.add(gkey)
            added += 1
    mp[META_LEARNED] = sorted(learned)
    mp.pop("unlocked_nodes", None)
    mp.pop("unspent_sp", None)
    mp[META_MIGRATED] = True
    _save_meta(character, mp)
    return added


def grant_grimoire(character: Character, grimoire_key: str, *, to_inventory: bool = True) -> bool:
    if grimoire_key not in SKILL_GRIMOIRES and grimoire_key not in SUPREME_GRIMOIRES:
        return False
    mp = _meta(character)
    learned = learned_keys(character)
    if grimoire_key in learned:
        return True
    if to_inventory:
        inv = inventory_keys(character)
        if grimoire_key not in inv:
            inv.append(grimoire_key)
            mp[META_INVENTORY] = inv
            _save_meta(character, mp)
        return True
    return learn_grimoire(character, grimoire_key)[0]


def learn_grimoire(character: Character, grimoire_key: str) -> tuple[bool, str]:
    migrate_tree_to_grimoires(character)
    if grimoire_key in learned_keys(character):
        return False, "Гримуар уже изучен."
    inv = inventory_keys(character)
    if grimoire_key in SKILL_GRIMOIRES and grimoire_key not in inv:
        return False, "Сначала получите гримуар (он должен быть в сумке)."
    if grimoire_key in SKILL_GRIMOIRES and not grimoire_usable_by_character(character, grimoire_key):
        return False, "Этот гримуар не подходит вашему пути."
    if grimoire_key in SUPREME_GRIMOIRES:
        sg = SUPREME_GRIMOIRES[grimoire_key]
        cur = str(character.class_key or "wanderer").lower()
        if cur != sg.parent_class_key:
            return False, "Высший гримуар только для вашего базового пути."
        if ARCHETYPES.get(cur, ARCHETYPES["wanderer"]).tier >= 2:
            return False, "Специализация уже открыта."

    mp = _meta(character)
    learned = list(learned_keys(character))
    learned.append(grimoire_key)
    mp[META_LEARNED] = learned
    inv = [k for k in inventory_keys(character) if k != grimoire_key]
    mp[META_INVENTORY] = inv
    _save_meta(character, mp)
    g = SKILL_GRIMOIRES.get(grimoire_key)
    if g:
        return True, f"Изучен гримуар: {g.name_ru}"
    sg = SUPREME_GRIMOIRES[grimoire_key]
    return True, f"Получен {sg.name_ru}. Используйте его для смены класса."


def apply_supreme_grimoire_class_change(character: Character, grimoire_key: str) -> tuple[bool, str]:
    sg = SUPREME_GRIMOIRES.get(grimoire_key)
    if not sg:
        return False, "Неизвестный высший гримуар."
    if grimoire_key not in learned_keys(character):
        return False, "Сначала изучите гримуар (прочитайте в инвентаре)."
    cur = str(character.class_key or "wanderer").lower()
    if cur != sg.parent_class_key:
        return False, "Гримуар не для вашего пути."
    arch = ARCHETYPES.get(sg.tier2_class_key)
    if not arch:
        return False, "Ошибка данных класса."
    character.class_key = sg.tier2_class_key
    mp = _meta(character)
    mp["equipped_skill_keys"] = []
    mp.pop("unlocked_nodes", None)
    mp.pop("unspent_sp", None)
    _save_meta(character, mp)
    prune_incompatible_grimoires(character)
    return True, f"Вы стали {arch.name_ru}!"


def prune_incompatible_grimoires(character: Character) -> int:
    """Убрать из изученных/сумки гримуары другого пути (после смены класса)."""
    migrate_tree_to_grimoires(character)
    mp = _meta(character)
    before_l = set(learned_keys(character))
    before_i = set(inventory_keys(character))
    kept_l = [k for k in before_l if grimoire_usable_by_character(character, k)]
    kept_i = [k for k in before_i if grimoire_usable_by_character(character, k)]
    mp[META_LEARNED] = kept_l
    mp[META_INVENTORY] = kept_i
    _save_meta(character, mp)
    return (len(before_l) - len(kept_l)) + (len(before_i) - len(kept_i))


def get_unlocked_skill_keys_from_grimoires(character: Character) -> list[str]:
    migrate_tree_to_grimoires(character)
    keys: list[str] = []
    for gk in learned_keys(character):
        if not grimoire_usable_by_character(character, gk):
            continue
        g = SKILL_GRIMOIRES.get(gk)
        if g and g.node_type == "active_skill":
            sk = str(g.value)
            if sk and sk not in keys:
                keys.append(sk)
    return keys


def get_grimoire_combat_bonuses(character: Character) -> dict[str, float | int]:
    migrate_tree_to_grimoires(character)
    merged: dict[str, float | int] = {}
    for gk in learned_keys(character):
        if not grimoire_usable_by_character(character, gk):
            continue
        g = SKILL_GRIMOIRES.get(gk)
        if not g:
            continue
        if g.node_type in ("passive_bonus", "stat_boost") and isinstance(g.value, dict):
            for k, v in g.value.items():
                merged[k] = merged.get(k, 0) + v
    return merged


def passive_grimoires_as_passives(character: Character) -> list[PassiveV2]:
    out: list[PassiveV2] = []
    for gk in learned_keys(character):
        if not grimoire_usable_by_character(character, gk):
            continue
        g = SKILL_GRIMOIRES.get(gk)
        if g and g.node_type == "passive_bonus" and isinstance(g.value, dict):
            out.append(
                PassiveV2(
                    f"grim_passive_{gk}",
                    g.name_ru.replace("📖 ", ""),
                    "Бонус из гримуара.",
                    dict(g.value),
                ),
            )
    return out


def format_grimoires_profile_html_ru(character: Character) -> str:
    """Пассивные/стат бонусы из гримуаров для полного профиля."""
    from game.archetypes import manager as arch_manager

    chunks: list[str] = []
    for gk in sorted(learned_keys(character)):
        if not grimoire_usable_by_character(character, gk):
            continue
        g = SKILL_GRIMOIRES.get(gk)
        if not g or g.node_type not in ("passive_bonus", "stat_boost"):
            continue
        node = SkillTreeNode(
            g.source_node_key or gk,
            g.name_ru.replace("📖 ", ""),
            g.description_ru,
            g.node_type,
            g.value,
        )
        fx = arch_manager.format_skill_tree_node_effect_ru(node).strip()
        if fx:
            chunks.append(f"<b>{html.escape(g.name_ru)}</b>\n {html.escape(fx)}")
    return "\n\n".join(chunks)


def supreme_keys_for_parent(parent_key: str) -> list[str]:
    pk = str(parent_key).lower()
    return [sg.key for sg in SUPREME_GRIMOIRES.values() if sg.parent_class_key == pk]
