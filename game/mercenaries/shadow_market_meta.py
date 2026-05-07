"""Флаги «Тени Башни»: зачистка 26 этажа, визиты на рынок, отряд, доля XP."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character

META_SHADOW_MARKET = "shadow_market_v1"


def _sm(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_SHADOW_MARKET)
    return dict(raw) if isinstance(raw, dict) else {}


def _save(character: Character, sm: dict[str, Any]) -> None:
    mp = dict(character.meta_progress or {})
    mp[META_SHADOW_MARKET] = sm
    character.meta_progress = mp
    try:
        flag_modified(character, "meta_progress")
    except Exception:
        pass


def floor_26_shadow_cleared(character: Character) -> bool:
    return bool(_sm(character).get("floor_26_cleared"))


def mark_floor_26_shadow_cleared(character: Character) -> None:
    sm = _sm(character)
    sm["floor_26_cleared"] = True
    _save(character, sm)


def first_market_entry_free_used(character: Character) -> bool:
    return bool(_sm(character).get("first_entry_free_used"))


def mark_first_market_entry_used(character: Character) -> None:
    sm = _sm(character)
    sm["first_entry_free_used"] = True
    _save(character, sm)


def get_merc_xp_share_percent(character: Character) -> int:
    v = int(_sm(character).get("merc_xp_share_pct", 30))
    return max(20, min(40, v))


def set_merc_xp_share_percent(character: Character, pct: int) -> None:
    sm = _sm(character)
    sm["merc_xp_share_pct"] = max(20, min(40, int(pct)))
    _save(character, sm)


def get_party_merc_ids(character: Character) -> list[int]:
    raw = _sm(character).get("party_merc_ids") or []
    out: list[int] = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    max_in_battle = max_mercs_in_battle(character)
    return out[:max_in_battle]


def set_party_merc_ids(character: Character, ids: list[int]) -> None:
    sm = _sm(character)
    cap = max_mercs_in_battle(character)
    clean: list[int] = []
    for x in ids:
        try:
            ix = int(x)
        except (TypeError, ValueError):
            continue
        if ix not in clean:
            clean.append(ix)
        if len(clean) >= cap:
            break
    sm["party_merc_ids"] = clean
    _save(character, sm)


def roster_collection_cap(character: Character) -> int:
    lv = int(character.level)
    if lv < 15:
        return 0
    thresholds = ((60, 6), (55, 5), (45, 4), (35, 3), (25, 2), (15, 1))
    for need, cap in thresholds:
        if lv >= need:
            return cap
    return 0


def max_mercs_in_battle(character: Character) -> int:
    if int(character.level) >= 25:
        return 2
    return 1


def party_blocks_arena_coliseum(character: Character) -> bool:
    return len(get_party_merc_ids(character)) > 0


def arena_coliseum_block_message() -> str:
    return (
        "С активным отрядом наёмников сюда нельзя. Убери наёмников из отряда "
        "в Покоях (Дом) или заверши настройку отряда."
    )


def market_hub_session_open(character: Character) -> bool:
    return bool(_sm(character).get("hub_session_open"))


def open_market_hub_session(character: Character) -> None:
    sm = _sm(character)
    sm["hub_session_open"] = True
    _save(character, sm)


def close_market_hub_session(character: Character) -> None:
    sm = _sm(character)
    sm.pop("hub_session_open", None)
    _save(character, sm)
