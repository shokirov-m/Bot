"""
Души некроманта: валюта, дроп с мобов, лавка и прокачка нежити.
Только класс necromancer.
"""

from __future__ import annotations

import html
import random
from dataclasses import dataclass
from typing import Any

from db.models.character import Character
from game.necromancer.service import (
    META_NECRO,
    SKELETON_ROLES,
    _necro_block,
    _save_necro,
    ensure_necro_meta,
    is_necromancer,
    skeleton_role_label,
    unlocked_skeleton_keys,
)

META_SOULS = "souls"
META_SOUL_SHOP = "soul_shop_levels"
META_SKEL_UPGRADES = "skeleton_upgrades"

SOUL_DROP_CHANCE = 0.5
MAX_SKEL_UPGRADE_LEVEL = 5


@dataclass(frozen=True, slots=True)
class SoulShopItem:
    key: str
    name_ru: str
    blurb: str
    base_cost: int
    max_level: int
    effect: str  # int_stat | barrier_pct | skel_atk_pct


SOUL_SHOP: dict[str, SoulShopItem] = {
    "nec_soul_int": SoulShopItem(
        "nec_soul_int",
        "Резонанс душ",
        "+2 к ИНТ (постоянно).",
        8,
        5,
        "int_stat",
    ),
    "nec_soul_barrier": SoulShopItem(
        "nec_soul_barrier",
        "Укрепление барьера",
        "+4% к HP защитного барьера.",
        6,
        10,
        "barrier_pct",
    ),
    "nec_soul_undead": SoulShopItem(
        "nec_soul_undead",
        "Воля нежити",
        "+3% к урону скелетов в бою.",
        5,
        10,
        "skel_atk_pct",
    ),
}


def get_souls(character: Character) -> int:
    if not is_necromancer(character):
        return 0
    block = _necro_block(character)
    return max(0, int(block.get(META_SOULS) or 0))


def add_souls(character: Character, amount: int) -> int:
    if not is_necromancer(character) or amount <= 0:
        return get_souls(character)
    block = ensure_necro_meta(character)
    new_val = max(0, int(block.get(META_SOULS) or 0) + int(amount))
    block[META_SOULS] = new_val
    _save_necro(character, block)
    return new_val


def spend_souls(character: Character, amount: int) -> bool:
    if amount <= 0:
        return True
    if get_souls(character) < amount:
        return False
    block = ensure_necro_meta(character)
    block[META_SOULS] = int(block.get(META_SOULS) or 0) - int(amount)
    _save_necro(character, block)
    return True


def maybe_grant_soul_on_victory(character: Character) -> int:
    """50% шанс +1 душа после победы в башне (только некромант)."""
    if not is_necromancer(character):
        return 0
    if random.random() >= SOUL_DROP_CHANCE:
        return 0
    add_souls(character, 1)
    return 1


def _shop_levels(block: dict[str, Any]) -> dict[str, int]:
    raw = dict(block.get(META_SOUL_SHOP) or {})
    return {str(k): max(0, int(v)) for k, v in raw.items()}


def soul_shop_level(character: Character, item_key: str) -> int:
    if not is_necromancer(character):
        return 0
    return _shop_levels(_necro_block(character)).get(str(item_key), 0)


def soul_shop_item_cost(item: SoulShopItem, current_level: int) -> int:
    return max(1, int(item.base_cost + current_level * 2))


def try_buy_soul_shop_item(character: Character, item_key: str) -> tuple[bool, str]:
    if not is_necromancer(character):
        return False, "Лавка душ только у некроманта."
    item = SOUL_SHOP.get(str(item_key))
    if item is None:
        return False, "Нет такого улучшения."
    block = ensure_necro_meta(character)
    levels = _shop_levels(block)
    cur = int(levels.get(item.key, 0))
    if cur >= item.max_level:
        return False, "Улучшение уже на максимуме."
    cost = soul_shop_item_cost(item, cur)
    if not spend_souls(character, cost):
        return False, f"Нужно {cost} 👻 (у вас {get_souls(character)})."
    levels[item.key] = cur + 1
    block[META_SOUL_SHOP] = levels
    if item.effect == "int_stat":
        character.stat_intelligence = int(character.stat_intelligence or 0) + 2
    _save_necro(character, block)
    return True, f"Куплено: {item.name_ru} (ур. {cur + 1}/{item.max_level})."


def soul_shop_barrier_bonus_pct(character: Character) -> float:
    lv = soul_shop_level(character, "nec_soul_barrier")
    return lv * 0.04


def soul_shop_skeleton_atk_bonus_pct(character: Character) -> float:
    lv = soul_shop_level(character, "nec_soul_undead")
    return lv * 0.03


def _skeleton_upgrades(block: dict[str, Any]) -> dict[str, dict[str, int]]:
    raw = dict(block.get(META_SKEL_UPGRADES) or {})
    out: dict[str, dict[str, int]] = {}
    for sk, data in raw.items():
        if sk not in SKELETON_ROLES:
            continue
        d = dict(data or {})
        out[str(sk)] = {
            "atk": max(0, min(MAX_SKEL_UPGRADE_LEVEL, int(d.get("atk", 0)))),
            "hp": max(0, min(MAX_SKEL_UPGRADE_LEVEL, int(d.get("hp", 0)))),
        }
    return out


def skeleton_upgrade_levels(character: Character, role_key: str) -> tuple[int, int]:
    if not is_necromancer(character):
        return 0, 0
    up = _skeleton_upgrades(_necro_block(character)).get(str(role_key), {})
    return int(up.get("atk", 0)), int(up.get("hp", 0))


def skeleton_upgrade_cost(current_level: int) -> int:
    return max(2, 3 + int(current_level) * 2)


def try_upgrade_skeleton(character: Character, role_key: str, *, kind: str) -> tuple[bool, str]:
    if not is_necromancer(character):
        return False, "Только для некроманта."
    rk = str(role_key)
    if rk not in unlocked_skeleton_keys(character):
        return False, "Этот тип нежити не открыт."
    k = str(kind).lower()
    if k not in ("atk", "hp"):
        return False, "Неизвестный тип улучшения."
    block = ensure_necro_meta(character)
    all_up = _skeleton_upgrades(block)
    cur = dict(all_up.get(rk) or {"atk": 0, "hp": 0})
    lv = int(cur.get(k, 0))
    if lv >= MAX_SKEL_UPGRADE_LEVEL:
        return False, "Улучшение на максимуме."
    cost = skeleton_upgrade_cost(lv)
    if not spend_souls(character, cost):
        return False, f"Нужно {cost} 👻."
    cur[k] = lv + 1
    all_up[rk] = cur
    block[META_SKEL_UPGRADES] = all_up
    _save_necro(character, block)
    label = "атаки" if k == "atk" else "HP"
    return True, f"{skeleton_role_label(rk)}: +1 ур. {label} ({lv + 1}/{MAX_SKEL_UPGRADE_LEVEL})."


def skeleton_upgrade_mults(character: Character, role_key: str) -> tuple[float, float]:
    atk_lv, hp_lv = skeleton_upgrade_levels(character, role_key)
    return 1.0 + atk_lv * 0.08, 1.0 + hp_lv * 0.10


def format_soul_shop_html(character: Character) -> str:
    bal = get_souls(character)
    lines = [
        "👻 <b>Лавка душ</b>",
        f"<i>Души выпадают с врагов башни (шанс {int(SOUL_DROP_CHANCE * 100)}%). Баланс: <b>{bal}</b> 👻</i>",
        "",
    ]
    for item in SOUL_SHOP.values():
        lv = soul_shop_level(character, item.key)
        cost = soul_shop_item_cost(item, lv) if lv < item.max_level else 0
        if lv >= item.max_level:
            status = f"MAX ({item.max_level})"
        else:
            status = f"ур. {lv}/{item.max_level} — <b>{cost}</b> 👻"
        lines.append(f"• <b>{html.escape(item.name_ru)}</b> — {status}")
        lines.append(f"  <i>{html.escape(item.blurb)}</i>")
    return "\n".join(lines)


def format_skeleton_quarters_html(character: Character) -> str:
    party = set()
    from game.necromancer.service import get_party_skeleton_keys

    party = set(get_party_skeleton_keys(character))
    lines = [
        "🦴 <b>Покои нежити</b>",
        f"<i>👻 Душ: <b>{get_souls(character)}</b>. Улучшайте скелетов за души.</i>",
        "",
    ]
    for key in sorted(unlocked_skeleton_keys(character)):
        rd = SKELETON_ROLES[key]
        atk_lv, hp_lv = skeleton_upgrade_levels(character, key)
        mark = " — <b>в отряде</b>" if key in party else ""
        lines.append(
            f"{rd.emoji} <b>{html.escape(rd.name_ru)}</b>{mark}\n"
            f"  ⚔️ атака ур.{atk_lv}/{MAX_SKEL_UPGRADE_LEVEL} · "
            f"🛡 HP ур.{hp_lv}/{MAX_SKEL_UPGRADE_LEVEL}",
        )
    if not unlocked:
        lines.append("<i>Нет открытых типов нежити.</i>")
    return "\n".join(lines)


def format_skeleton_detail_html(character: Character, role_key: str) -> str:
    rk = str(role_key)
    rd = SKELETON_ROLES.get(rk)
    if rd is None or rk not in unlocked_skeleton_keys(character):
        return "Неизвестный скелет."
    atk_lv, hp_lv = skeleton_upgrade_levels(character, rk)
    atk_cost = skeleton_upgrade_cost(atk_lv) if atk_lv < MAX_SKEL_UPGRADE_LEVEL else 0
    hp_cost = skeleton_upgrade_cost(hp_lv) if hp_lv < MAX_SKEL_UPGRADE_LEVEL else 0
    from game.necromancer.skeleton_abilities import ability_for_role

    ab = ability_for_role(rk)
    ab_line = f"⚡ <b>{ab.name_ru}</b> (КД {ab.cooldown} х.) — <i>{html.escape(ab.blurb)}</i>" if ab else ""
    return (
        f"{rd.emoji} <b>{html.escape(rd.name_ru)}</b>\n\n"
        f"👻 Душ: <b>{get_souls(character)}</b>\n\n"
        f"⚔️ Урон: улучшение <b>{atk_lv}/{MAX_SKEL_UPGRADE_LEVEL}</b>"
        + (f" — следующее: <b>{atk_cost}</b> 👻" if atk_cost else " (MAX)")
        + f"\n🛡 HP: улучшение <b>{hp_lv}/{MAX_SKEL_UPGRADE_LEVEL}</b>"
        + (f" — следующее: <b>{hp_cost}</b> 👻" if hp_cost else " (MAX)")
        + (f"\n\n{ab_line}" if ab_line else "")
    )
