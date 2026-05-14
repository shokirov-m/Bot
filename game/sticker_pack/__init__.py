"""Виртуальный стикер-пак: гача, коллекция, дуэли (не путать с Telegram-стикерами в чате)."""

from game.sticker_pack.catalog import (
    STICKER_PACK_TOTAL,
    StickerDef,
    all_sticker_defs,
    sticker_def_by_id,
)
from game.sticker_pack.battle import rps_score_bonus_multiplier, resolve_duel_scores

__all__ = [
    "STICKER_PACK_TOTAL",
    "StickerDef",
    "all_sticker_defs",
    "sticker_def_by_id",
    "rps_score_bonus_multiplier",
    "resolve_duel_scores",
]
