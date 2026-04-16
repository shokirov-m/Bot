"""
Питомцы: призыв за золото (лавка городского хаба; редкий пул после открытия 48 этажа).
Бонусы суммируются через passive_combat_modifiers_merged (как глобальные пассивы).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from db.models.character import Character
META_KEY = "pets_v1"

# Стоимость и шансы (золото). Призыв с этажа отключён — только город (см. try_city_pet_summon).
GACHA_FLOOR_BASIC = 8
GACHA_FLOOR_RARE = 48
GACHA_COST_BASIC = 100
GACHA_COST_RARE = 350
# Три призыва подряд: дороже трёх отдельных базовых (3×100), чтобы не было выгодного абуза.
CITY_SUMMON_COST_X3_BASIC = 340
# После открытия 48 этажа — редкий пул; ×3 тоже с наценкой к сумме трёх одиночных.
CITY_SUMMON_COST_X3_RARE = 1225
DUPLICATE_REFUND_RATIO = 0.25  # доля от стоимости броска при дубликате

# Оставлено для смены активного питомца на этажах с «алтарём» (8 и 48).
_PET_GACHA_FLOORS: dict[int, tuple[int, bool]] = {
    GACHA_FLOOR_BASIC: (GACHA_COST_BASIC, False),
    GACHA_FLOOR_RARE: (GACHA_COST_RARE, True),
}


def is_pet_gacha_floor(floor_number: int) -> bool:
    return int(floor_number) in _PET_GACHA_FLOORS


def pet_gacha_floors_for_pet_switch() -> frozenset[int]:
    return frozenset(_PET_GACHA_FLOORS.keys())


@dataclass(frozen=True, slots=True)
class PetDef:
    key: str
    name_ru: str
    emoji: str
    blurb: str
    passive: dict[str, float | int]


# Обычный пул (этаж 8)
PET_BASIC_POOL: tuple[PetDef, ...] = (
    PetDef(
        "pet_moss_sprite",
        "Моховой спрайт",
        "🌱",
        "+1 к защите в бою.",
        {"def_bonus": 1.0},
    ),
    PetDef(
        "pet_cinder_fox",
        "Угольный лис",
        "🦊",
        "+2% к шансу крита.",
        {"crit_bonus": 0.02},
    ),
    PetDef(
        "pet_drip_slime",
        "Капельный слизень",
        "💧",
        "+1 MP реген / ход (бой).",
        {"mp_regen_turn": 1},
    ),
    PetDef(
        "pet_iron_beetle",
        "Железный жук",
        "🪲",
        "+3% к магическим навыкам.",
        {"mag_bonus_percent": 3},
    ),
    PetDef(
        "pet_gloom_moth",
        "Мрачная моль",
        "🦋",
        "+2% к уклонению.",
        {"dodge_bonus": 0.02},
    ),
)

# Два редких — в пуле после открытия 48 этажа (добавляются к базовому пулу при броске)
PET_RARE_EXCLUSIVE: tuple[PetDef, ...] = (
    PetDef(
        "pet_void_wisp",
        "Осколок пустоты",
        "🌑",
        "+4% крит, +2 защита.",
        {"crit_bonus": 0.04, "def_bonus": 2.0},
    ),
    PetDef(
        "pet_sun_cub",
        "Солнечный зверёк",
        "☀️",
        "+6% магия, +1 MP/ход.",
        {"mag_bonus_percent": 6, "mp_regen_turn": 1},
    ),
)


def _all_defs() -> dict[str, PetDef]:
    out: dict[str, PetDef] = {}
    for p in PET_BASIC_POOL + PET_RARE_EXCLUSIVE:
        out[p.key] = p
    return out


def _pets_meta(character: Character) -> dict[str, Any]:
    mp = dict(character.meta_progress or {})
    raw = mp.get(META_KEY)
    if not isinstance(raw, dict):
        raw = {}
    return mp, raw


def owned_keys(character: Character) -> list[str]:
    _, st = _pets_meta(character)
    raw = st.get("owned")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def active_pet_key(character: Character) -> str | None:
    _, st = _pets_meta(character)
    a = st.get("active")
    return str(a) if a else None


def active_pet_display(character: Character) -> str | None:
    key = active_pet_key(character)
    if not key:
        return None
    d = _all_defs().get(key)
    if d is None:
        return None
    return f"{d.emoji} {d.name_ru}"


def pet_passive_delta(character: Character) -> dict[str, float | int]:
    key = active_pet_key(character)
    if not key:
        return {}
    d = _all_defs().get(key)
    if d is None:
        return {}
    return dict(d.passive)


def _save_meta(character: Character, mp: dict[str, Any], st: dict[str, Any]) -> None:
    mp[META_KEY] = st
    character.meta_progress = mp


def set_active_pet(character: Character, key: str) -> tuple[bool, str]:
    if key not in _all_defs():
        return False, "Неизвестный питомец."
    owned = set(owned_keys(character))
    if key not in owned:
        return False, "Сначала получи питомца в призыве (город)."
    mp, st = _pets_meta(character)
    st["active"] = key
    _save_meta(character, mp, st)
    return True, _all_defs()[key].name_ru


def cycle_active_pet(character: Character) -> str | None:
    """Следующий из открытых (кольцо). Возвращает display или None."""
    own = owned_keys(character)
    if not own:
        return None
    mp, st = _pets_meta(character)
    cur = active_pet_key(character)
    if cur is None or cur not in own:
        st["active"] = own[0]
        _save_meta(character, mp, st)
        return active_pet_display(character)
    i = own.index(cur)
    nxt = own[(i + 1) % len(own)]
    st["active"] = nxt
    _save_meta(character, mp, st)
    return active_pet_display(character)


def _roll_pet_choice(*, rare_exclusive: bool) -> PetDef:
    pool = list(PET_BASIC_POOL)
    weights = [1.0] * len(pool)
    if rare_exclusive:
        pool.extend(PET_RARE_EXCLUSIVE)
        weights.extend([0.35, 0.35])
    total_w = sum(weights)
    r = random.uniform(0, total_w)
    acc = 0.0
    chosen: PetDef | None = None
    for p, w in zip(pool, weights):
        acc += w
        if r <= acc:
            chosen = p
            break
    return chosen if chosen is not None else pool[-1]


def _apply_pet_pull_after_payment(
    character: Character,
    chosen: PetDef,
    *,
    cost_for_refund: int,
) -> str:
    mp, st = _pets_meta(character)
    owned = list(st.get("owned") or [])
    if not isinstance(owned, list):
        owned = []
    owned_set = {str(x) for x in owned}

    if chosen.key in owned_set:
        refund = max(1, int(cost_for_refund * DUPLICATE_REFUND_RATIO))
        character.gold = int(character.gold) + refund
        return (
            f"Повтор: <b>{chosen.emoji} {chosen.name_ru}</b> уже с тобой. "
            f"Возврат <b>{refund}</b> золота."
        )

    owned.append(chosen.key)
    st["owned"] = owned
    if not st.get("active"):
        st["active"] = chosen.key
    _save_meta(character, mp, st)
    return f"Новый питомец: <b>{chosen.emoji} {chosen.name_ru}</b>\n<i>{chosen.blurb}</i>"


def city_summon_price_band(character: Character) -> tuple[int, int, bool]:
    """
    (цена ×1, цена ×3, редкий_пул).
    Редкий пул — если когда-либо открыт 48-й этаж (highest_floor_reached).
    """
    hi = int(character.highest_floor_reached)
    if hi >= GACHA_FLOOR_RARE:
        return GACHA_COST_RARE, CITY_SUMMON_COST_X3_RARE, True
    return GACHA_COST_BASIC, CITY_SUMMON_COST_X3_BASIC, False


def try_city_pet_summon(character: Character, *, pulls: int) -> tuple[bool, str]:
    """Призыв из городского хаба: 1 или 3 броска одной оплатой."""
    if pulls not in (1, 3):
        return False, "Неверный запрос."
    c1, c3, rare = city_summon_price_band(character)
    total = c1 if pulls == 1 else c3
    if int(character.gold) < total:
        return False, f"Нужно {total} золота."
    character.gold = int(character.gold) - total
    per_refund = max(1, total // pulls)
    parts = [_apply_pet_pull_after_payment(character, _roll_pet_choice(rare_exclusive=rare), cost_for_refund=per_refund) for _ in range(pulls)]
    return True, "\n\n".join(parts)


def try_gacha_pull(character: Character, *, floor_number: int) -> tuple[bool, str]:
    """
    Совместимость: призыв с этажа (если остались старые кнопки) — перенаправляет логику на этажные цены.
    """
    spec = _PET_GACHA_FLOORS.get(int(floor_number))
    if spec is None:
        return False, "Призыв питомцев — в городе (лавка хаба)."
    cost, rare_exclusive = spec
    if int(character.gold) < cost:
        return False, f"Нужно {cost} золота."
    chosen = _roll_pet_choice(rare_exclusive=rare_exclusive)
    character.gold = int(character.gold) - cost
    return True, _apply_pet_pull_after_payment(character, chosen, cost_for_refund=cost)
