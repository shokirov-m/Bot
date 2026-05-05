"""Текстовый справочник: рецепты мастерской по профессиям (результат и стоимость)."""

from __future__ import annotations

import html

from game.items.craft_resources import RESOURCE_DEFS
from utils.ui import format_craft_result_effects_block_html
from game.crafting.recipes_data import (
    PROF_ALCHEMIST,
    PROF_BLACKSMITH,
    PROF_JEWELER,
    RECIPES,
    is_forge_instant,
)

_RU_RARE: dict[str, str] = {
    "common": "о.",
    "uncommon": "н.",
    "rare": "р.",
    "epic": "эп.",
    "legendary": "лег.",
    "mythic": "миф.",
}


def _fmt_cost(cost: dict[str, int] | None) -> str:
    if not cost:
        return "—"
    parts: list[str] = []
    for k in sorted(cost.keys()):
        parts.append(f"{_RU_RARE.get(k, k)}×{int(cost[k])}")
    return ", ".join(parts)


def _fmt_craft_only(craft_cost: dict[str, int] | None) -> str:
    if not craft_cost:
        return "—"
    parts: list[str] = []
    for k in sorted(craft_cost.keys()):
        rid = str(k)
        label = str((RESOURCE_DEFS.get(rid) or {}).get("name_ru") or rid)
        parts.append(f"{label}×{int(craft_cost[k])}")
    return ", ".join(parts)


def catalog_text_for_profession(profession: str) -> str:
    """HTML: список рецептов для одной профессии (очередь мастерской + мгновенные в кузне)."""
    pk = str(profession).lower().strip()
    title = {
        PROF_BLACKSMITH: "⚒️ <b>Кузница</b>",
        PROF_ALCHEMIST: "⚗️ <b>Лаборатория</b>",
        PROF_JEWELER: "💎 <b>Ювелирная</b>",
    }.get(pk, f"⚙️ <b>{html.escape(pk)}</b>")
    timed: list[str] = []
    instant: list[str] = []
    prof_recipes = [r for r in RECIPES if str(r.get("profession")) == pk]
    prof_recipes.sort(
        key=lambda r: (int(r.get("min_profession_level", 1)), str(r.get("name_ru", r.get("id", "")))),
    )
    for r in prof_recipes:
        name = str(r.get("name_ru", r.get("id", "")))
        res = r.get("result") or {}
        rname = str(res.get("name", "—"))
        rare = _fmt_cost(dict(r.get("cost") or {}))
        named = _fmt_craft_only(dict(r.get("craft_cost") or {}))
        if rare != "—" and named != "—":
            cost = f"{rare} + {named}"
        elif named != "—":
            cost = named
        else:
            cost = rare
        mprof = int(r.get("min_profession_level", 1))
        mst = int(r.get("min_station_level", 1))
        mch = int(r.get("min_character_level", 1))
        bp = " <i>(нужен чертёж)</i>" if r.get("requires_blueprint") else ""
        craft_secs = int(r.get("craft_seconds") or 0)
        time_part = ""
        if not is_forge_instant(r) and craft_secs > 0:
            time_part = f" <i>Время крафта:</i> {max(1, (craft_secs + 59) // 60)} мин."
        eff_extra = ""
        if isinstance(res, dict):
            eff_txt = format_craft_result_effects_block_html(res)
            if eff_txt.strip():
                eff_extra = "\n  <b>Что даёт предмет:</b>\n  " + eff_txt.replace("\n", "\n  ")
        line = (
            f"• <b>{html.escape(name)}</b> → {html.escape(rname)}{bp}{eff_extra}\n"
            f"  <i>Материалы:</i> {html.escape(cost)}. "
            f"<i>Нужно:</i> проф. {mprof}+, станок {mst}+, герой {mch}+.{time_part}"
        )
        if is_forge_instant(r):
            instant.append(line)
        else:
            timed.append(line)
    chunks: list[str] = [title, ""]
    if timed:
        chunks.append("<b>Очередь мастерской</b>")
        chunks.extend(timed)
        chunks.append("")
    if instant:
        chunks.append("<b>Мгновенно (городская кузня)</b>")
        chunks.extend(instant)
    if len(chunks) <= 2:
        return f"{title}\n\n<i>Нет рецептов в каталоге.</i>"
    return "\n".join(chunks)
