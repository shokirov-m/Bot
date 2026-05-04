"""
Мастерская: очередь крафта, опыт профессий, ускорение рунными камнями, бонусы классов.
"""

from __future__ import annotations

import copy
import html
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import character_repo, inventory_repo
from game.crafting.recipes_data import (
    PROF_ALCHEMIST,
    PROF_BLACKSMITH,
    PROF_JEWELER,
    get_recipe_by_id,
    is_forge_instant,
    max_station_level_cap,
    recipes_for_profession,
    xp_to_next_profession_level,
)
from game.crafting.workshop_constants import max_profession_level
from game.crafting.workshop_meta import (
    add_known_blueprint,
    get_workshop_state,
    increment_counter,
    new_craft_slot_id,
    prof_level,
    save_workshop_state,
    station_level,
    known_blueprint_ids,
    WORKSHOP_META_KEY,
)
from services import achievement_service, character_service, title_service
from services.forge_service import _consume_materials  # noqa: SLF001
from game.items import craft_resources as cr_sys
from game.items import materials as mat_sys


def _forgemaster_star_cap(blacksmith_level: int) -> int:
    """Максимум звёзд на крафте кузнеца (1..5) по уровню профессии."""
    lv = max(1, min(30, int(blacksmith_level)))
    if lv >= 26:
        return 5
    if lv >= 21:
        return 4
    if lv >= 15:
        return 3
    if lv >= 9:
        return 2
    return 1


def roll_forge_stars(blacksmith_level: int) -> int:
    cap = _forgemaster_star_cap(blacksmith_level)
    return random.randint(1, cap)


_WORKSHOP_ALCHEMY_ENCHANT_TAG = "workshop_alchemy_enchant"


def apply_workshop_craft_premium(item_payload: dict[str, Any]) -> dict[str, Any]:
    """Крафт мастерской чуть сильнее типичного лута той же редкости (числовые статы / зелья)."""
    out = dict(item_payload)
    kind = str(out.get("kind") or "")
    ut = str(out.get("use_tag") or "")
    if kind == "consumable" and ut == _WORKSHOP_ALCHEMY_ENCHANT_TAG:
        return out
    rare = str(out.get("rarity") or "common").lower()
    mult = {
        "common": 1.14,
        "uncommon": 1.15,
        "rare": 1.16,
        "epic": 1.17,
        "legendary": 1.16,
        "mythic": 1.15,
    }.get(rare, 1.15)
    if kind == "consumable" and ut in ("heal_hp_pct", "heal_mp_pct"):
        uv = int(out.get("use_value") or 0)
        if uv > 0:
            out["use_value"] = max(1, int(round(uv * mult)))
        return out
    for k in ("attack", "defense", "armor", "str", "dex", "int", "vit"):
        if k not in out:
            continue
        try:
            base = float(out[k])
        except (TypeError, ValueError):
            continue
        if base != 0:
            out[k] = max(1, int(round(base * mult)))
    return out


def apply_blacksmith_forge_quality(character: Character, item_payload: dict[str, Any]) -> dict[str, Any]:
    """Звёзды качества и усиление статов для предметов кузнеца."""
    out = dict(item_payload)
    lv = prof_level(character, PROF_BLACKSMITH)
    stars = roll_forge_stars(lv)
    out["forge_stars"] = stars
    mult = 1.0 + 0.11 * max(0, stars - 1)
    for k in ("attack", "defense", "armor", "str", "dex", "int", "vit"):
        if k not in out:
            continue
        try:
            base = float(out[k])
        except (TypeError, ValueError):
            continue
        if base != 0:
            out[k] = max(1, int(round(base * mult)))
    return out


def _workshop_xp_multiplier(character: Character, profession: str) -> float:
    mult = 1.0
    k = str(character.class_key or "wanderer").lower()
    if k == "priest":
        mult *= 1.05
    ws = get_workshop_state(character)
    if str(ws.get("spec_profession") or "").lower() == str(profession).lower():
        mult *= 1.10
    return mult


def _class_ingredient_discount_roll(class_key: str) -> bool:
    """Маг: шанс не потратить часть common материала (упрощённо — один бросок)."""
    if str(class_key or "").lower() != "mage":
        return False
    return random.random() < 0.05


def _durability_bonus_pct(class_key: str) -> int:
    if str(class_key or "").lower() == "warrior":
        return 5
    return 0


def queue_capacity(character: Character) -> int:
    ws = get_workshop_state(character)
    bonus = int(ws.get("queue_bonus", 0))
    return 3 + max(0, bonus)


def _active_queue_len(ws: dict[str, Any]) -> int:
    return len(list(ws.get("active_crafts") or []))


def _can_afford(cost: dict[str, int], bag_items: list[Any]) -> bool:
    for r, n in cost.items():
        if mat_sys.total_materials_in_bag(bag_items, r) < int(n):
            return False
    return True


def _can_afford_craft_cost(bag_items: list[Any], craft_cost: dict[str, int]) -> bool:
    for rid, n in craft_cost.items():
        if cr_sys.total_craft_resource_in_bag(bag_items, str(rid)) < int(n):
            return False
    return True


async def _consume_recipe_cost(
    session: AsyncSession,
    character: Character,
    cost: dict[str, int],
) -> None:
    """Списать материалы заточки; маг иногда экономит 1 ед. common."""
    skip_common_one = _class_ingredient_discount_roll(character.class_key)
    for rare, n in sorted(cost.items(), key=lambda x: x[0]):
        amt = int(n)
        if skip_common_one and str(rare).lower() == "common" and amt > 0:
            amt -= 1
            skip_common_one = False
        if amt > 0:
            await _consume_materials(session, int(character.id), str(rare), amt)


async def _consume_recipe_craft_cost(
    session: AsyncSession,
    character: Character,
    craft_cost: dict[str, int],
) -> None:
    if craft_cost:
        await cr_sys.consume_craft_resources(session, int(character.id), craft_cost)


def validate_start(
    character: Character,
    recipe_id: str,
) -> tuple[bool, str]:
    r = get_recipe_by_id(recipe_id)
    if r is None:
        return False, "Нет такого рецепта."
    if is_forge_instant(r):
        return False, "Этот рецепт крафтится мгновенно в городской кузнице."
    prof = str(r.get("profession", ""))
    need_p = int(r.get("min_profession_level", 1))
    need_s = int(r.get("min_station_level", 1))
    need_lv = int(r.get("min_character_level", 1))
    max_p = max_profession_level(prof)
    if need_p > max_p:
        return False, "Рецепт устарел (левел профессии выше потолка)."
    if int(character.level) < need_lv:
        return False, f"Нужен {need_lv} уровень героя."
    if prof_level(character, prof) < need_p:
        return False, "Низкий уровень профессии."
    if station_level(character, prof) < need_s:
        return False, "Нужен более высокий станок."
    if bool(r.get("requires_blueprint")):
        rid = str(r.get("id"))
        if rid not in known_blueprint_ids(character):
            return False, "Нужен чертёж (таверна, дроп, награда)."
    ws = get_workshop_state(character)
    if _active_queue_len(ws) >= queue_capacity(character):
        return False, "Очередь полна. Забери готовое или расширь лимит позже."
    return True, ""


async def try_start_craft(
    session: AsyncSession,
    character: Character,
    recipe_id: str,
    qty: int = 1,
) -> tuple[bool, list[str]]:
    await character_repo.lock_character_row(session, character.id)
    ok, err = validate_start(character, recipe_id)
    if not ok:
        return False, [err]
    r = get_recipe_by_id(recipe_id)
    if r is None:
        return False, ["Нет рецепта."]
    if int(qty) != 1:
        return False, ["Очередь: по одному крафту за раз."]
    bag_items = await inventory_repo.list_bag_items(session, character.id)
    cost = dict(r.get("cost") or {})
    craft_cost = {str(k): int(v) for k, v in (r.get("craft_cost") or {}).items()}
    if not _can_afford(cost, bag_items):
        return False, ["Недостаточно материалов."]
    if craft_cost and not _can_afford_craft_cost(bag_items, craft_cost):
        return False, ["Недостаточно специальных материалов (гача / ремесленные слитки)."]
    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, ["Нет свободной ячейки в сумке (нужна для готового)."]

    await _consume_recipe_cost(session, character, cost)
    await _consume_recipe_craft_cost(session, character, craft_cost)

    seconds = int(r.get("craft_seconds") or 300)
    base_xp = int(r.get("xp_reward") or 10)
    prof_key = str(r.get("profession", PROF_BLACKSMITH))
    xp_mult = _workshop_xp_multiplier(character, prof_key)
    xp_gain = max(1, int(round(base_xp * xp_mult)))

    now = datetime.now(UTC)
    ready_at = now + timedelta(seconds=seconds)
    slot_id = new_craft_slot_id()
    ws = get_workshop_state(character)
    entry = {
        "slot_id": slot_id,
        "recipe_id": str(r.get("id")),
        "started_at": now.isoformat(),
        "ready_at": ready_at.isoformat(),
        "qty": 1,
        "xp_reserved": xp_gain,
        "dur_bonus_pct": _durability_bonus_pct(character.class_key),
    }
    ws.setdefault("active_crafts", []).append(entry)
    save_workshop_state(character, ws)
    await session.flush()
    nm = html.escape(str(r.get("name_ru", recipe_id)))
    return True, [
        f"🔧 <b>{nm}</b> в работе.",
        f"⏱ Готово около: <i>{ready_at.strftime('%H:%M UTC')}</i>",
        f"✨ Опыт профессии начислится при сборе: ~{xp_gain}",
    ]


def _parse_iso(ts: str) -> datetime | None:
    try:
        t = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(t)
    except (ValueError, TypeError):
        return None


async def try_claim_craft(
    session: AsyncSession,
    character: Character,
    slot_id: str,
) -> tuple[bool, list[str]]:
    await character_repo.lock_character_row(session, character.id)
    ws = get_workshop_state(character)
    crafts = list(ws.get("active_crafts") or [])
    idx = next((i for i, c in enumerate(crafts) if str(c.get("slot_id")) == str(slot_id)), None)
    if idx is None:
        return False, ["Слот не найден."]
    entry = crafts[idx]
    ready = _parse_iso(str(entry.get("ready_at") or ""))
    if ready is None or datetime.now(UTC) < ready:
        return False, ["Ещё не готово."]
    rid = str(entry.get("recipe_id", ""))
    r = get_recipe_by_id(rid)
    if r is None:
        crafts.pop(idx)
        ws["active_crafts"] = crafts
        save_workshop_state(character, ws)
        return False, ["Рецепт удалён из игры — слот очищен."]

    free = await inventory_repo.first_free_bag_slot(session, character.id)
    if free is None:
        return False, ["Нет места в сумке для готового предмета."]

    pl = copy.deepcopy(r["result"])
    pl = apply_workshop_craft_premium(pl)
    if str(r.get("profession")) == PROF_BLACKSMITH:
        pl = apply_blacksmith_forge_quality(character, pl)
    # воин: «прочность» — если есть поле durability_max в данных
    db = int(entry.get("dur_bonus_pct") or 0)
    if db and pl.get("durability_max") is not None:
        try:
            dm = int(pl["durability_max"])
            pl["durability_max"] = dm + max(1, dm * db // 100)
            if pl.get("durability_current") is not None:
                pl["durability_current"] = pl["durability_max"]
        except (TypeError, ValueError):
            pass

    await inventory_repo.add_bag_item(session, character.id, pl, bag_slot=free)
    crafts.pop(idx)
    ws["active_crafts"] = crafts
    save_workshop_state(character, ws)

    prof = str(r.get("profession", PROF_BLACKSMITH))
    xp_add = int(entry.get("xp_reserved") or int(r.get("xp_reward") or 10))
    _add_profession_xp(character, prof, xp_add)

    increment_counter(character, "crafts_done", 1)
    await session.flush()
    title_service.refresh_unlocks(character)
    achievement_service.check_and_apply_achievements(character)
    nm = html.escape(str(pl.get("name", "Предмет")))
    return True, [
        f"✅ Готово: <b>{nm}</b> (ячейка {free}).",
        f"+{xp_add} опыта профессии ({prof}).",
    ]


def _add_profession_xp(character: Character, profession: str, xp_add: int) -> None:
    ws = get_workshop_state(character)
    pk = str(profession)
    cap = max_profession_level(pk)
    lv = int(ws["prof_levels"].get(pk, 1))
    xp = int(ws["prof_xp"].get(pk, 0)) + max(0, int(xp_add))
    while lv < cap:
        need = xp_to_next_profession_level(lv, pk)
        if xp < need:
            break
        xp -= need
        lv += 1
    if lv >= cap:
        xp = 0
    ws["prof_levels"][pk] = lv
    ws["prof_xp"][pk] = xp
    save_workshop_state(character, ws)


async def try_accelerate(
    session: AsyncSession,
    character: Character,
    slot_id: str,
) -> tuple[bool, list[str]]:
    """−10 мин к готовности за 1 рунный камень (колонка rune_stones)."""
    await character_repo.lock_character_row(session, character.id)
    ws = get_workshop_state(character)
    crafts = list(ws.get("active_crafts") or [])
    idx = next((i for i, c in enumerate(crafts) if str(c.get("slot_id")) == str(slot_id)), None)
    if idx is None:
        return False, ["Слот не найден."]
    if int(character.rune_stones or 0) < 1:
        return False, ["Нужен рунный камень."]
    entry = crafts[idx]
    ready = _parse_iso(str(entry.get("ready_at") or ""))
    if ready is None:
        return False, ["Ошибка времени."]
    now = datetime.now(UTC)
    if ready <= now:
        return False, ["Уже готово — забери предмет."]
    new_ready = ready - timedelta(seconds=600)
    if new_ready < now:
        new_ready = now
    character.rune_stones = int(character.rune_stones) - 1
    entry["ready_at"] = new_ready.isoformat()
    crafts[idx] = entry
    ws["active_crafts"] = crafts
    save_workshop_state(character, ws)
    await session.flush()
    return True, ["⚡ −10 минут к готовности (−1 рунный камень)."]


async def try_upgrade_station(
    session: AsyncSession,
    character: Character,
    profession: str,
) -> tuple[bool, list[str]]:
    await character_repo.lock_character_row(session, character.id)
    pk = str(profession).strip().lower()
    if pk not in ("blacksmith", "alchemist", "jeweler"):
        return False, ["Неизвестная профессия."]
    ws = get_workshop_state(character)
    plv = int(ws["prof_levels"].get(pk, 1))
    cap = max_station_level_cap(plv)
    cur = int(ws["stations"].get(pk, 1))
    if cur >= cap:
        return False, [f"Станок на максимуме для твоего уровня профессии ({cap})."]
    if cur >= 5:
        return False, ["Максимальный уровень станка."]
    target = cur + 1
    gold_cost = 400 * target * target
    mat_cost = 2 * target
    if int(character.gold) < gold_cost:
        return False, [f"Нужно {gold_cost:,} золота."]
    bag = await inventory_repo.list_bag_items(session, character.id)
    if mat_sys.total_materials_in_bag(bag, "common") < mat_cost:
        return False, [f"Нужно {mat_cost} осколков стали (common)."]
    character_service.add_gold(character, -gold_cost, spend_for="Мастерская: станок", spend_kind="workshop")
    await _consume_materials(session, int(character.id), "common", mat_cost)
    ws["stations"][pk] = target
    save_workshop_state(character, ws)
    await session.flush()
    return True, [f"🔧 Станок улучшен до {target}/{cap}."]


def profession_summary_lines(character: Character, locale: str = "ru") -> list[str]:
    _ = locale
    ws = get_workshop_state(character)
    lines: list[str] = []
    labels = {
        PROF_BLACKSMITH: "⚒️ Кузнец",
        PROF_ALCHEMIST: "⚗️ Алхимик",
        PROF_JEWELER: "💎 Ювелир",
    }
    for pk, lab in labels.items():
        pl = int(ws["prof_levels"].get(pk, 1))
        px = int(ws["prof_xp"].get(pk, 0))
        mxl = max_profession_level(pk)
        need = xp_to_next_profession_level(pl, pk) if pl < mxl else 0
        st = int(ws["stations"].get(pk, 1))
        cap = max_station_level_cap(pl)
        xp_s = f"{px}/{need}" if pl < mxl else "MAX"
        lines.append(f"{lab}: ур. <b>{pl}</b>/{mxl} ({xp_s}), станок <b>{st}</b>/{cap}")
    return lines


def list_ready_slots(character: Character) -> list[str]:
    now = datetime.now(UTC)
    ws = get_workshop_state(character)
    out: list[str] = []
    for c in ws.get("active_crafts") or []:
        rdt = _parse_iso(str(c.get("ready_at") or ""))
        if rdt is not None and rdt <= now:
            out.append(str(c.get("slot_id")))
    return out


__all__ = [
    "queue_capacity",
    "validate_start",
    "try_start_craft",
    "try_claim_craft",
    "try_accelerate",
    "try_upgrade_station",
    "profession_summary_lines",
    "list_ready_slots",
    "recipes_for_profession",
    "PROF_BLACKSMITH",
    "PROF_ALCHEMIST",
    "PROF_JEWELER",
    "add_known_blueprint",
    "WORKSHOP_META_KEY",
    "apply_blacksmith_forge_quality",
]
