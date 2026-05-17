"""Перегенерация room_clear/instances_data.py из CONFIG_* (после правки данных)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.enemies.floors.spawns import MonsterTemplate
from game.tower.mechanics.room_clear.engine import RoomClearBanner
from game.tower.mechanics.room_clear.instances_data import (
    CONFIG_10 as cfg10,
    CONFIG_24 as cfg24,
    CONFIG_26 as cfg26,
    CONFIG_30 as cfg30,
    CONFIG_40 as cfg40,
    CONFIG_5 as cfg5,
)

OUT = ROOT / "game" / "tower" / "mechanics" / "room_clear" / "instances_data.py"

BANNERS: dict[int, RoomClearBanner] = {
    5: RoomClearBanner(
        boss_done="🌳 <b>Сценарий завершён!</b> Страж Прохода пал — ворота открыты.",
        title_fmt="🗺️ <b>Зачистка комнат</b> [{room_bar}] {cleared}/{total} комнат{hint}\n{monster_line}",
        hint_boss=" → <b>открылся Страж!</b>",
        filled_tile="🟩",
    ),
    10: RoomClearBanner(
        boss_done="👑 <b>Катакомбы зачищены!</b> Лорд Тьмы пал — путь на 11-й этаж открыт.",
        title_fmt="💀 <b>Тёмные Катакомбы</b> [{room_bar}] {cleared}/{total} комнат{hint}\n{monster_line}",
        hint_boss=" → <b>Лорд пробудился!</b>",
        filled_tile="🟥",
    ),
    24: RoomClearBanner(
        boss_done="🌑 <b>Пещера зачищена!</b> Теневой Владыка повержен — путь на 25-й этаж открыт.",
        title_fmt="🕯️ <b>Пещеры Теней</b> [{room_bar}] {cleared}/{total} комнат{hint}\n{monster_line}",
        hint_boss=" → <b>Теневой Владыка пробудился!</b>",
        filled_tile="🟣",
    ),
    26: RoomClearBanner(
        boss_done=(
            "🗝️ <b>Зал сомнений пуст.</b> Привратник пал — монстры больше не вернутся. "
            "Открыт <b>Тёмный проход</b> к рынку «Тени Башни». Поднимись на <b>27</b> этаж, когда будешь готов."
        ),
        title_fmt="🗝️ <b>Зал сомнений</b> [{room_bar}] {cleared}/{total} залов{hint}\n{monster_line}",
        hint_boss=" → <b>Привратник ждёт!</b>",
        monster_subhint="<i>(последовательные бои в каждом зале)</i>",
        filled_tile="⬛",
    ),
    30: RoomClearBanner(
        boss_done="🌑 <b>Глубины зачищены!</b> Ночной охотник повержен — путь на 31-й этаж открыт.",
        title_fmt="🕯️ <b>Тёмный периметр (30)</b> [{room_bar}] {cleared}/{total} залов{hint}\n{monster_line}",
        hint_boss=" → <b>Ночной охотник ждёт!</b>",
        monster_line_fmt="Врагов: {mon}/{mon_total} {subhint}",
        filled_tile="🟣",
    ),
    40: RoomClearBanner(
        boss_done="❄️ <b>Вершина взята!</b> Король ледников повержен — путь на 41-й этаж открыт.",
        title_fmt="🌨️ <b>Ледяной цитадельный пояс (40)</b> [{room_bar}] {cleared}/{total} залов{hint}\n{monster_line}",
        hint_boss=" → <b>Король ледников ждёт!</b>",
        monster_line_fmt="Врагов: {mon}/{mon_total} {subhint}",
        monster_subhint="<i>(в каждом зале — последовательные бои)</i>",
        filled_tile="🧊",
    ),
}

CONFIGS = [
    ("CONFIG_5", cfg5),
    ("CONFIG_10", cfg10),
    ("CONFIG_24", cfg24),
    ("CONFIG_26", cfg26),
    ("CONFIG_30", cfg30),
    ("CONFIG_40", cfg40),
]

BUTTON_PREFIX = {5: "rc_r", 10: "r10_r", 24: "r24_r", 26: "r26_r", 30: "r30_r", 40: "r40_r"}
ALL_SLOTS_ATTR = {
    5: "ROOM_CLEAR_ALL_SLOTS",
    10: "ROOM_CLEAR_10_ALL_SLOTS",
    24: "ROOM_CLEAR_24_ALL_SLOTS",
    26: "ROOM_CLEAR_26_ALL_SLOTS",
    30: "ROOM_CLEAR_30_ALL_SLOTS",
    40: "ROOM_CLEAR_40_ALL_SLOTS",
}


def _repr_template(t: MonsterTemplate) -> str:
    return f"MonsterTemplate({t.key!r}, {t.name!r}, {t.emoji!r}, {t.element!r}, {t.blurb!r})"


def _repr_room_templates(room_templates: tuple[tuple[MonsterTemplate, ...], ...]) -> str:
    lines = ["("]
    for room in room_templates:
        lines.append("    (")
        for t in room:
            lines.append(f"        {_repr_template(t)},")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines)


def _repr_banner(b: RoomClearBanner) -> str:
    parts = [
        f"boss_done={b.boss_done!r}",
        f"title_fmt={b.title_fmt!r}",
        f"hint_boss={b.hint_boss!r}",
    ]
    if b.monster_line_fmt != "Монстров: {mon}/{mon_total} {subhint}":
        parts.append(f"monster_line_fmt={b.monster_line_fmt!r}")
    if b.monster_subhint != "<i>(в каждой комнате 2-3 последовательных боя)</i>":
        parts.append(f"monster_subhint={b.monster_subhint!r}")
    if b.filled_tile != "🟩":
        parts.append(f"filled_tile={b.filled_tile!r}")
    if b.empty_tile != "⬜":
        parts.append(f"empty_tile={b.empty_tile!r}")
    return f"RoomClearBanner({', '.join(parts)})"


def main() -> None:
    chunks: list[str] = [
        '"""Данные room-clear по этажам (автоген: devtools/gen_room_clear_instances.py)."""',
        "",
        "from __future__ import annotations",
        "",
        "from game.enemies.floors.spawns import MonsterTemplate",
        "from game.tower.mechanics.room_clear.engine import RoomClearBanner, RoomClearConfig",
        "",
    ]

    for var_name, cfg in CONFIGS:
        floor = cfg.floor_number
        banner = BANNERS[floor]
        chunks.append(f"{var_name} = RoomClearConfig(")
        chunks.append(f"    floor_number={floor},")
        chunks.append(f"    meta_key={cfg.meta_key!r},")
        chunks.append(f"    slot_boss={cfg.slot_boss!r},")
        chunks.append(f"    button_prefix={cfg.button_prefix!r},")
        chunks.append(f"    room_groups={cfg.room_groups!r},")
        chunks.append(f"    room_templates={_repr_room_templates(cfg.room_templates)},")
        chunks.append(f"    boss_template={_repr_template(cfg.boss_template)},")
        chunks.append(f"    banner={_repr_banner(banner)},")
        chunks.append(f"    duo_room_index={cfg.duo_room_index},")
        chunks.append(f"    all_slots_attr={ALL_SLOTS_ATTR[floor]!r},")
        chunks.append(")")
        chunks.append("")

    OUT.write_text("\n".join(chunks), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
