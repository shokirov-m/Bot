"""
Каталог стикеров-монстров (MVP): редкость, стихия (fire/water/earth), диапазоны ATK/DEF.
Веса гачи по типу редкости: 45 / 30 / 15 / 7 / 2.5 / 0.5 %.

Реальные стикеры Telegram (набор BashnyaIspytanij и др.): поле telegram_file_id в StickerDef —
узнай через /admin_sticker_set имя_набора у бота и вставь полный file_id в каталог.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Веса ×10 для целых: 450+300+150+70+25+5 = 1000
RARITY_WEIGHTS: Final[tuple[tuple[str, int], ...]] = (
    ("common", 450),
    ("uncommon", 300),
    ("rare", 150),
    ("epic", 70),
    ("legendary", 25),
    ("mythic", 5),
)

# ATK и DEF — при первом выпадении случайно в диапазоне [lo, hi]
RARITY_ATK_RANGE: Final[dict[str, tuple[int, int]]] = {
    "common": (10, 25),
    "uncommon": (26, 45),
    "rare": (46, 70),
    "epic": (71, 90),
    "legendary": (91, 110),
    "mythic": (111, 150),
}

RARITY_DEF_RANGE: Final[dict[str, tuple[int, int]]] = {
    "common": (5, 15),
    "uncommon": (12, 22),
    "rare": (18, 32),
    "epic": (28, 42),
    "legendary": (38, 52),
    "mythic": (50, 70),
}

RARITY_STARS_RU: Final[dict[str, str]] = {
    "common": "⭐",
    "uncommon": "⭐⭐",
    "rare": "⭐⭐⭐",
    "epic": "⭐⭐⭐⭐",
    "legendary": "⭐⭐⭐⭐⭐",
    "mythic": "⭐⭐⭐⭐⭐⭐",
}


@dataclass(frozen=True, slots=True)
class StickerDef:
    id: str
    name_ru: str
    rarity: str  # common | uncommon | rare | epic | legendary | mythic
    element: str  # fire | water | earth
    telegram_file_id: str | None = None  # для sendSticker после дропа (заполняется вручную)


# Компактные id для callback_data (≤64 байт)
STICKERS: Final[tuple[StickerDef, ...]] = (
    StickerDef("c1", "Лесной слизень", "common", "earth"),
    StickerDef("c2", "Каменный гоблин", "common", "earth"),
    StickerDef("c3", "Искорка", "common", "fire"),
    StickerDef("c4", "Капелька", "common", "water"),
    StickerDef("u1", "Пепельный волк", "uncommon", "fire"),
    StickerDef("u2", "Туманный дух", "uncommon", "water"),
    StickerDef("u3", "Корень-плеть", "uncommon", "earth"),
    StickerDef("r1", "Магма-змей", "rare", "fire"),
    StickerDef("r2", "Ледяной шип", "rare", "water"),
    StickerDef("e1", "Кристальный голем", "epic", "earth"),
    StickerDef("e2", "Штормовой элементаль", "epic", "water"),
    StickerDef("l1", "Огненный дракон", "legendary", "fire"),
    StickerDef("m1", "Прайм титан", "mythic", "earth"),
)

STICKER_PACK_TOTAL: Final[int] = len(STICKERS)

_BY_ID: dict[str, StickerDef] = {s.id: s for s in STICKERS}


def all_sticker_defs() -> tuple[StickerDef, ...]:
    return STICKERS


def sticker_def_by_id(sid: str) -> StickerDef | None:
    return _BY_ID.get(str(sid).strip())


def stickers_by_rarity(rarity: str) -> list[StickerDef]:
    r = str(rarity).strip().lower()
    return [s for s in STICKERS if s.rarity == r]
