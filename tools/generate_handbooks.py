# -*- coding: utf-8 -*-
"""Генерация TXT: полный каталог предметов из кода + (опционально) заготовка прочих систем.

Запуск из папки tower_bot:
  python tools/generate_handbooks.py
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.items.equipment.catalog_generated import all_example_groups
from game.items.equipment.constants import RARITY_EMOJI, RARITY_NAME_RU
from game.items.equipment.secret_gear import SECRET_GEAR_ITEMS
from game.items.equipment.starters import (
    promo_starter_armor_amulet_payloads,
    referral_inviter_epic_necklace_payload,
    referral_inviter_gear_payloads,
    starter_boots_payload,
    starter_bread_payload,
    starter_cloak_payload,
    starter_offhand_dagger_payload,
    starter_pants_payload,
    starter_weapon_payload,
)
from game.items.runes import ELEMENTS, RUNE_RANK_STATS, SYNERGIES

ORDER_KEYS = (
    "hand",
    "weapon_type",
    "two_handed",
    "attack",
    "defense",
    "str",
    "dex",
    "int",
    "vit",
    "luck",
    "hp_bonus",
    "mp_bonus",
    "enchant",
    "ring_slot",
    "block_chance",
    "use_tag",
    "use_value",
    "set_key",
    "set_piece",
)


def _rarity_ru(code: str) -> str:
    return str(RARITY_NAME_RU.get(code, code))


def _fmt_stats(d: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ORDER_KEYS:
        if k not in d:
            continue
        v = d[k]
        if k == "two_handed":
            if v:
                parts.append("двуручное")
            continue
        if v in (None, "", False):
            continue
        if v == 0 and k not in ("enchant", "ring_slot"):
            continue
        labels = {
            "hand": "рука",
            "weapon_type": "тип оружия",
            "attack": "атака",
            "defense": "защита",
            "str": "STR",
            "dex": "DEX",
            "int": "INT",
            "vit": "VIT",
            "luck": "удача",
            "hp_bonus": "+HP",
            "mp_bonus": "+MP",
            "enchant": "заточка",
            "ring_slot": "слот кольца",
            "block_chance": "блок %",
            "use_tag": "использование",
            "use_value": "значение",
            "set_key": "набор",
            "set_piece": "часть набора",
        }
        lab = labels.get(k, k)
        parts.append(f"{lab}={v}")
    return " | ".join(parts) if parts else "—"


def _item_block(title: str, d: dict[str, Any]) -> list[str]:
    name = str(d.get("name", "?"))
    kind = str(d.get("kind", "?"))
    rare = str(d.get("rarity", "?"))
    emoji = RARITY_EMOJI.get(rare, "")
    head = f"• {emoji} [{kind}] {name} — {_rarity_ru(rare)}"
    st = _fmt_stats(d)
    lines = [head, f"  Параметры: {st}"]
    summ = d.get("summary")
    if summ:
        lines.append(f"  Описание: {summ}")
    lines.append("")
    return lines


def build_items_document() -> str:
    lines: list[str] = [
        "=" * 80,
        "ПРЕДМЕТЫ: КАТАЛОГ ИЗ КОДА (tower_bot/game/items)",
        "Секции: примеры экипировки по слотам, тайник (ранний пул), старт/промо/реферал, руны.",
        "Картинки в игре — заглушки/ассеты; в справочнике не дублируем URL.",
        "=" * 80,
        "",
    ]

    groups = all_example_groups()
    group_order = (
        "weapon_main",
        "weapon_off",
        "two_handed",
        "armor",
        "pants",
        "helmet",
        "gloves",
        "ring",
        "amulet",
        "shield",
        "grimoire",
    )
    titles = {
        "weapon_main": "ОРУЖИЕ (основная рука) — примеры каталога",
        "weapon_off": "ОРУЖИЕ (вторая рука)",
        "two_handed": "ДВУРУЧНОЕ ОРУЖИЕ",
        "armor": "НАГРУДНИК (броня)",
        "pants": "ПОНОЖИ",
        "helmet": "ШЛЕМ",
        "gloves": "ПЕРЧАТКИ",
        "ring": "КОЛЬЦА",
        "amulet": "АМУЛЕТЫ",
        "shield": "ЩИТЫ",
        "grimoire": "ГРИМУАРЫ (оффхенд мага)",
    }

    for key in group_order:
        items = groups.get(key) or []
        lines.append("-" * 80)
        lines.append(titles.get(key, key.upper()))
        lines.append(f"(записей: {len(items)})")
        lines.append("-" * 80)
        for it in items:
            lines.extend(_item_block(key, deepcopy(it)))

    lines.append("=" * 80)
    lines.append("ТАЙНИК: РАННИЙ ПУЛ (этажи ≤ SECRET_GEAR_EARLY_MAX_FLOOR, см. balance)")
    lines.append("Веса — относительная частота; предмет выбирается случайно.")
    lines.append("=" * 80)
    total_w = sum(w for w, _ in SECRET_GEAR_ITEMS)
    for w, data in SECRET_GEAR_ITEMS:
        pct = 100.0 * w / total_w if total_w else 0.0
        dd = deepcopy(data)
        lines.append(f"[вес {w:.2f} ≈ {pct:.1f}% от суммы весов]")
        lines.extend(_item_block("secret", dd))

    lines.append("=" * 80)
    lines.append("СТАРТ И ПРОМО (выдаётся при регистрации / акциях)")
    lines.append("=" * 80)
    lines.extend(_item_block("starter", starter_bread_payload()))
    lines.extend(_item_block("starter", starter_pants_payload()))
    lines.extend(_item_block("starter", starter_boots_payload()))
    lines.extend(_item_block("starter", starter_cloak_payload()))
    lines.extend(_item_block("starter", starter_offhand_dagger_payload()))
    starter_weapon_keys = (
        "wanderer",
        "star_touched",
        "tower_reaper",
        "warrior",
        "mage",
        "archer",
        "priest",
        "assassin",
        "berserker",
        "necromancer",
        "warden",
        "shaman",
        "hunter",
    )
    for wk in starter_weapon_keys:
        lines.extend(_item_block(f"стартер оружие ({wk})", starter_weapon_payload(wk)))
    a, b = promo_starter_armor_amulet_payloads()
    lines.extend(_item_block("promo", a))
    lines.extend(_item_block("promo", b))
    g1, g2 = referral_inviter_gear_payloads()
    lines.extend(_item_block("referral", g1))
    lines.extend(_item_block("referral", g2))
    lines.extend(_item_block("referral", referral_inviter_epic_necklace_payload()))

    lines.append("=" * 80)
    lines.append("РУНЫ (вставляются в оружие; см. game/items/runes.py)")
    lines.append("=" * 80)
    lines.append("Стихии и статусы в бою:")
    for el, meta in ELEMENTS.items():
        lines.append(f"  {meta.get('emoji','')} {el}: «{meta.get('name','')}» → эффект статуса: {meta.get('status_effect','')}")
    lines.append("")
    lines.append("Ранг руны: бонус % к урону по стихии, шанс статуса, вес дропа, плоский элемент. урон:")
    for rank, st in sorted(RUNE_RANK_STATS.items()):
        lines.append(
            f"  {rank}: +{st['damage_bonus_percent']}% урон, шанс статуса {int(float(st['status_chance'])*100)}%, "
            f"вес дропа {st['drop_weight']}, +{st.get('flat_elemental', 0)} плоского элем. урона",
        )
    lines.append("")
    lines.append("Синергии (две разные стихии на оружии):")
    for elems, syn in SYNERGIES.items():
        els = ", ".join(sorted(elems))
        lines.append(f"  [{els}] {syn.get('name')}: {syn.get('description')}")
    lines.append("")
    lines.append("Мастерство: две и больше рун одной стихии — см. MASTERY_SAME_ELEMENT_BONUS в runes.py.")
    lines.append("")
    lines.append(
        "Слоты под руны по редкости оружия (max_rune_slots): common 0, uncommon 1, rare 1, epic 2, legendary 3.",
    )
    lines.append("")

    lines.append("=" * 80)
    lines.append("ДРОП ПОСЛЕ БОЯ (game/items/loot.py) — не фиксированный список имён")
    lines.append("=" * 80)
    lines.append(
        "Обычная цель: настой HP, капля маны, слабый эликсир %, перчатки/кольцо с числом этажа в имени, "
        "трофей, оружие «Клинок N» / «Сук N», на этажах ≤12 дополнительно накидка, капюшон, оберег, сапоги, "
        "роса, пары кинжалов, двуручник, меч/щит равновесия, посох, палочка, гримуар — с весами в коде.",
    )
    lines.append(
        "Элита: оружие «Элита N», накидка, шлем, флакон, эфирный отвар — редкость/статы от этажа (loot_scaling).",
    )
    lines.append(
        "Мини-босс: «Клык N», латы, шлем/рукавицы/сапоги претендента, запас — редкость выше.",
    )
    lines.append(
        "Сильный босс: «Корона N» (оружие), «Страж N» (броня), печать этажа, кольцо «Победа N», "
        "сапоги триумфа, сосуд триумфа.",
    )
    lines.append("")
    lines.append("Тайник на этажах после ранних: процедурная «броня/поножи/… редкости X — ярус N» (secret_gear._scaled_secret_gear).")
    lines.append("")
    lines.append("=" * 80)
    lines.append("Конец файла. Обновление: python tools/generate_handbooks.py")
    lines.append("=" * 80)
    return "\n".join(lines)


def main() -> None:
    out_items = WORKSPACE / "ПРЕДМЕТЫ_ПОЛНЫЙ_СПРАВОЧНИК.txt"
    out_items.write_text(build_items_document(), encoding="utf-8")
    print(f"Wrote {out_items}")


if __name__ == "__main__":
    main()
