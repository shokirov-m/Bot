"""Текст главного меню с краткой сводкой героя."""

from __future__ import annotations

import html

from bot.i18n import t
from db.models.character import Character
from game.characters.path_ranks import path_rank_name_ru
from utils.ui import LINE_SEP


def format_menu_hub_html(character: Character, *, locale: str) -> str:
    rank = path_rank_name_ru(character)
    rank_s = html.escape(rank) if rank else "—"
    title_s = html.escape(character.active_title) if character.active_title else "—"
    ch = t(locale, "channel_display_name")
    return (
        f"{t(locale, 'hub_title')}\n"
        f"{LINE_SEP}\n"
        f"{t(locale, 'hub_floor_line', floor=int(character.floor_number), level=int(character.level))}\n"
        f"{t(locale, 'hub_rank_line', rank=rank_s)}\n"
        f"{t(locale, 'hub_title_line', title=title_s)}\n"
        f"{LINE_SEP}\n"
        f"{t(locale, 'hub_daily_hint', channel=html.escape(ch))}"
    )
