"""
Профессии: meta_progress, разблокировки, активные слоты, бонусы для статов и боя.
"""

from __future__ import annotations

from typing import Any

from db.models.character import Character
from game.characters.professions import (
    PROFESSIONS,
    PROFESSION_BY_KEY,
    SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR,
    EnchantAttemptsGeUnlock,
    ProfessionDef,
    StatGeUnlock,
    STAT_COLUMN,
)
from game.items.stat_bonuses import STAT_KEYS, empty_stat_bonus_map

META_UNLOCKED = "professions_unlocked"
META_ACTIVE_PRIMARY = "active_profession"
META_ACTIVE_SECONDARY = "active_profession_2"
META_MIGRATED = "_professions_migrated_v1"


def _mp(character: Character) -> dict[str, Any]:
    return dict(character.meta_progress or {})


def _save_mp(character: Character, mp: dict[str, Any]) -> None:
    character.meta_progress = mp


def meets_unlock(character: Character, prof: ProfessionDef) -> bool:
    """Условия разблокировки по базовым полям персонажа (без экипа)."""
    for cond in prof.unlock:
        if isinstance(cond, StatGeUnlock):
            col = STAT_COLUMN[cond.stat]
            if int(getattr(character, col, 0) or 0) < int(cond.value):
                return False
        elif isinstance(cond, EnchantAttemptsGeUnlock):
            if int(character.enchant_attempts or 0) < int(cond.value):
                return False
    return True


def unlocked_keys(character: Character) -> set[str]:
    mp = _mp(character)
    raw = mp.get(META_UNLOCKED)
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def refresh_unlocks(character: Character) -> None:
    """Добавить в список все профессии, чьи условия выполнены."""
    mp = _mp(character)
    cur = unlocked_keys(character)
    changed = False
    for prof in PROFESSIONS:
        if prof.key in cur:
            continue
        if meets_unlock(character, prof):
            cur.add(prof.key)
            changed = True
    if changed:
        mp[META_UNLOCKED] = sorted(cur)
        _save_mp(character, mp)


def _migrate_legacy(character: Character) -> None:
    mp = _mp(character)
    if mp.get(META_MIGRATED):
        return
    cur = unlocked_keys(character)
    ck = str(character.class_key or "").strip()
    if ck and ck != "wanderer" and ck in PROFESSION_BY_KEY:
        cur.add(ck)
    if meets_unlock(character, PROFESSION_BY_KEY["smith"]):
        cur.add("smith")
    mp[META_UNLOCKED] = sorted(cur)
    if not mp.get(META_ACTIVE_PRIMARY) and ck in PROFESSION_BY_KEY:
        mp[META_ACTIVE_PRIMARY] = ck
    mp[META_MIGRATED] = True
    _save_mp(character, mp)


def ensure_profession_meta(character: Character) -> None:
    _migrate_legacy(character)
    refresh_unlocks(character)
    mp = _mp(character)
    # Сброс недоступной второй профессии
    if int(character.highest_floor_reached or 0) < SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR:
        if mp.get(META_ACTIVE_SECONDARY):
            mp[META_ACTIVE_SECONDARY] = None
            _save_mp(character, mp)


def active_primary_key(character: Character) -> str | None:
    ensure_profession_meta(character)
    k = _mp(character).get(META_ACTIVE_PRIMARY)
    if not k or not str(k).strip():
        return None
    key = str(k).strip()
    if key not in unlocked_keys(character):
        return None
    return key if key in PROFESSION_BY_KEY else None


def active_secondary_key(character: Character) -> str | None:
    ensure_profession_meta(character)
    if int(character.highest_floor_reached or 0) < SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR:
        return None
    k = _mp(character).get(META_ACTIVE_SECONDARY)
    if not k or not str(k).strip():
        return None
    key = str(k).strip()
    if key not in unlocked_keys(character):
        return None
    return key if key in PROFESSION_BY_KEY else None


def __prof_or_none(key: str | None) -> ProfessionDef | None:
    if not key:
        return None
    return PROFESSION_BY_KEY.get(key)


def combat_skill_class_key(character: Character) -> str:
    """Источник дефолтного тройного набора навыков (школа навыков / миграция слотов)."""
    ensure_profession_meta(character)
    pk = active_primary_key(character)
    prof = __prof_or_none(pk)
    if prof is None:
        return "wanderer"
    return prof.skill_class_key


def primary_skill_class_for_passives(character: Character) -> str:
    """Класс для passive_combat_modifiers основной профессии."""
    ensure_profession_meta(character)
    pk = active_primary_key(character)
    prof = __prof_or_none(pk)
    if prof is None:
        return "wanderer"
    return prof.skill_class_key


def secondary_skill_class_for_passives(character: Character) -> str | None:
    """Второй набор пассивов (только если открыт слот по этажу)."""
    ensure_profession_meta(character)
    sk = active_secondary_key(character)
    prof = __prof_or_none(sk)
    if prof is None:
        return None
    return prof.skill_class_key


def profession_primary_stat_bonuses(character: Character) -> dict[str, int]:
    """Плоские статы только от основной активной профессии."""
    ensure_profession_meta(character)
    pk = active_primary_key(character)
    prof = __prof_or_none(pk)
    if prof is None:
        return empty_stat_bonus_map()
    out = empty_stat_bonus_map()
    for k, v in prof.stat_bonus.items():
        if k in STAT_KEYS:
            out[k] = int(v)
    return out


def enchant_success_bonus_active(character: Character) -> float:
    """Бонус к шансу заточки, если основная профессия — кузнец."""
    ensure_profession_meta(character)
    pk = active_primary_key(character)
    prof = __prof_or_none(pk)
    if prof is None or prof.key != "smith":
        return 0.0
    return float(prof.enchant_success_bonus)


def set_active_primary(character: Character, profession_key: str | None) -> tuple[bool, str]:
    ensure_profession_meta(character)
    mp = _mp(character)
    if not profession_key or not str(profession_key).strip():
        mp[META_ACTIVE_PRIMARY] = None
        _save_mp(character, mp)
        return True, ""
    key = str(profession_key).strip()
    if key not in PROFESSION_BY_KEY:
        return False, "Неизвестная профессия."
    refresh_unlocks(character)
    if key not in unlocked_keys(character):
        return False, "Профессия ещё не открыта."
    mp[META_ACTIVE_PRIMARY] = key
    _save_mp(character, mp)
    return True, ""


def set_active_secondary(character: Character, profession_key: str | None) -> tuple[bool, str]:
    ensure_profession_meta(character)
    mp = _mp(character)
    if int(character.highest_floor_reached or 0) < SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR:
        if profession_key:
            return False, f"Вторая профессия доступна с {SECONDARY_PROFESSION_MIN_HIGHEST_FLOOR} этажа (макс. достигнутый)."
        mp[META_ACTIVE_SECONDARY] = None
        _save_mp(character, mp)
        return True, ""
    if not profession_key or not str(profession_key).strip():
        mp[META_ACTIVE_SECONDARY] = None
        _save_mp(character, mp)
        return True, ""
    key = str(profession_key).strip()
    if key not in PROFESSION_BY_KEY:
        return False, "Неизвестная профессия."
    refresh_unlocks(character)
    if key not in unlocked_keys(character):
        return False, "Профессия ещё не открыта."
    pk = active_primary_key(character)
    if pk == key:
        return False, "Уже выбрана как основная."
    mp[META_ACTIVE_SECONDARY] = key
    _save_mp(character, mp)
    return True, ""


def profession_display_name(key: str, *, locale: str) -> str:
    prof = PROFESSION_BY_KEY.get(key)
    if prof is None:
        return key
    return prof.name_en if locale == "en" else prof.name_ru


def sorted_unlocked_defs(character: Character) -> list[ProfessionDef]:
    refresh_unlocks(character)
    keys = sorted(unlocked_keys(character))
    return [PROFESSION_BY_KEY[k] for k in keys if k in PROFESSION_BY_KEY]
