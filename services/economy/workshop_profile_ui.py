"""Строки профиля: выбранная профессия для отображения, полоска опыта, специализация."""

from __future__ import annotations

import html

from db.models.character import Character
from game.archetypes import manager as arch_manager
from game.crafting.recipes_data import (
    PROF_ALCHEMIST,
    PROF_BLACKSMITH,
    PROF_JEWELER,
    xp_to_next_profession_level,
)
from game.crafting.workshop_constants import max_profession_level
from game.crafting.workshop_meta import get_workshop_state
from utils.telegram.ui import _BAR_LEN, render_exp_bar


_PROF_RU: dict[str, str] = {
    PROF_BLACKSMITH: "Кузнец",
    PROF_ALCHEMIST: "Алхимик",
    PROF_JEWELER: "Ювелир",
}


def workshop_compact_line(character: Character) -> str:
    """Одна строка для компактного статуса: класс уже есть — добавляем ремесло."""
    a = arch_manager.get_character_archetype(character)
    class_disp = f"{a.emoji} {a.name_ru}"
    ws = get_workshop_state(character)
    show = str(ws.get("status_profession") or PROF_BLACKSMITH).lower()
    if show not in _PROF_RU:
        show = PROF_BLACKSMITH
    pl = int(ws["prof_levels"].get(show, 1))
    px = int(ws["prof_xp"].get(show, 0))
    cap = max_profession_level(show)
    need = xp_to_next_profession_level(pl, show) if pl < cap else 0
    lab = _PROF_RU.get(show, show)
    spec = ws.get("spec_profession")
    spec_s = ""
    if isinstance(spec, str) and spec in _PROF_RU:
        spec_s = f" · спец.: {_PROF_RU[spec]}"
    return (
        f"🔧 Ремесло: <b>{html.escape(lab)}</b> ур.{pl}"
        f"{html.escape(spec_s)} · класс: <b>{html.escape(class_disp)}</b>"
    )


def workshop_full_stats_block(character: Character) -> str:
    """Блок для полных характеристик: три профессии с полоской прогресса."""
    ws = get_workshop_state(character)
    lines: list[str] = ["", "🔧 <b>Мастерская</b>", ""]
    for pk, title in _PROF_RU.items():
        pl = int(ws["prof_levels"].get(pk, 1))
        px = int(ws["prof_xp"].get(pk, 0))
        cap = max_profession_level(pk)
        need = xp_to_next_profession_level(pl, pk) if pl < cap else 0
        pct_line = (
            render_exp_bar(px, need, wrap_bar_in_code=False)
            if need > 0
            else "✅ Макс."
        )
        st_lv = int(ws["stations"].get(pk, 1))
        lines.append(f"<b>{title}</b> — ур.{pl}/{cap}, станок {st_lv}")
        lines.append(f"{pct_line}  <i>{px}/{need if need else '—'}</i>")
        lines.append("")
    show = str(ws.get("status_profession") or PROF_BLACKSMITH)
    lines.append(
        f"<i>На карточке показывается: {_PROF_RU.get(show, show)} "
        f"(смена в «Специализация → ремесло»).</i>",
    )
    return "\n".join(lines)
