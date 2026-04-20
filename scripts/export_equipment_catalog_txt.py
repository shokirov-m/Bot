"""
Экспорт справки по всем предметам: каталог (data/items), лут победы, тайник, лавка, старт.

Запуск из каталога tower_bot:
  python -m scripts.export_equipment_catalog_txt

Выход: catalog_txt_edit/*.txt
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game.balance import (
    DROP_CHANCE_ELITE_HIGH,
    DROP_CHANCE_ELITE_LOW,
    DROP_CHANCE_FLOOR_LOW_MAX,
    DROP_CHANCE_MAJOR_HIGH,
    DROP_CHANCE_MAJOR_LOW,
    DROP_CHANCE_MINI_HIGH,
    DROP_CHANCE_MINI_LOW,
    DROP_CHANCE_NORMAL_HIGH,
    DROP_CHANCE_NORMAL_LOW,
    RUNE_CHANCE_ELITE,
    RUNE_CHANCE_MAJOR,
    RUNE_CHANCE_MINI,
    RUNE_CHANCE_NORMAL,
)
from game.data.items.amulets import amulet_examples
from game.data.items.armor import armor_examples, gloves_examples, helmet_examples, pants_examples
from game.data.items.offhand import grimoire_examples, shield_examples
from game.data.items.rings import ring_examples
from game.data.items.weapons import (
    two_handed_weapon_examples,
    weapon_main_examples,
    weapon_offhand_examples,
)
from game.economy.shop import SHOP_GOODS, SHOP_FLOOR3_GEAR, SHOP_PORTRAITS
from game.floors.floor_data import SECRET_ROOM_CHANCE
from game.items.equipment.constants import (
    RARITY_NAME_RU,
    SECRET_GEAR_DROP_CHANCE,
    SECRET_GEAR_EARLY_MAX_FLOOR,
    SECRET_GEAR_MAX_FLOOR,
)
from game.items.equipment.secret_gear import SECRET_GEAR_ITEMS
from game.items import loot_scaling as ls
from game.items.equipment.starters import (
    promo_starter_armor_amulet_payloads,
    referral_inviter_epic_necklace_payload,
    referral_inviter_gear_payloads,
    starter_bread_payload,
    starter_offhand_dagger_payload,
    starter_pants_payload,
    starter_weapon_payload,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "catalog_txt_edit"

RARITY_RU: dict[str, str] = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
}

STAT_ORDER = (
    ("attack", "Атака"),
    ("defense", "Защита"),
    ("str", "Сила"),
    ("dex", "Ловкость"),
    ("int", "Интеллект"),
    ("vit", "Живучесть"),
    ("luck", "Удача"),
    ("hp_bonus", "Бонус HP"),
    ("mp_bonus", "Бонус MP"),
    ("enchant", "Заточка"),
)

RING_CATALOG_INTRO = """
КАТАЛОГ НИЖЕ — справочные карточки из game/data/items/rings.py.
Диапазоны этажей (дроп с монстров/сундуков) указаны согласно обновлённой схеме.

СХЕМА ДРОПА ПО ЭТАЖАМ:
  • Обычный        1–20
  • Необычный      11–30
  • Редкий         21–50
  • Эпический      41–80
  • Легендарный    70–90
  • Мифический     90+

Кольца можно надеть в оба слота без разделения колец для слота 1–2.
""".strip()

RING_CATALOG_FOOTER = """
────────────────────────────────────────
КАК ПОЛУЧИТЬ В ИГРЕ
Именованные записи (например Обручальное Кольцо Башни) подключаются лавкой, квестами, NPC.
Случайный лут после боя и тайник этажа используют указанные диапазоны этажей.
""".strip()

CATALOG_INTRO = (
    "КАТАЛОГ НИЖЕ — справочные карточки из game/data/items/*.py.\n"
    "Это не таблица случайного дропа с монстров; шанс и этажи ниже указаны условно (каталог / сценарий)."
)

CATALOG_FOOTER = """
────────────────────────────────────────
КАК ПОЛУЧИТЬ В ИГРЕ
Именованные записи подключаются лавкой, квестами, NPC — см. код.
Случайный лут после боя и тайник этажа описаны в файлах 12–16 и 17 в этой папке.
""".strip()


def _kind_ru_emoji(kind: str) -> tuple[str, str]:
    """(emoji, русское название типа) для поля kind."""
    m: dict[str, tuple[str, str]] = {
        "weapon": ("⚔️", "Оружие"),
        "armor": ("🛡️", "Нагрудник"),
        "helmet": ("⛑️", "Шлем"),
        "pants": ("👖", "Поножи"),
        "gloves": ("🧤", "Перчатки"),
        "ring": ("💍", "Кольцо"),
        "amulet": ("📿", "Амулет"),
        "shield": ("🛡️", "Щит"),
        "grimoire": ("📖", "Гримуар"),
        "misc": ("📦", "Разное"),
        "consumable": ("🧪", "Расходник"),
        "rune": ("💎", "Руна"),
    }
    k = str(kind).strip().lower()
    return m.get(k, ("📦", k or "—"))


def _weapon_type_ru(wt: str) -> str:
    m = {
        "blade": "клинок",
        "staff": "посох",
        "bow": "лук",
        "dagger": "кинжал",
        "axe": "топор",
        "polearm": "древковое",
        "hammer": "молот",
    }
    return m.get(wt, wt)


def _relative_item_png_path(image_url: Any) -> str | None:
    """Относительный путь для правки арта: tower_bot/assets/items/<stem>.png."""
    if not image_url:
        return None
    stem = Path(str(image_url).replace("\\", "/")).stem
    if not stem:
        return None
    return f"tower_bot/assets/items/{stem}.png"


def _lines_stats(d: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, label in STAT_ORDER:
        if str(key).startswith("export_"):
            continue
        if key in d and d[key] is not None:
            v = d[key]
            if isinstance(v, bool):
                continue
            if key == "enchant" and int(v) == 0:
                continue
            lines.append(f"  • {label}: +{v}")
    wt = d.get("weapon_type")
    if wt:
        lines.append(f"  • Тип оружия: {_weapon_type_ru(str(wt))} ({wt})")
    hand = d.get("hand")
    if hand == "main":
        lines.append("  • Рука: основная")
    elif hand == "off":
        lines.append("  • Рука: левая / вторая")
    if d.get("two_handed"):
        lines.append("  • Двуручное: да")
    rs = d.get("ring_slot")
    if rs is not None:
        lines.append(f"  • Слот кольца: {rs}")
    sk = d.get("set_key")
    if sk:
        lines.append(f"  • Набор: {sk}" + (f" ({d.get('set_piece')})" if d.get("set_piece") else ""))
    return lines


def _block(
    idx: int,
    d: dict[str, Any],
    *,
    acquisition: str | None = None,
    drop_note: str = "—",
    floor_note: str = "—",
    rarity_line_mode: str = "default",
    show_image_path: bool = False,
) -> str:
    name = str(d.get("name", ""))
    rarity_key = str(d.get("rarity", ""))
    rarity = RARITY_RU.get(rarity_key, rarity_key)
    desc = str(d.get("summary", "")).strip()
    kind = str(d.get("kind") or "").strip()
    k_emoji, kind_ru = _kind_ru_emoji(kind)
    title = f"[{idx}] {k_emoji} {name}" if kind else f"[{idx}] {name}"
    if rarity_line_mode == "floors_only":
        rarity_line = f"Редкость: {rarity} · Этажи дропа: {floor_note}"
    else:
        rarity_line = f"Редкость: {rarity} · Шанс получения: {drop_note} · Этажи: {floor_note}"
    lines = [
        "",
        "────────────────────────────────────────",
        title,
        rarity_line,
    ]
    if kind:
        lines.append(f"Тип: {kind_ru}")
    img_path = _relative_item_png_path(d.get("image_url")) if show_image_path else None
    if img_path:
        lines.append(f"Путь к картинке: {img_path}")
    lines.extend(
        [
            "",
            "Описание:",
            desc,
            "",
            "Что даёт (статы в данных):",
        ],
    )
    stat_lines = _lines_stats(d)
    if stat_lines:
        lines.extend(stat_lines)
    else:
        ut = d.get("use_tag")
        if ut:
            lines.append(f"  • Применение: {ut}, значение {d.get('use_value', '—')}")
        elif d.get("kind") == "rune":
            lines.append(f"  • Руна: {d.get('rune', '—')}")
        else:
            lines.append("  (нет числовых статов в записи)")
    if acquisition:
        lines.extend(["", "Как получить:", acquisition])
    return "\n".join(lines)


def _header(title: str, src: str) -> str:
    return (
        "=" * 76
        + "\n"
        + f"  {title}\n"
        + f"  Источник в коде: {src}\n"
        + "  Редактируйте текст; для синхронизации с игрой пришлите файлы разработчику.\n"
        + "=" * 76
    )


def _write_catalog(
    filename: str,
    title: str,
    src: str,
    rows: list[dict[str, Any]],
    *,
    intro: str | None = None,
    footer: str | None = None,
    default_drop_note: str = "не дроп с монстров (справочник)",
    default_floor_note: str = "по сценарию / лавка / квест",
    rarity_line_mode: str = "default",
    show_image_path: bool = False,
) -> None:
    parts = [_header(title, src), "", (intro or CATALOG_INTRO), ""]
    for i, row in enumerate(rows, 1):
        dn = row.get("export_drop_note")
        if dn is None:
            dn = default_drop_note
        fn = row.get("export_floor_note")
        if fn is None:
            fn = default_floor_note
        parts.append(
            _block(
                i,
                row,
                drop_note=str(dn),
                floor_note=str(fn),
                rarity_line_mode=rarity_line_mode,
                show_image_path=show_image_path,
            ),
        )
    parts.append(footer or CATALOG_FOOTER)
    parts.append("")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / filename).write_text("\n".join(parts), encoding="utf-8")


LOOT_NORMAL_WEIGHTS_HINT = """
Относительные веса строк в пуле (до расширения для этажа ≤ 12):
  эликсир HP 1.15 · MP 0.95 · %HP 0.62 · перчатки 0.74 · кольцо 0.26 · трофей 0.11
При этаже ≤ 12 добавляются дополнительные варианты оружия, брони, щита, гримуара (см. game/items/loot.py).
""".strip()

LOOT_ELITE_WEIGHTS = "Веса строк _elite_loot: оружие 1.0 · накидка 0.95 · шлем 0.7 · эликсир 0.85 · отвар 0.55"
LOOT_MINI_WEIGHTS = "Веса _mini_boss_loot: оружие 1.0 · латы 0.92 · шлем 0.65 · перчатки 0.92 · запас 0.45"
LOOT_MAJOR_WEIGHTS = "Веса _major_boss_loot: оружие 1.0 · броня 0.95 · амулет 0.55 · кольцо 0.6 · сосуд 0.56"


def _scaled_drop_chance(low: float, high: float, floor_number: int) -> float:
    if int(floor_number) <= int(DROP_CHANCE_FLOOR_LOW_MAX):
        return min(0.95, float(low))
    return min(0.95, float(high))


def _doc_loot_normal_sample(fl: int) -> str:
    heal = min(120, 22 + fl * 3)
    mp_v = min(70, 14 + fl * 2)
    pct = min(30, 18 + fl // 4)
    atk_base = ls.normal_weapon_attack_low(fl, dagger_or_bow=False)
    atk_db = ls.normal_weapon_attack_low(fl, dagger_or_bow=True)
    lines = [
        f"Пример чисел для этажа победы N = {fl} (формулы game/items/loot_scaling.py):",
        f"  • Настой странника (HP): восстановление {heal} HP",
        f"  • Капля маны (MP): {mp_v} MP",
        f"  • Слабый эликсир % HP: {pct}% от макс. HP",
        f"  • Перчатки {fl}: защита {ls.normal_gloves_defense(fl)}",
        f"  • Кольцо {fl}: защита {ls.normal_ring_defense(fl)}",
        f"  • Клинок {fl} (случайный тип оружия): атака ~{atk_base}",
        f"  • Сук {fl}: атака ~{max(3, atk_base - 1)}",
        f"  • Мох. накидка: защита {ls.moss_armor_defense(fl)}, бонус HP {ls.moss_armor_hp_bonus(fl)}",
        f"  • Капюшон {fl}: защита {ls.cap_defense(fl)}",
        f"  • Оберег: защита {ls.charm_defense(fl)}",
        f"  • Роса {fl}: атака ~{ls.rare_edge_attack(fl)}",
        f"  • Кинжал пары / Боковик пары: атака ~{atk_db} и ~{max(3, atk_db - 2)}",
        f"  • Клеймор уступа: атака ~{ls.greatsword_attack(fl)}",
        f"  • Меч равновесия: атака ~{atk_base}, вит +1",
        f"  • Щит равновесия: защита {ls.balanced_shield_defense(fl)}",
        f"  • Посох дуги: атака ~{max(4, atk_base - 1)}, инт +2",
        f"  • Палочка фокуса: атака ~{max(3, atk_base - 3)}, инт/удача +1",
        f"  • Гримуар заметок: инт +2, защита 1",
    ]
    return "\n".join(lines)


def _write_text(name: str, title: str, src: str, body: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = _header(title, src) + "\n\n" + body.strip() + "\n"
    (OUT_DIR / name).write_text(text, encoding="utf-8")


def _write_index() -> None:
    body = "\n".join(
        [
            "Содержимое папки (все предметы и источники)",
            "  01–11  — именованный каталог экипировки (game/data/items)",
            "  12     — лут после боя: обычная цель на карте",
            "  13     — лут: элита",
            "  14     — лут: мини-босс (этажи 5, 15, 25, … — каждый ×5, кроме ×10)",
            "  15     — лут: сильный босс (этажи 10, 20, …)",
            "  16     — тайник этажа (кнопка поиска) + фиксированный пул низких этажей",
            "  17     — лавка (город / торговец на этаже) и товары этажа 3",
            "  18     — стартовые подарки, промо, реферальные награды",
            "  19     — рунные камни (валюта) и гемы-руны в сумку",
            "  20     — мировое событие «Золотой гоблин»",
            "",
            "Шансы дропа предмета в сумку (если есть свободная ячейка):",
            f"  Обычный враг:   этажи 1–5 = {DROP_CHANCE_NORMAL_LOW*100:.1f}%,  этажи 6+ = {DROP_CHANCE_NORMAL_HIGH*100:.1f}%",
            f"  Элита:          этажи 1–5 = {DROP_CHANCE_ELITE_LOW*100:.1f}%,  этажи 6+ = {DROP_CHANCE_ELITE_HIGH*100:.1f}%",
            f"  Мини-босс:      этажи 1–5 = {DROP_CHANCE_MINI_LOW*100:.1f}%,  этажи 6+ = {DROP_CHANCE_MINI_HIGH*100:.1f}%",
            f"  Главный босс:   этажи 1–5 = {DROP_CHANCE_MAJOR_LOW*100:.1f}%, этажи 6+ = {DROP_CHANCE_MAJOR_HIGH*100:.1f}%",
            "",
            "Рунный камень (⚗️ валюта кузницы): отдельный бросок RUNE_CHANCE_* по типу цели.",
            "",
            "Гем-руна (предмет «руна» в сумке): дополнительно после элиты или мини/мажор-босса — см. файл 19.",
        ]
    )
    _write_text("00_ИНДЕКС_ИСТОЧНИКИ.txt", "Навигация по файлам предметов", "scripts/export_equipment_catalog_txt.py", body)


def _write_loot_normal() -> str:
    parts = [
        "⚔️ УСЛОВИЕ",
        "• Победа над обычной целью на карте этажа (не элита, не мини-босс, не мажор-босс).",
        "• Срабатывает roll_item_drop из game/floors/rewards.py.",
        f"• Шанс предмета в сумку: этажи 1–5 = {DROP_CHANCE_NORMAL_LOW*100:.1f}%; этажи 6+ = {DROP_CHANCE_NORMAL_HIGH*100:.1f}%.",
        "• Дроп только если есть свободная ячейка сумки; имя предмета часто содержит номер этажа N.",
        "",
        "📍 Этажи получения: 1–100 (после победы над обычной целью на соответствующем этаже).",
        "",
        "ЧТО ВЫПАДАЕТ",
        "Случайная строка из взвешенной таблицы game/items/loot.py → _normal_loot.",
        "Базовые варианты (любой этаж): настой HP, капля MP, эликсир %HP, перчатки N, кольцо N, трофей.",
        "Если номер этажа ≤ 12 — добавляется расширенный пул: клинок, сук, мох. накидка, капюшон, оберег, редкий клинок, пары кинжалов, двуручник, меч+щит, посохи, гримуар заметок и др.",
        "",
        LOOT_NORMAL_WEIGHTS_HINT,
        "",
        _doc_loot_normal_sample(10),
        "",
        _doc_loot_normal_sample(25),
    ]
    return "\n".join(parts)


def _elite_sample(fl: int) -> str:
    w_att = ls.elite_weapon_attack(fl, staff_or_dagger=False)
    w_sd = ls.elite_weapon_attack(fl, staff_or_dagger=True)
    defb = ls.elite_armor_defense_base(fl)
    return "\n".join(
        [
            f"Пример для этажа {fl}:",
            f"  • Оружие «Элита {fl}»: атака ~{w_att} (или ~{w_sd} для посоха/кинжала)",
            f"  • Накидка: защита ~{defb}, бонус HP {ls.elite_armor_hp_bonus(fl)}",
            f"  • Шлем: защита ~{ls.elite_helm_defense(fl, defb)}",
            "  • Флакон эликсира / эфирный отвар — см. loot.py",
        ],
    )


def _write_loot_elite() -> str:
    parts = [
        "⭐ УСЛОВИЕ: победа над элитой на этаже.",
        f"Шанс предмета в сумку: этажи 1–5 = {DROP_CHANCE_ELITE_LOW*100:.1f}%; этажи 6+ = {DROP_CHANCE_ELITE_HIGH*100:.1f}%.",
        "",
        "📍 Этажи: любой этаж, где на карте есть элита.",
        "",
        "ТАБЛИЦА: game/items/loot.py → _elite_loot (оружие, накидка, шлем, эликсиры).",
        "Тип оружия элитного дропа выбирается случайно из набора blade/staff/bow/dagger/axe/polearm/hammer.",
        "",
        LOOT_ELITE_WEIGHTS,
        "",
        _elite_sample(10),
    ]
    return "\n".join(parts)


def _mini_sample(fl: int) -> str:
    return "\n".join(
        [
            f"Пример для этажа {fl} (мини-босс зоны):",
            f"  • Клык {fl}: атака {ls.mini_weapon_attack(fl)}, заточка из mini_weapon_enchant",
            f"  • Латы: защита {ls.mini_armor_defense(fl)}, бонус HP {ls.mini_armor_hp_bonus(fl)}",
            f"  • Шлем/перчатки претендента: от защиты лат",
            "  • Запас претендента — сильное лечение HP",
        ],
    )


def _write_loot_mini() -> str:
    parts = [
        "🗡️ УСЛОВИЕ: победа над мини-боссом (этажи 5, 15, 25, … — каждый 5-й, кроме 10, 20, …).",
        f"Шанс предмета в сумку: этажи 1–5 = {DROP_CHANCE_MINI_LOW*100:.1f}%; этажи 6+ = {DROP_CHANCE_MINI_HIGH*100:.1f}%.",
        "",
        "📍 Этажи получения: 5, 15, 25, 35, … 95 (не 10, 20, …).",
        "",
        "ТАБЛИЦА: _mini_boss_loot в game/items/loot.py",
        "",
        LOOT_MINI_WEIGHTS,
        "",
        _mini_sample(15),
    ]
    return "\n".join(parts)


def _major_sample(fl: int) -> str:
    return "\n".join(
        [
            f"Пример для этажа {fl} (сильный босс зоны):",
            f"  • Корона {fl}: атака {ls.major_weapon_attack(fl)}, заточка {ls.major_weapon_enchant(fl)}",
            f"  • Страж {fl}: защита {ls.major_armor_defense(fl) + 2}, бонус HP",
            "  • Печать этажа (амулет), Победа N (кольцо), Сосуд триумфа",
        ],
    )


def _write_loot_major() -> str:
    parts = [
        "👑 УСЛОВИЕ: победа над сильным боссом (каждый 10-й этаж: 10, 20, 30, …).",
        f"Шанс предмета в сумку: этажи 1–5 = {DROP_CHANCE_MAJOR_LOW*100:.1f}%; этажи 6+ = {DROP_CHANCE_MAJOR_HIGH*100:.1f}%.",
        "",
        "📍 Этажи получения: 10, 20, 30, … 100.",
        "",
        "ТАБЛИЦА: _major_boss_loot в game/items/loot.py",
        "",
        LOOT_MAJOR_WEIGHTS,
        "",
        _major_sample(20),
    ]
    return "\n".join(parts)


def _write_secret() -> str:
    total_w = sum(w for w, _ in SECRET_GEAR_ITEMS) or 1
    secret_room_pct = SECRET_ROOM_CHANCE * 100
    gear_if_secret_pct = SECRET_GEAR_DROP_CHANCE * 100
    parts = [
        "🔍 УСЛОВИЕ",
        "• На экране этажа есть действие «обыск / тайник» (services/floor_service.try_secret_search).",
        "• Один попытка за текущий «заход» на этаж; после неудачи или успеха — снова после следующей победы на этом этаже.",
        f"• Шанс найти тайник при обыске: ~{secret_room_pct:.0f}%.",
        f"• Если тайник найден — предмет из кисета в сумку с шансом ~{gear_if_secret_pct:.0f}% (если сумка не полна).",
        "",
        "РЕЖИМ ЭТАЖЕЙ 1–" + str(SECRET_GEAR_EARLY_MAX_FLOOR) + " — фиксированный пул (карточки ниже).",
        "РЕЖИМ С ЭТАЖА " + str(SECRET_GEAR_EARLY_MAX_FLOOR + 1) + f" ДО {SECRET_GEAR_MAX_FLOOR} — процедурная вещь по слоту и ярусу этажа.",
        "",
        "─── Фиксированный пул (тайник, этажи 1–" + str(SECRET_GEAR_EARLY_MAX_FLOOR) + ") ───",
    ]
    for i, (w, data) in enumerate(SECRET_GEAR_ITEMS, 1):
        d = dict(data)
        share = float(w) / float(total_w)
        approx_pct = SECRET_ROOM_CHANCE * SECRET_GEAR_DROP_CHANCE * share * 100
        drop_note = (
            f"≈{approx_pct:.1f}% на обыск (тайник ~{secret_room_pct:.0f}% × предмет ~{gear_if_secret_pct:.0f}% × доля пула {share * 100:.1f}%)"
        )
        parts.append(
            _block(
                i,
                d,
                drop_note=drop_note,
                floor_note=f"1–{SECRET_GEAR_EARLY_MAX_FLOOR} (фикс. пул), вес в пуле {w}",
            ),
        )
    parts.append("")
    parts.append(
        "─── Процедурный тайник (этажи " + str(SECRET_GEAR_EARLY_MAX_FLOOR + 1) + f"–{SECRET_GEAR_MAX_FLOOR}) ───",
    )
    parts.append("Случайный слот экипировки и редкость масштабируются этажом (secret_gear._scaled_secret_gear).")
    parts.append("Типы предметов: 🛡️ нагрудник · 👖 поножи · ⛑️ шлем · 🧤 перчатки · 💍 кольцо · 📿 амулет.")
    parts.append(
        f"Шанс по сценарию: как у тайника выше (~{secret_room_pct:.0f}% × ~{gear_if_secret_pct:.0f}% на предмет при найденном тайнике).",
    )
    return "\n".join(parts)


def _write_shop() -> str:
    lines: list[str] = [
        "🏪 ЛАВКА — РАСХОДНИКИ (торговец на этаже / в городе-хабе)",
        "Файл: game/economy/shop.py — SHOP_GOODS",
        "Покупка за золото: шанс 100% при достатке монет · этажи: лавка на любом этаже с торговцем / в хабе.",
        "",
    ]
    for g in SHOP_GOODS:
        d = dict(g.item_data)
        lines.append(f"• {g.name} ({g.key}) — {g.price} 💰 базово, цена растёт с этажом (effective_good_price).")
        lines.append(f"  {g.blurb}")
        lines.append(f"  Данные предмета: {d.get('summary', '')}")
        lines.append("")
    lines.append("ЭТАЖ 3 — ДОП. СНАРЯЖЕНИЕ (только если floor_number == 3)")
    lines.append("SHOP_FLOOR3_GEAR:")
    lines.append("Шанс: покупка 100% · Этажи получения: только этаж 3 при посещении лавки.")
    lines.append("")
    for g in SHOP_FLOOR3_GEAR:
        lines.append(f"• {g.name} — {g.price} 💰 · {g.blurb}")
        lines.append(f"  {g.item_data.get('summary', '')}")
        lines.append("")
    lines.append("ГЛАВНОЕ МЕНЮ «МАГАЗИН» — ВИРТУАЛЬНЫЕ ОБЛИКИ")
    lines.append("Разблокировка портрета персонажа за 💰 (не предмет в сумке).")
    for g in SHOP_PORTRAITS:
        lines.append(f"• {g.name} ({g.key}) — {g.price} 💰 — {g.blurb}")
    return "\n".join(lines)


def _write_starters() -> str:
    chunks: list[str] = []

    def add(title: str, rows: list[dict[str, Any]], how: str) -> None:
        chunks.append(f"=== {title} ===")
        chunks.append(f"Как получить: {how}")
        chunks.append("")
        for i, d in enumerate(rows, 1):
            chunks.append(
                _block(
                    i,
                    d,
                    acquisition=how,
                    drop_note="выдача/награда 100%",
                    floor_note="стартовый этаж / акция (см. текст выше)",
                ),
            )
        chunks.append("")

    add("Хлеб и поножи", [starter_bread_payload(), starter_pants_payload()], "Стартовая выдача / обучение (см. код выдачи персонажу).")
    add(
        "Стартовое оружие по классу",
        [starter_weapon_payload(k) for k in ("wanderer", "warrior", "mage", "archer", "assassin")],
        "Выбор класса при создании героя (полный список классов — в starters.starter_weapon_payload).",
    )
    ad, am = promo_starter_armor_amulet_payloads()
    add("Промо кольчуга и медальон", [ad, am], "Промо-набор новичка (условия выдачи — в сервисе промо).")
    rg1, rg2 = referral_inviter_gear_payloads()
    add("Реферал: перчатки и кольцо", [rg1, rg2], "Награда за приглашённого друга (реферальная программа).")
    add("Реферал: ожерелье", [referral_inviter_epic_necklace_payload()], "Эпический амулет за нескольких достигших 3 уровня по ссылке.")
    add(
        "Кинжал второй руки",
        [starter_offhand_dagger_payload()],
        "Выдаётся классам с парным стилем (например ассасин).",
    )

    return "\n".join(chunks)


def _write_runes_doc() -> str:
    return "\n".join(
        [
            "⚗️ РУННЫЙ КАМЕНЬ (валюта кузницы)",
            "После победы: отдельный бросок roll_rune_stone(spawn) в game/floors/rewards.py",
            f"  • обычная цель: ≈{RUNE_CHANCE_NORMAL * 100:.0f}%",
            f"  • элита: ≈{RUNE_CHANCE_ELITE * 100:.0f}%",
            f"  • мини-босс: ≈{RUNE_CHANCE_MINI * 100:.0f}%",
            f"  • сильный босс: ≈{RUNE_CHANCE_MAJOR * 100:.0f}%",
            "Награда: +1 к счётчику рунных камней персонажа (для кузницы).",
            "В сумке как предмет не лежит — счётчик в профиле.",
            "📍 Этажи: любые, где есть победа над указанным типом цели.",
            "",
            "💎 ГЕМ-РУНА (предмет «руна» в сумке)",
            "После победы над элитой ИЛИ мини/мажор-боссом: game/items/runes.roll_rune_drop.",
            "Дополнительный фильтр: лишь ~8% попыток превращаются в гем-руну; ранг и стихия случайны по этажу.",
            "📍 Этажи: как у элиты / мини / мажор-босса (см. файлы 13–15).",
            "",
            "Стихии и ранги: game/items/runes.py (ELEMENTS, RUNE_RANK_STATS).",
            "Имя гема: стихия + ранг (римские цифры в RuneData.display_name).",
        ],
    )


def _write_golden_goblin() -> str:
    return "\n".join(
        [
            "💰 Мировое событие «Золотой гоблин» (services/golden_goblin_service.py)",
            "• Периодически выбирается этаж от 5 до 20; на этом этаже на карте появляется монстр-событие.",
            "• Первый игрок в волне, победивший гоблина: +1000…2000 💰 и +1000 опыта (combat_service).",
            "• Шанс «редкого» дропа из обычных таблиц победы для этого убийства отключён — отдельная награда.",
            "• Следующие убийцы в той же волне получают обычные награды за победу.",
            "",
            "📍 Этажи появления: 5–20 · Шанс для игрока — когда событие активно и гоблин заспавнен на вашем этаже.",
        ],
    )


def main() -> None:
    _write_index()

    _write_catalog("01_НАГРУДНИК.txt", "Нагрудники (броня)", "game/data/items/armor.py → armor_examples()", armor_examples())
    _write_catalog("02_ШЛЕМ.txt", "Шлемы", "game/data/items/armor.py → helmet_examples()", helmet_examples())
    _write_catalog("03_ПОНОЖИ.txt", "Поножи", "game/data/items/armor.py → pants_examples()", pants_examples())
    _write_catalog("04_ПЕРЧАТКИ.txt", "Перчатки", "game/data/items/armor.py → gloves_examples()", gloves_examples())
    _write_catalog("05_ЩИТЫ.txt", "Щиты", "game/data/items/offhand.py → shield_examples()", shield_examples())
    _write_catalog("06_ГРИМУАРЫ.txt", "Гримуары", "game/data/items/offhand.py → grimoire_examples()", grimoire_examples())
    _write_catalog(
        "07_КОЛЬЦА.txt",
        "Кольца",
        "game/data/items/rings.py → ring_examples()",
        ring_examples(),
        intro=RING_CATALOG_INTRO,
        footer=RING_CATALOG_FOOTER,
        default_drop_note="дроп по схеме этажа / сундуки",
        rarity_line_mode="floors_only",
        show_image_path=True,
    )
    _write_catalog("08_АМУЛЕТЫ.txt", "Амулеты", "game/data/items/amulets.py → amulet_examples()", amulet_examples())

    mains = weapon_main_examples()
    main_1h = [r for r in mains if not r.get("two_handed")]
    main_2h_only = [r for r in mains if r.get("two_handed")]
    two_h = two_handed_weapon_examples()
    _write_catalog(
        "09_ОРУЖИЕ_ОСНОВНАЯ_РУКА_ОДНОРУЧНОЕ.txt",
        "Оружие в основную руку (одноручное)",
        "game/data/items/weapons.py → weapon_main_examples(), без two_handed",
        main_1h,
    )
    _write_catalog(
        "10_ОРУЖИЕ_ЛЕВАЯ_РУКА.txt",
        "Оружие во вторую руку (левая)",
        "game/data/items/weapons.py → weapon_offhand_examples()",
        weapon_offhand_examples(),
    )
    combined_2h = main_2h_only + two_h
    _write_catalog(
        "11_ОРУЖИЕ_ДВУРУЧНОЕ.txt",
        "Двуручное оружие",
        "game/data/items/weapons.py (two_handed в main + two_handed_weapon_examples)",
        combined_2h,
    )

    _write_text("12_ЛУТ_ПОБЕДА_ОБЫЧНАЯ_ЦЕЛЬ.txt", "Лут: обычная цель", "game/items/loot.py::_normal_loot", _write_loot_normal())
    _write_text("13_ЛУТ_ПОБЕДА_ЭЛИТА.txt", "Лут: элита", "game/items/loot.py::_elite_loot", _write_loot_elite())
    _write_text("14_ЛУТ_ПОБЕДА_МИНИБОСС.txt", "Лут: мини-босс", "game/items/loot.py::_mini_boss_loot", _write_loot_mini())
    _write_text("15_ЛУТ_ПОБЕДА_МАЖОРБОСС.txt", "Лут: сильный босс", "game/items/loot.py::_major_boss_loot", _write_loot_major())
    _write_text("16_ТАЙНИК_ЭТАЖА.txt", "Тайник этажа", "game/items/equipment/secret_gear.py + floor_service.try_secret_search", _write_secret())
    _write_text("17_ЛАВКА_РАСХОДНИКИ_И_ЭТАЖ3.txt", "Лавка", "game/economy/shop.py", _write_shop())
    _write_text("18_СТАРТ_ПРОМО_РЕФЕРАЛ.txt", "Старт и акции", "game/items/equipment/starters.py", _write_starters())
    _write_text("19_РУНЫ_И_РУННЫЕ_КАМНИ.txt", "Руны и рунные камни", "game/floors/rewards.py + game/items/runes.py", _write_runes_doc())
    _write_text("20_ЗОЛОТОЙ_ГОБЛИН.txt", "Золотой гоблин", "services/golden_goblin_service.py", _write_golden_goblin())

    readme = OUT_DIR / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "Папка catalog_txt_edit/",
                "",
                "Сгенерировано: python -m scripts.export_equipment_catalog_txt",
                "",
                "01–11 — справочный каталог предметов (game/data/items): редкость, условный шанс и этажи, тип на русском.",
                "12–15 — дроп после боя по типу цели (шансы и диапазоны этажей из game/balance и loot.py).",
                "16 — тайник этажа, 17 — лавка, 18 — старт и акции, 19 — руны, 20 — золотой гоблин.",
                "",
                "После правок пришлите файлы для синхронизации с кодом.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print("OK:", OUT_DIR)


if __name__ == "__main__":
    main()
