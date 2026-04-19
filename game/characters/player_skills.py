"""
Навыки боя: покупка в городе (храм / школа), экипировка 3 слотов в статусе.
Урон маг. навыков масштабируется от ИНТ, физ. — от СИЛ с лёгкой подтяжкой ИНТ (см. combat/engine.py).
"""

from __future__ import annotations

from db.models.character import Character
from game.characters.skills import CLASS_SKILLS, SkillDef, skills_for_class
from services import profession_service

META_LEARNED_SKILL_KEYS = "learned_skill_keys"
META_EQUIPPED_SKILL_KEYS = "equipped_skill_keys"

# Цена в золоте за обучение навыку в храме города (этаж 3). Ключ = SkillDef.key из CLASS_SKILLS.
TEMPLE_SKILL_PRICES_GOLD: dict[str, int] = {
    # Магия
    "m1": 420,
    "m2": 720,
    "m3": 980,
    "st1": 650,
    "st2": 820,
    "n1": 580,
    # Физика
    "w1": 380,
    "w3": 520,
    "as1": 560,
    "a1": 400,
    "tr1": 480,
    "h1": 440,
}


def _build_skill_by_key() -> dict[str, SkillDef]:
    out: dict[str, SkillDef] = {}
    for triple in CLASS_SKILLS.values():
        for sk in triple:
            out[sk.key] = sk
    return out


SKILL_BY_KEY: dict[str, SkillDef] = _build_skill_by_key()

# Пустой слот в бою: без урона, чтобы игрок закрепил навык в статусе
_EMPTY_SLOT_SKILL = SkillDef(
    key="_empty",
    name="— Пустой слот —",
    mp_cost=0,
    cooldown=0,
    power=0.0,
    kind="phys",
)


def ensure_skill_meta(character: Character) -> None:
    """Инициализация learned/equipped по классу; миграция старых сохранений."""
    mp = dict(character.meta_progress or {})
    default_triple = skills_for_class(profession_service.combat_skill_class_key(character))
    default_keys = [default_triple[0].key, default_triple[1].key, default_triple[2].key]

    learned = mp.get(META_LEARNED_SKILL_KEYS)
    if not isinstance(learned, list):
        learned = list(default_keys)
    else:
        learned = [str(x).strip() for x in learned if str(x).strip()]
        for k in default_keys:
            if k not in learned:
                learned.append(k)

    eq = mp.get(META_EQUIPPED_SKILL_KEYS)
    if not isinstance(eq, list) or len(eq) != 3:
        eq = list(default_keys)
    else:
        eq = [str(x).strip() if x else "" for x in eq[:3]]
        while len(eq) < 3:
            eq.append("")
        eq = eq[:3]

    mp[META_LEARNED_SKILL_KEYS] = learned
    mp[META_EQUIPPED_SKILL_KEYS] = eq
    character.meta_progress = mp


def learned_skill_keys(character: Character) -> set[str]:
    ensure_skill_meta(character)
    raw = character.meta_progress.get(META_LEARNED_SKILL_KEYS) or []
    return {str(k).strip() for k in raw if str(k).strip()}


def equipped_skill_key_slots(character: Character) -> list[str]:
    ensure_skill_meta(character)
    row = character.meta_progress.get(META_EQUIPPED_SKILL_KEYS) or ["", "", ""]
    out = [str(x).strip() if x else "" for x in row[:3]]
    while len(out) < 3:
        out.append("")
    return out[:3]


def _resolve_skill(key: str) -> SkillDef | None:
    k = (key or "").strip()
    if not k:
        return None
    sk = SKILL_BY_KEY.get(k)
    return sk


def battle_skills_tuple(character: Character) -> tuple[SkillDef, SkillDef, SkillDef]:
    """Три навыка для боя (пустой слот = заглушка без атаки)."""
    ensure_skill_meta(character)
    learned = learned_skill_keys(character)
    slots = equipped_skill_key_slots(character)
    resolved: list[SkillDef] = []
    for slot_key in slots:
        if not slot_key:
            resolved.append(_EMPTY_SLOT_SKILL)
            continue
        if slot_key not in learned:
            resolved.append(_EMPTY_SLOT_SKILL)
            continue
        sk = _resolve_skill(slot_key)
        resolved.append(sk if sk is not None else _EMPTY_SLOT_SKILL)
    return (resolved[0], resolved[1], resolved[2])


def set_equipped_slot(character: Character, slot_index: int, skill_key: str | None) -> bool:
    """Назначить навык в слот 0..2. skill_key должен быть в learned (или None/\"\" очистить)."""
    if slot_index < 0 or slot_index > 2:
        return False
    ensure_skill_meta(character)
    learned = learned_skill_keys(character)
    mp = dict(character.meta_progress or {})
    eq = equipped_skill_key_slots(character)
    if not skill_key or not str(skill_key).strip():
        eq[slot_index] = ""
    else:
        k = str(skill_key).strip()
        if k not in learned:
            return False
        if k not in SKILL_BY_KEY:
            return False
        eq[slot_index] = k
    mp[META_EQUIPPED_SKILL_KEYS] = eq
    character.meta_progress = mp
    return True


def try_buy_temple_skill(character: Character, skill_key: str) -> tuple[bool, str]:
    """
    Покупка навыка за золото на этаже города (проверка этажа — в хендлере).
    Возвращает (успех, сообщение игроку).
    """
    k = (skill_key or "").strip()
    price = TEMPLE_SKILL_PRICES_GOLD.get(k)
    if price is None:
        return False, "Этот навык нельзя выучить здесь."
    sk = SKILL_BY_KEY.get(k)
    if sk is None:
        return False, "Неизвестный навык."
    ensure_skill_meta(character)
    learned = learned_skill_keys(character)
    if k in learned:
        return False, "Уже выучено."
    if int(character.gold) < price:
        return False, f"Нужно {price} золота."
    character.gold = int(character.gold) - price
    mp = dict(character.meta_progress or {})
    lst = list(mp.get(META_LEARNED_SKILL_KEYS) or [])
    if k not in lst:
        lst.append(k)
    mp[META_LEARNED_SKILL_KEYS] = lst
    character.meta_progress = mp
    return True, f"Вы освоили: {sk.name}"


def skill_shop_summary_html(locale: str) -> str:
    """Кратко: тип навыка и шкала урона для экрана магазина."""
    if locale == "en":
        return (
            "<i>Magic skills scale mainly with <b>INT</b>; physical skills mainly with "
            "<b>STR</b> (INT slightly tunes technique).</i>"
        )
    return (
        "<i>Магические навыки в основном от <b>ИНТ</b>; физические — от <b>СИЛ</b> "
        "(ИНТ слегка улучшает технику удара).</i>"
    )


def shop_offer_skill_defs() -> list[SkillDef]:
    """Уникальные предложения для витрины (порядок стабильный)."""
    seen: set[str] = set()
    out: list[SkillDef] = []
    for k in sorted(TEMPLE_SKILL_PRICES_GOLD.keys()):
        sk = SKILL_BY_KEY.get(k)
        if sk is None or k in seen:
            continue
        seen.add(k)
        out.append(sk)
    return out


def describe_skill_for_ui(sk: SkillDef, locale: str) -> str:
    kind_ru = "магия" if sk.kind == "mag" else "физ."
    kind_en = "magic" if sk.kind == "mag" else "phys."
    if locale == "en":
        return f"{kind_en} · MP {sk.mp_cost} · CD {sk.cooldown} · ×{sk.power:.2f}"
    return f"{kind_ru} · MP {sk.mp_cost} · перезарядка {sk.cooldown} х. · сила ×{sk.power:.2f}"
