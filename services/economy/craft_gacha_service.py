"""
Гача ремесленных ресурсов в мастерской: случайный материал профессии + шанс чертежа.
"""

from __future__ import annotations

import html
import random
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.character import Character

if TYPE_CHECKING:
    from aiogram import Bot
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
import services.progression.character_service as character_service

GACHA_PULL_COST_GOLD = 200
BLUEPRINT_ROLL_CHANCE = 0.065
GACHA_MAX_BATCH = 10


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
    import services.progression.home_service as home_service

    if not home_service.can_access_workbench(character):
        return (
            "🎰 <b>Гача ресурсов</b>\n"
            "<i>Доступна в мастерской после дома ур. 2 и верстака.</i>"
        )
    t1 = GACHA_PULL_COST_GOLD
    t10 = GACHA_PULL_COST_GOLD * 10
    lines = [
        "🎰 <b>Гача ремесленных ресурсов</b>\n<i>В мастерской.</i>",
        f"<i>Призыв ×1:</i> <b>{t1:,} 💰</b> · <i>×10:</i> <b>{t10:,} 💰</b>",
        "",
        "Выпадет <b>случайный материал</b> выбранной профессии (⭐ — редкость).",
        f"Шанс <b>чертёжа</b> (ещё не изученного) на <b>каждом</b> броске: ≈{int(BLUEPRINT_ROLL_CHANCE * 100)}%.",
        "",
        "<b>Кузнец</b> — металлы (высокие ⭐ реже).",
        "<b>Алхимик</b> — травы и реагенты.",
        "<b>Ювелир</b> — камни и кристаллы.",
    ]
    return "\n".join(lines)


async def try_gacha_pull(
    session: AsyncSession,
    character: Character,
    profession: str,
    *,
    times: int = 1,
    bot: "Bot | None" = None,
) -> tuple[bool, list[str], list[str]]:
    """Списать золото, выдать материал(ы) и с шансом — чертёж на каждом броске."""
    import services.progression.home_service as home_service

    if not home_service.can_access_workbench(character):
        return False, ["Сначала улучши дом до ур. 2."], []

    prof = str(profession).strip().lower()
    if prof not in (PROF_BLACKSMITH, PROF_ALCHEMIST, PROF_JEWELER):
        return False, ["Неизвестная профессия."], []

    n = max(1, min(GACHA_MAX_BATCH, int(times)))
    total_cost = GACHA_PULL_COST_GOLD * n
    if int(character.gold) < total_cost:
        return False, [f"Нужно {total_cost:,} 💰 (×{n})."], []

    character_service.add_gold(
        character,
        -total_cost,
        spend_for="Гача ремесленных ресурсов",
        spend_kind="workshop",
    )

    lines_out: list[str] = [
        f"−{total_cost:,} 💰",
        f"<i>Призывов: ×{n}</i>",
        "",
    ]
    any_item = False
    pulled_resource_ids: list[str] = []
    for i in range(n):
        rid_pick = _weighted_pick(prof)
        if rid_pick is None:
            refund = (n - i) * GACHA_PULL_COST_GOLD
            if refund:
                character_service.add_gold(
                    character,
                    refund,
                    spend_for="Откат гачи (таблица)",
                    spend_kind="workshop",
                )
            return False, lines_out + [f"Ошибка таблицы. Возврат: {refund} 💰."], pulled_resource_ids

        d = RESOURCE_DEFS.get(rid_pick) or {}
        stars = int(d.get("stars") or 1)
        count = roll_stack_count_for_stars(stars)
        payload = craft_resource_payload(rid_pick, count)
        row = await inventory_repo.add_bag_item(session, character.id, payload)
        if row is None:
            refund = (n - i) * GACHA_PULL_COST_GOLD
            if refund:
                character_service.add_gold(
                    character,
                    refund,
                    spend_for="Откат гачи (нет места)",
                    spend_kind="workshop",
                )
            if not any_item:
                return False, lines_out + [f"Нет места в сумке. Возврат: {refund} 💰."], pulled_resource_ids
            return True, lines_out + [
                "",
                f"⚠️ <b>Сумка полна</b> — дальше {n - i} призыв(ов) не сделано, возврат <b>{refund:,}</b> 💰.",
            ], pulled_resource_ids

        any_item = True
        pulled_resource_ids.append(str(rid_pick))
        lines_out.append(f"📦 <b>{html.escape(str(payload.get('name') or rid_pick))}</b> ×{count}")

        if bot is not None and stars >= 6:
            import services.social.gacha_broadcast_service as gacha_broadcast_service

            await gacha_broadcast_service.notify_high_star_material(
                bot,
                session,
                character,
                stars=stars,
                material_name=str(payload.get("name") or rid_pick),
                quantity=count,
            )

        pool = _blueprint_pool(prof, character)
        if pool and random.random() < BLUEPRINT_ROLL_CHANCE:
            bp_id = random.choice(pool)
            add_known_blueprint(character, bp_id)
            from game.crafting.recipes_data import get_recipe_by_id

            rr = get_recipe_by_id(bp_id)
            nm = html.escape(str((rr or {}).get("name_ru") or bp_id))
            lines_out.append(f"📜 <b>Чертёж:</b> {nm}")

    await session.flush()
    return True, lines_out, pulled_resource_ids
