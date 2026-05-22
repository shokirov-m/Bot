"""
Некромант: престиж-класс (tier 3), скелеты в бою вместо наёмников.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.archetypes import manager as arch_manager
from game.mercenaries.shadow_market_meta import set_party_merc_ids

NECROMANCER_CLASS_KEY = "necromancer"
NECROMANCER_COST_GOLD = 800_000
NECROMANCER_MIN_LEVEL = 60
MAX_SKELETONS_IN_BATTLE = 3
NEC_BARRIER_MP_COST = 800
# Множитель поглощения к базовой формуле (ИНТ + уровень).
NEC_BARRIER_EFFECT_MULT = 2.5

META_NECRO = "necromancer_v1"
META_UNLOCKS = "skeleton_unlocks"
META_PARTY = "skeleton_party"
META_CLASS_SWAP_USED = "class_swap_used"

_DEFAULT_UNLOCKS = ("skel_tank", "skel_blade", "skel_mage")
_DEFAULT_PARTY = ("skel_tank", "skel_blade", "skel_mage")


@dataclass(frozen=True, slots=True)
class SkeletonRoleDef:
    key: str
    name_ru: str
    emoji: str
    base_hp: int
    base_atk: int
    is_tank: bool = False
    slots_cost: int = 1


SKELETON_ROLES: dict[str, SkeletonRoleDef] = {
    "skel_tank": SkeletonRoleDef("skel_tank", "Костяной страж", "🛡️", 420, 28, is_tank=True),
    "skel_blade": SkeletonRoleDef("skel_blade", "Костяной клинок", "⚔️", 260, 44),
    "skel_mage": SkeletonRoleDef("skel_mage", "Пепельный культист", "💀", 180, 52),
    "skel_colossus": SkeletonRoleDef(
        "skel_colossus",
        "Склепный колосс",
        "☠️",
        900,
        38,
        slots_cost=2,
    ),
}


def is_necromancer(character: Character) -> bool:
    return str(character.class_key or "").lower() == NECROMANCER_CLASS_KEY


def _meta(character: Character) -> dict[str, Any]:
    return dict(character.meta_progress or {})


def _necro_block(character: Character) -> dict[str, Any]:
    mp = _meta(character)
    block = dict(mp.get(META_NECRO) or {})
    if META_UNLOCKS not in block:
        block[META_UNLOCKS] = list(_DEFAULT_UNLOCKS)
    if META_PARTY not in block:
        block[META_PARTY] = list(_DEFAULT_PARTY)
    return block


def _save_necro(character: Character, block: dict[str, Any]) -> None:
    mp = _meta(character)
    mp[META_NECRO] = block
    character.meta_progress = mp
    flag_modified(character, "meta_progress")


def ensure_necro_meta(character: Character) -> dict[str, Any]:
    block = _necro_block(character)
    _save_necro(character, block)
    return block


def unlocked_skeleton_keys(character: Character) -> set[str]:
    if not is_necromancer(character):
        return set()
    block = _necro_block(character)
    raw = block.get(META_UNLOCKS) or list(_DEFAULT_UNLOCKS)
    return {str(x) for x in raw if str(x) in SKELETON_ROLES}


def get_party_skeleton_keys(character: Character) -> list[str]:
    if not is_necromancer(character):
        return []
    block = _necro_block(character)
    raw = list(block.get(META_PARTY) or _DEFAULT_PARTY)
    unlocked = unlocked_skeleton_keys(character)
    out: list[str] = []
    slots_used = 0
    for key in raw:
        k = str(key)
        if k not in unlocked or k not in SKELETON_ROLES:
            continue
        cost = int(SKELETON_ROLES[k].slots_cost)
        if slots_used + cost > MAX_SKELETONS_IN_BATTLE:
            continue
        out.append(k)
        slots_used += cost
    return out


def set_party_skeleton_keys(character: Character, keys: list[str]) -> None:
    block = ensure_necro_meta(character)
    unlocked = unlocked_skeleton_keys(character)
    clean: list[str] = []
    slots = 0
    for k in keys:
        sk = str(k)
        if sk not in unlocked or sk not in SKELETON_ROLES:
            continue
        cost = int(SKELETON_ROLES[sk].slots_cost)
        if slots + cost > MAX_SKELETONS_IN_BATTLE:
            continue
        if sk in clean:
            continue
        clean.append(sk)
        slots += cost
    block[META_PARTY] = clean
    _save_necro(character, block)


def skeleton_role_label(key: str) -> str:
    rd = SKELETON_ROLES.get(str(key))
    if rd is None:
        return key
    return f"{rd.emoji} {rd.name_ru}"


def _scale_stat(base: int, hero_level: int, per_level: float) -> int:
    lv = max(NECROMANCER_MIN_LEVEL, int(hero_level))
    delta = max(0, lv - NECROMANCER_MIN_LEVEL)
    return max(1, int(round(base + delta * per_level)))


def intelligence_stat(character: Character) -> int:
    return max(0, int(character.stat_intelligence or 0))


def skeleton_power_mult_from_intelligence(character: Character) -> float:
    """
    Сила скелетов от ИНТ некроманта: +0.75% HP и ATK за каждую единицу ИНТ.
    При 60 ИНТ ≈ ×1.45, при 100 ИНТ ≈ ×1.75.
    """
    intel = intelligence_stat(character)
    return 1.0 + intel * 0.0075


def defensive_barrier_hp(
    character: Character | None = None,
    *,
    hp_max: int | None = None,
    intelligence: int | None = None,
    level: int | None = None,
) -> int:
    """
    Ёмкость защитного барьера: база + ИНТ + уровень, с потолком от max HP героя.
    """
    if character is not None:
        intel = intelligence_stat(character)
        lv = max(NECROMANCER_MIN_LEVEL, int(character.level or NECROMANCER_MIN_LEVEL))
        hp_cap = int(hp_max if hp_max is not None else character.hp_max or 1)
    else:
        intel = max(0, int(intelligence or 0))
        lv = max(1, int(level or NECROMANCER_MIN_LEVEL))
        hp_cap = max(1, int(hp_max or 1))
    raw = int(30 + intel * 14 + max(0, lv - NECROMANCER_MIN_LEVEL) * 5)
    ceiling = max(80, int(hp_cap * 0.5))
    base = max(40, min(raw, ceiling))
    return max(72, int(round(base * NEC_BARRIER_EFFECT_MULT)))


def apply_necromancer_barrier_upkeep(state: dict[str, Any]) -> list[str]:
    """
    Поддержание барьера в конце раунда: −800 MP.
    Если маны нет — барьер рушится.
    """
    logs: list[str] = []
    if str(state.get("player_shield_kind") or "") != "barrier":
        return logs
    if int(state.get("player_shield_hp", 0) or 0) <= 0:
        return logs
    cost = NEC_BARRIER_MP_COST
    mp = int(state.get("player_mp", 0) or 0)
    if mp < cost:
        state["player_shield_hp"] = 0
        state["player_shield_hp_max"] = 0
        state["player_shield_kind"] = ""
        logs.append(
            f"💀 <b>Барьер рухнул</b> — нужно {cost:,} MP за ход (осталось {mp:,}).".replace(",", " "),
        )
        return logs
    state["player_mp"] = mp - cost
    logs.append(
        f"🔮 Барьер: −{cost:,} MP за ход поддержания (осталось {int(state['player_mp']):,}).".replace(",", " "),
    )
    return logs


def _skeleton_atk_bonus_mult(character: Character) -> float:
    from game.characters.skills import passive_combat_modifiers_merged

    mods = passive_combat_modifiers_merged(character)
    pct = float(mods.get("companion_atk_pct", 20) or 20)
    return 1.0 + max(0.0, pct) / 100.0


def build_skeleton_companions(character: Character) -> list[dict[str, Any]]:
    """Союзники для combat_state['companions'] (как наёмники, без id)."""
    if not is_necromancer(character):
        return []
    party = get_party_skeleton_keys(character)
    if not party:
        return []
    atk_mult = _skeleton_atk_bonus_mult(character)
    int_mult = skeleton_power_mult_from_intelligence(character)
    lv = int(character.level)
    out: list[dict[str, Any]] = []
    for key in party:
        rd = SKELETON_ROLES.get(key)
        if rd is None:
            continue
        hp = max(1, int(round(_scale_stat(rd.base_hp, lv, 10.0) * int_mult)))
        atk = max(1, int(round(_scale_stat(rd.base_atk, lv, 2.2) * atk_mult * int_mult)))
        out.append(
            {
                "id": f"skel:{key}",
                "name": rd.name_ru,
                "role": key,
                "is_tank": bool(rd.is_tank),
                "hp": hp,
                "hp_max": hp,
                "atk": atk,
                "loyalty": 80,
                "dead": False,
                "is_skeleton": True,
            },
        )
    return out


def clear_merc_party_for_necromancer(character: Character) -> None:
    set_party_merc_ids(character, [])


def class_swap_to_necromancer_used(character: Character) -> bool:
    return bool(_necro_block(character).get(META_CLASS_SWAP_USED))


def can_purchase_necromancer(character: Character) -> tuple[bool, str]:
    if is_necromancer(character):
        return False, "Вы уже некромант."
    if int(character.level) < NECROMANCER_MIN_LEVEL:
        return False, f"Нужен уровень {NECROMANCER_MIN_LEVEL}+."
    if int(character.gold) < NECROMANCER_COST_GOLD:
        return (
            False,
            f"Нужно {NECROMANCER_COST_GOLD:,} 💰 (у вас {int(character.gold):,}).".replace(",", " "),
        )
    cur = arch_manager.get_character_archetype(character)
    if cur.tier < 1:
        return False, "Сначала выберите базовый путь (с 10 уровня)."
    if cur.tier >= 1 and class_swap_to_necromancer_used(character):
        return False, "Смена класса на некроманта уже была использована (один раз)."
    return True, "Можно провести ритуал."


def purchase_necromancer(character: Character) -> tuple[bool, str]:
    ok, msg = can_purchase_necromancer(character)
    if not ok:
        return False, msg
    from services.progression import character_service

    if not character_service.try_spend_gold(
        character,
        NECROMANCER_COST_GOLD,
        note="ritual_necromancer",
        kind="class_unlock",
    ):
        return False, "Не хватает золота."
    arch = arch_manager.get_archetype(NECROMANCER_CLASS_KEY)
    if arch is None:
        return False, "Класс не найден в данных."
    character.class_key = arch.key
    mp = dict(character.meta_progress or {})
    mp.pop("unlocked_nodes", None)
    mp.pop("unspent_sp", None)
    mp["equipped_skill_keys"] = []
    character.meta_progress = mp
    flag_modified(character, "meta_progress")
    clear_merc_party_for_necromancer(character)
    from game.archetypes.grimoires import prune_incompatible_grimoires

    prune_incompatible_grimoires(character)
    block = ensure_necro_meta(character)
    block[META_CLASS_SWAP_USED] = True
    _save_necro(character, block)
    character.hp_max = character_service._compute_hp_max(
        character.stat_vitality,
        character.stat_strength,
        arch,
    )
    character.mp_max = character_service._compute_mp_max(character.stat_intelligence, arch)
    character.hp_current = character.hp_max
    character.mp_current = character.mp_max
    return True, f"Ритуал завершён. Вы — {arch.name_ru}."


def mercenaries_blocked_message() -> str:
    return (
        "Некромант ведёт в бой только нежить. Наёмники отряда недоступны — "
        "настройте «Ковчег костей» в профиле."
    )
