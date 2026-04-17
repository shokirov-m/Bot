"""Сгенерировать КАТАЛОГ_ЭКИПИРОВКИ_ПОЛНЫЙ.txt из catalog_generated."""

from __future__ import annotations

from pathlib import Path

from game.items.enchant import MAX_ENCHANT
from game.items.equipment import EQUIP_ORDER, SLOT_LABEL_RU, resolve_equip_slot_for_item_data
from game.characters.classes import all_classes_ordered, get_class_or_none
from game.items.equipment.catalog_generated import all_example_groups
from game.items.equipment.starters import starter_weapon_payload
from game.items.runes import max_rune_slots
from game.items.stat_bonuses import STAT_KEYS as BONUS_STAT_KEYS

RARITY_RU = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
}
STAT_KEYS = ("attack", "defense", "hp_bonus", "str", "dex", "int", "vit", "luck", "enchant")
EXTRA = ("hand", "two_handed", "weapon_type", "ring_slot", "set_key", "set_piece")


def stat_lines(d: dict) -> str:
    parts: list[str] = []
    for k in STAT_KEYS:
        if k in d and d[k] is not None:
            parts.append(f"{k}={d[k]}")
    for k in EXTRA:
        if k in d and d[k] is not None and d[k] != "":
            parts.append(f"{k}={d[k]}")
    return ", ".join(parts) if parts else "—"


def main() -> None:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("  КАТАЛОГ ЭКИПИРОВКИ И ОРУЖИЯ (tower_bot) — данные из catalog/*.py")
    lines.append("  Слоты и правила: game/items/equipment/slots.py")
    lines.append("=" * 78)
    lines.append("")
    lines.append("ПОРЯДОК СЛОТОВ (EQUIP_ORDER)")
    for s in EQUIP_ORDER:
        lines.append(f"  • {s}: {SLOT_LABEL_RU.get(s, s)}")
    lines.append("")
    lines.append("ТИПЫ ОРУЖИЯ (weapon_type)")
    lines.append("  blade, staff, bow, dagger, axe, polearm, hammer")
    lines.append("")
    lines.append("РЕДКОСТИ")
    for k, v in RARITY_RU.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"ЗАТОЧКА: поле enchant (или plus), максимум +{MAX_ENCHANT} — game/items/enchant.py")
    lines.append("")
    lines.append("ГНЁЗДА ПОД РУНЫ В ОРУЖИИ (по редкости оружия)")
    for r in ("common", "uncommon", "rare", "epic", "legendary"):
        lines.append(f"  {r}: {max_rune_slots(r)}")
    lines.append("")
    lines.append(
        "КОЛЬЦА: ring_slot в item_data — значения 2, right, ring2, второе → слот ring2; "
        "1, left, ring1, первое → ring; иначе при надевании слот выбирает инвентарь.",
    )
    lines.append("")
    lines.append(
        "ВТОРАЯ РУКА: weapon с hand=off / shield / grimoire / tome / orb / focus → equip_slot offhand.",
    )
    lines.append("")
    lines.append(
        "ПРИМЕЧАНИЕ: в catalog/ нет отдельных файлов boots и cloak — виды kind=boots и kind=cloak "
        "используются в loot.py, starters.py, secret_gear.py.",
    )
    lines.append("")

    titles = {
        "weapon_main": "ОРУЖИЕ — ОСНОВНАЯ РУКА (weapon, обычно hand=main)",
        "weapon_off": "ОРУЖИЕ — ВТОРАЯ РУКА (weapon, hand=off)",
        "two_handed": "ОРУЖИЕ — ДВУРУЧНОЕ (two_handed=True)",
        "armor": "НАГРУДНИК (armor)",
        "pants": "ПОНОЖИ (pants)",
        "helmet": "ШЛЕМ (helmet)",
        "gloves": "ПЕРЧАТКИ (gloves)",
        "ring": "КОЛЬЦА (ring)",
        "amulet": "АМУЛЕТЫ (amulet)",
        "shield": "ЩИТЫ (shield → offhand)",
        "grimoire": "ГРИМУАРЫ (grimoire → offhand)",
    }

    groups = all_example_groups()
    for key in (
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
    ):
        items = groups.get(key) or []
        lines.append("-" * 78)
        lines.append(titles.get(key, key.upper()))
        lines.append("-" * 78)
        for i, d in enumerate(items, 1):
            slot = resolve_equip_slot_for_item_data(d) or "?"
            rr = RARITY_RU.get(str(d.get("rarity", "")), str(d.get("rarity")))
            lines.append(f"{i}. {d.get('name')}")
            lines.append(f"   Слот: {slot}  |  Редкость: {rr}  |  kind: {d.get('kind')}")
            lines.append(f"   Статы и поля: {stat_lines(d)}")
            summ = str(d.get("summary") or "").replace("\n", " ")
            lines.append(f"   Описание: {summ}")
            iu = d.get("image_url", "")
            if isinstance(iu, str) and iu:
                iu = Path(iu).name
            else:
                iu = "—"
            lines.append(f"   файл: assets/items/{iu}")
            lines.append("")
        lines.append("")

    lines.append("-" * 78)
    lines.append("СТАРТОВОЕ ОРУЖИЕ ПО КЛАССУ (starters.starter_weapon_payload)")
    lines.append("-" * 78)
    extra_first = ("wanderer", "star_touched", "tower_reaper")
    seen: set[str] = set()
    for key in (*extra_first, *(c.key for c in all_classes_ordered())):
        if key in seen:
            continue
        seen.add(key)
        cls = get_class_or_none(key)
        label = f"{cls.emoji} {cls.name_ru}" if cls else key
        p = starter_weapon_payload(key)
        th = "да" if p.get("two_handed") else "нет"
        lines.append(
            f"  • {label} ({key}): «{p.get('name')}» — "
            f"ATK {p.get('attack')}, тип {p.get('weapon_type')}, двуручн. {th}",
        )
    lines.append("")

    lines.append("-" * 78)
    lines.append("БОНУСЫ К СТАТАМ НА ПРЕДМЕТЕ (game/items/stat_bonuses.py)")
    lines.append("-" * 78)
    lines.append(
        "  Плоские поля в item_data: "
        + ", ".join(BONUS_STAT_KEYS)
        + "; также strength/dexterity/… (алиасы); вложенный dict stat_bonus.",
    )
    lines.append(
        "  Заточка (enchant) даёт бонус к уже ненулевым статам на броне/украшениях; "
        "на чистом defense-кольце — бонус к ВЫН.",
    )
    lines.append("")

    root = Path(__file__).resolve().parents[1]
    out = root / "КАТАЛОГ_ЭКИПИРОВКИ_ПОЛНЫЙ.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
