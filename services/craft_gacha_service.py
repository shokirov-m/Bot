"""
Гача ремесленных ресурсов в доме: случайный материал профессии + шанс чертежа.
"""

from __future__ import annotations

import html
import random
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character
from db.repository import inventory_repo
from game.crafting.recipes_data import (
    PROF_ALCHEMIST,
    PROF_BLACKSMITH,
    PROF_JEWELER,
    recipes_for_profession,
)
from game.crafting.workshop_meta import add_known_blueprint, known_blueprint_ids
from game.items.craft_resources import (
    RESOURCE_DEFS,
    craft_resource_payload,
    gacha_weights_for_profession,
    roll_stack_count_for_stars,
)
from services import character_service

GACHA_PULL_COST_GOLD = 500
BLUEPRINT_ROLL_CHANCE = 0.065


def _weighted_pick(profession: str) -> str | None:
    wmap = gacha_weights_for_profession(str(profession).strip().lower())
    keys = list(wmap.keys())
    weights = [max(0.01, float(wmap[k])) for k in keys]
    if not keys:
        return None
    return random.choices(keys, weights=weights, k=1)[0]


def _blueprint_pool(profession: str, character: Character) -> list[str]:
    known = known_blueprint_ids(character)
    out: list[str] = []
    for r in recipes_for_profession(profession):
        if not bool(r.get("requires_blueprint")):
            continue
        rid = str(r.get("id") or "")
        if rid and rid not in known:
            out.append(rid)
    return out


def format_gacha_intro_html(character: Character) -> str:
    from services import home_service

    if not home_service.can_access_workbench(character):
        return (
            "🎰 <b>Гача ресурсов</b>\n"
            "<i>Откроется вместе с постройками дома (ур. 2).</i>"
        )
    lines = [
        "🎰 <b>Гача ремесленных ресурсов</b>",
        f"<i>Один призыв:</i> <b>{GACHA_PULL_COST_GOLD:,} 💰</b>",
        "",
        "Выпадет <b>случайный материал</b> выбранной профессии (⭐ — редкость).",
        f"Шанс <b>чертёжа</b> (ещё не изученного): ≈{int(BLUEPRINT_ROLL_CHANCE * 100)}%.",
        "",
        "<b>Кузнец</b> — металлы (мифрил ⭐4, адамантит ⭐6 очень редко).",
        "<b>Алхимик</b> — травы и реагенты.",
        "<b>Ювелир</b> — камни и кристаллы.",
    ]
    return "\n".join(lines)


async def try_gacha_pull(
    session: AsyncSession,
    character: Character,
    profession: str,
) -> tuple[bool, list[str]]:
    """Списать золото, выдать материал и с шансом — чертёж."""
    from services import home_service

    if not home_service.can_access_workbench(character):
        return False, ["Сначала улучши дом до ур. 2."]

    prof = str(profession).strip().lower()
    if prof not in (PROF_BLACKSMITH, PROF_ALCHEMIST, PROF_JEWELER):
        return False, ["Неизвестная профессия."]

    if int(character.gold) < GACHA_PULL_COST_GOLD:
        return False, [f"Нужно {GACHA_PULL_COST_GOLD:,} 💰."]

    rid_pick = _weighted_pick(prof)
    if rid_pick is None:
        return False, ["Внутренняя ошибка таблицы гачи."]

    d = RESOURCE_DEFS.get(rid_pick) or {}
    stars = int(d.get("stars") or 1)
    count = roll_stack_count_for_stars(stars)
    payload = craft_resource_payload(rid_pick, count)

    character_service.add_gold(
        character,
        -GACHA_PULL_COST_GOLD,
        spend_for="Гача ремесленных ресурсов",
        spend_kind="home",
    )

    row = await inventory_repo.add_bag_item(session, character.id, payload)
    if row is None:
        character_service.add_gold(character, GACHA_PULL_COST_GOLD, spend_for="Откат гачи (нет места)", spend_kind="home")
        return False, ["Нет места в сумке для материала."]

    lines_out: list[str] = [
        f"−{GACHA_PULL_COST_GOLD:,} 💰",
        "",
        f"📦 <b>{html.escape(str(payload.get('name') or rid_pick))}</b> ×{count}",
    ]

    bp_lines: list[str] = []
    pool = _blueprint_pool(prof, character)
    if pool and random.random() < BLUEPRINT_ROLL_CHANCE:
        bp_id = random.choice(pool)
        add_known_blueprint(character, bp_id)
        # локализованное имя рецепта
        from game.crafting.recipes_data import get_recipe_by_id

        rr = get_recipe_by_id(bp_id)
        nm = html.escape(str((rr or {}).get("name_ru") or bp_id))
        bp_lines.append(f"\n📜 <b>Чертёж:</b> {nm}")

    await session.flush()

    return True, lines_out + bp_lines
