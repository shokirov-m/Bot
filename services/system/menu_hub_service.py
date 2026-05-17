"""Текст главного меню с краткой сводкой героя."""

from __future__ import annotations

import html
from pathlib import Path

from bot.i18n import t
from db.models.character import Character
from game.characters.path_ranks import path_rank_name_ru
from game.core.paths import images_root
from utils.game_images_prefs import game_images_enabled
from utils.media.profile_portraits import portrait_path_for_character
from utils.telegram.ui import LINE_SEP


def resolve_menu_hub_photo_path(character: Character) -> Path | None:
    """
    Картинка для главного меню: портрет героя из регистрации; если нет — ``menu_hub.png``.
    Без фото, если у игрока выключены игровые картинки.
    """
    if not game_images_enabled(character):
        return None
    pp = portrait_path_for_character(character)
    if pp is not None and pp.is_file():
        return pp
    hub = images_root() / "menu_hub.png"
    return hub if hub.is_file() else None


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
        f"{t(locale, 'hub_pet_line')}\n"
        f"{LINE_SEP}\n"
        f"{t(locale, 'hub_daily_hint', channel=html.escape(ch))}"
    )
