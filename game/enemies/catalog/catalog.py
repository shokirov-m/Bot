"""
Каталог монстров: карточки из `content/data/monsters_catalog.json` (см. `game/data/monsters.py`).

Бой: hp/atk/def с масштабом по этажу; точность/уклонение и реплики — поля JSON
(accuracy, evasion, opening_phrase, victory_phrase, defeat_phrase и ролевые варианты).
"""

from __future__ import annotations

import copy
from typing import Any, Literal

from game.balance import MONSTER_ACCURACY_CAP, MONSTER_EVASION_CAP
from game.enemies.catalog.registry import get_all_definitions
from game.enemies.floors.spawns import FloorMonsterSpawn

_ELITE_PREFIX = "elite_"

DialogKind = Literal["opening", "victory", "defeat"]

_DIALOG_SUFFIX: dict[DialogKind, str] = {
    "opening": "opening_phrase",
    "victory": "victory_phrase",
    "defeat": "defeat_phrase",
}


def _base_template_key(template_key: str) -> str:
    k = (template_key or "").strip()
    if k.startswith(_ELITE_PREFIX):
        return k[len(_ELITE_PREFIX) :]
    return k


def get_definition(template_key: str) -> dict[str, Any] | None:
    """Карточка монстра по ключу шаблона (elite_* → базовый id)."""
    bid = _base_template_key(template_key)
    row = get_all_definitions().get(bid)
    if row is None:
        return None
    return copy.deepcopy(row)


def has_explicit_stats(defn: dict[str, Any]) -> bool:
    return (
        defn.get("hp") is not None
        and defn.get("atk") is not None
        and defn.get("def") is not None
    )


def floor_ratio(defn: dict[str, Any], floor_number: int) -> float:
    ref = defn.get("reference_floor")
    if ref is None:
        ref = defn.get("level")
    r = max(1, int(ref or floor_number))
    ratio = float(floor_number) / float(r)
    return max(0.2, min(5.0, ratio))


def scaled_gold_exp(
    defn: dict[str, Any],
    floor_number: int,
) -> tuple[int | None, int | None]:
    """Переопределение золота и опыта; None — нет поля в карточке."""
    ratio = floor_ratio(defn, floor_number)
    g_raw = defn.get("gold")
    x_raw = defn.get("exp")
    gold: int | None = None
    xp: int | None = None
    if g_raw is not None:
        gold = max(1, int(round(float(g_raw) * ratio)))
    if x_raw is not None:
        xp = max(1, int(round(float(x_raw) * ratio)))
    return gold, xp


def catalog_dialog_line(
    cat: dict[str, Any],
    spawn: FloorMonsterSpawn,
    *,
    kind: DialogKind,
) -> str:
    """
    Реплика из monsters_catalog.json: роль (major/mini/elite) → общий ключ.
    """
    suf = _DIALOG_SUFFIX[kind]
    for cond, key in (
        (spawn.is_major_boss, f"major_boss_{suf}"),
        (spawn.is_mini_boss, f"mini_boss_{suf}"),
        (spawn.is_elite, f"elite_{suf}"),
    ):
        if not cond:
            continue
        raw = cat.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    raw = cat.get(suf)
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    return ""


def catalog_accuracy_evasion(
    cat: dict[str, Any],
    spawn: FloorMonsterSpawn,
    default_accuracy: float,
    default_evasion: float,
) -> tuple[float, float]:
    """
    Точность/уклонение (0..1): поля роли в JSON → accuracy/evasion → дефолт формулы этажа.
    """
    acc, ev = float(default_accuracy), float(default_evasion)
    got_acc = got_ev = False
    for cond, ak, ek in (
        (spawn.is_major_boss, "major_boss_accuracy", "major_boss_evasion"),
        (spawn.is_mini_boss, "mini_boss_accuracy", "mini_boss_evasion"),
        (spawn.is_elite, "elite_accuracy", "elite_evasion"),
    ):
        if not cond:
            continue
        if not got_acc and cat.get(ak) is not None:
            try:
                acc = float(cat[ak])
                got_acc = True
            except (TypeError, ValueError):
                pass
        if not got_ev and cat.get(ek) is not None:
            try:
                ev = float(cat[ek])
                got_ev = True
            except (TypeError, ValueError):
                pass
    if not got_acc and cat.get("accuracy") is not None:
        try:
            acc = float(cat["accuracy"])
        except (TypeError, ValueError):
            pass
    if not got_ev and cat.get("evasion") is not None:
        try:
            ev = float(cat["evasion"])
        except (TypeError, ValueError):
            pass
    acc = min(float(MONSTER_ACCURACY_CAP), max(0.0, acc))
    ev = min(float(MONSTER_EVASION_CAP), max(0.0, ev))
    return acc, ev


def catalog_phrase_list(cat: dict[str, Any]) -> list[str]:
    raw = cat.get("phrases")
    if not isinstance(raw, list):
        return []
    return [str(p).strip() for p in raw if p and str(p).strip()]


def apply_combat_overlay(
    bundle: dict[str, Any],
    spawn: FloorMonsterSpawn,
    floor_number: int,
    cat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Подмешать из JSON точность, уклонение и реплики (для любого пути сборки bundle).
    """
    if cat is None:
        cat = get_definition(str(spawn.template.key or ""))
    if not cat:
        return bundle

    from game.enemies.scaling import monster_accuracy_evasion_for_spawn

    a0, e0 = monster_accuracy_evasion_for_spawn(int(floor_number), spawn)
    acc, ev = catalog_accuracy_evasion(cat, spawn, a0, e0)
    bundle["accuracy"] = acc
    bundle["evasion"] = ev

    op = catalog_dialog_line(cat, spawn, kind="opening")
    if op:
        bundle["catalog_opening_phrase"] = op
    vq = catalog_dialog_line(cat, spawn, kind="victory")
    if vq:
        bundle["catalog_victory_phrase"] = vq
    dq = catalog_dialog_line(cat, spawn, kind="defeat")
    if dq:
        bundle["catalog_defeat_phrase"] = dq

    plist = catalog_phrase_list(cat)
    if plist:
        bundle["catalog_phrases"] = plist
    return bundle
