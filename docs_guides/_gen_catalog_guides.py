"""Run from tower_bot/: python docs_guides/_gen_catalog_guides.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs_guides"


def fmt_mods(mods: dict) -> str:
    if not mods:
        return "—"
    return ", ".join(f"{k}: {v}" for k, v in mods.items())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    from game.archetypes.data import ARCHETYPES, SKILLS

    lines: list[str] = []
    lines.extend(
        [
            "============================================================================",
            "  Классы (архетипы), навыки и пассивки",
            "  Источник в коде: game/archetypes/data.py → ARCHETYPES, SKILLS",
            "  Мост боевых данных: game/characters/skills.py → skills_for_class(), SkillDef",
            "  Дерево навыков: game/archetypes/manager.py",
            "",
            "Связанные файлы:",
            "  • game/archetypes/data.py — ключи классов, skills[], passives[], base_stats",
            "  • game/archetypes/manager.py — get_archetype, разблокировка через дерево",
            "  • game/characters/skills.py — passive_combat_modifiers_merged",
            "  • game/combat/engine.py — расчёт боя по SkillDef",
            "  • services/combat_service.py — старт/победа в бою",
            "  • services/character_service.py — class_key при создании",
            "  • bot/handlers/profile.py, bot/handlers/stats_alloc.py",
            "Редактируйте справочник вручную; для синка с кодом передайте dev или перезапустите генератор.",
            "============================================================================",
            "",
            "В бою первые три слота навыков могут браться из дерева талантов игрока, а не только из списка ниже.",
            "",
        ]
    )

    for key in sorted(ARCHETYPES.keys()):
        a = ARCHETYPES[key]
        name = getattr(a, "name_ru", key)
        lines.append("────────────────────────────────────────")
        lines.append(f"[{key}] {name}")
        lines.append("")
        bases = getattr(a, "base_stats", {}) or {}
        if bases:
            lines.append("Базовые статы:")
            lines.append(f"  {bases}")
            lines.append("")
        sk_keys = list(getattr(a, "skills", []) or [])
        lines.append("Навыки (ключи в SKILLS):")
        for i, sk_key in enumerate(sk_keys[:24], 1):
            s = SKILLS.get(sk_key)
            if not s:
                lines.append(f"  {i}. `{sk_key}` — (нет записи в SKILLS)")
                continue
            nm = getattr(s, "name_ru", sk_key)
            lines.append(f"  {i}. `{sk_key}` — {nm}")
            lines.append(
                f"     MP {getattr(s, 'mp_cost', 0)} · перезарядка {getattr(s, 'cooldown', 0)} · "
                f"{getattr(s, 'kind', '')} · сила×{getattr(s, 'power_mult', 0)}"
            )
            eff = getattr(s, "effect_key", None)
            if eff:
                lines.append(
                    f"     эффект: {eff}, шанс {getattr(s, 'effect_chance', 0)}"
                )
        lines.append("")
        pas = getattr(a, "passives", []) or []
        if not pas:
            lines.append("Пассивки архетипа: нет в данных.")
        else:
            lines.append("Пассивки архетипа:")
            for p in pas:
                pn = getattr(p, "name_ru", "?")
                mods = getattr(p, "modifiers", {}) or {}
                lines.append(f"  • {pn}")
                lines.append(f"    модификаторы: {fmt_mods(mods)}")
        lines.append("")

    (OUT / "00_КЛАССЫ_И_НАВЫКИ.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    from game.quests import story_quests as sq_mod

    nlines: list[str] = []
    nlines.extend(
        [
            "============================================================================",
            "  NPC и задания",
            "  Сюжетные NPC этажа 1 (Тихий Ручей): game/quests/story_quests.py",
            "============================================================================",
            "",
            "Связанные файлы:",
            "  • game/quests/story_quests.py — тексты NPC, условия, награды",
            "  • bot/handlers/floor.py — коллбэки fl:* (story_npc, sq:*)",
            "  • bot/keyboards/floor_kb.py — кнопка «Сюжетные NPC»",
            "  • services/floor_service.py — экран этажа, город",
            "  • bot/handlers/city.py — город: кузница, экономика-хабы",
            "  • bot/handlers/tavern.py — таверна",
            "  • bot/handlers/quests.py — раздел заданий",
            "  • services/quest_service.py · services/tavern_service.py",
            "  • game/floors/wandering_npcs.py — странники",
            "  • services/wandering_npc_quest_service.py — квест странника",
            "  • game/quests/*.py — city_quests, daily_quests, npc_quests и т.д.",
            "  • db/models/quest.py, db/repository/quest_repo.py",
            "",
            "──────── Таблица: сюжетные NPC (этаж 1) ────────",
            "",
        ]
    )

    hdr = "| NPC | Эмодзи | Квест | Цель | Награда (кратко) |\n|-----|--------|-------|------|-----------------|"
    row_lines = [hdr]
    for q in sq_mod.STORY_QUESTS:
        rew = []
        if q.reward_xp:
            rew.append(f"{q.reward_xp} XP")
        if q.reward_gold:
            rew.append(f"{q.reward_gold} зол")
        rew_s = "+".join(rew)
        targ = ""
        if q.condition_type == "kills":
            targ = f"убить {q.condition_target}"
        elif q.condition_type == "material_count":
            targ = f"материалы {q.condition_target}"
        elif q.condition_type == "floor_reached":
            targ = f"этаж ≥ {q.condition_target}"
        row_lines.append(f"| `{q.npc_key}` | {q.npc_name} | «{q.quest_title}» | {targ} | {rew_s} |")
    nlines.extend(row_lines)

    nlines.extend(
        [
            "",
            "──────── Карточки по квестам ────────",
            "",
        ]
    )

    for q in sq_mod.STORY_QUESTS:
        nlines.extend(
            [
                f"[{q.npc_key}] {q.npc_emoji} {q.npc_name}",
                f"Роль: {q.npc_role}",
                f"«{q.quest_title}»: {q.quest_desc.strip().replace(chr(10), ' ')}",
                f"Условие: type={q.condition_type}, ключ meta `{q.condition_key}`, цель={q.condition_target}",
                f"Награда: XP {q.reward_xp}, золото {q.reward_gold}",
                f"reward_extra в коде: {q.reward_extra!r}",
                "",
            ]
        )

    nlines.extend(
        [
            "──────── Прочие NPC ────────",
            "",
            "• Странник (random per floor в лесной зоне): fl:*:wnpc",
            "• Города на этажах из CITIES_RAW — см. файл «02 этажи»",
            "",
        ]
    )

    (OUT / "01_НПЦ_И_КВЕСТЫ.txt").write_text("\n".join(nlines) + "\n", encoding="utf-8")

    from game.data import floors as tower_raw

    flines: list[str] = []
    flines.extend(
        [
            "============================================================================",
            "  Особые этажи, зоны башни, эффекты локаций",
            "  Сырые зоны и города: game/data/floors.py",
            "  Интерпретация в игре: game/floors/floor_data.py",
            "============================================================================",
            "",
            "Связанные файлы:",
            "  • game/data/floors.py — ZONES_RAW, ZONE_FINAL_RAW, CITIES_RAW",
            "  • game/floors/floor_data.py — get_zone_for_floor, get_city_for_floor, PORTAL_*",
            "  • services/floor_service.py — format_floor_message, try_secret_search, travel_*",
            "  • bot/handlers/floor.py — главный обработчик этажа и fl:*",
            "  • bot/keyboards/floor_kb.py",
            "  • game/floors/explore_floor_4.py, explore_floor.py, explore_floor_22.py",
            "  • game/floors/room_clear_floor*.py, wave_floor*.py, long_floor.py",
            "  • game/floors/monsters.py — спауны по зоне и этажу",
            "  • game/floors/forest_beginnings.py, rotten_swamps.py и др.",
            "  • game/combat/engine.py — apply_floor_aura_effects (ауры боевого состояния)",
            "============================================================================",
            "",
            "──────── Зоны ────────",
            "",
        ]
    )

    for z in getattr(tower_raw, "ZONES_RAW", []):
        key = z.get("key", "?")
        nm = z.get("name", "")
        ef = z.get("emoji", "")
        f0, f1 = z.get("floor_from"), z.get("floor_to")
        ftype = z.get("floor_type", "normal")
        suf = ""
        if z.get("debuff"):
            suf = f"\n  дебафф: {z.get('debuff')}"
        if z.get("factions"):
            suf += "\n  (фракции — см. ключи floor_type faction_war в коде UI)"
        flines.append(f"• {ef} **{nm}** (`{key}`) — этажи **{f0}–{f1}**, тип `{ftype}`{suf}")

    fz = getattr(tower_raw, "ZONE_FINAL_RAW", None)
    if fz:
        flines.append("")
        flines.append(
            f"• Финал: {fz.get('emoji','')} {fz.get('name','')} `{fz.get('key','')}` — "
            f"этажи {fz.get('floor_from')}–{fz.get('floor_to')}"
        )

    flines.extend(["", "──────── Города-хабы ────────", ""])
    for floor_num, row in sorted(getattr(tower_raw, "CITIES_RAW", {}).items()):
        flines.append(f"Этаж {floor_num}: {row.get('emoji','')} {row.get('name','')}")
        flines.append(f"  {row.get('theme_ru','')}")
        flines.append("")

    flines.extend(
        [
            "──────── Краткая механика ────────",
            "",
            "• Обыск тайника: services/floor_service.try_secret_search; этаж 1 (полный город) — тайников нет.",
            "• Тип этажа `survival`: потеря HP без защиты (см. зоны и scheduler).",
            "• `faction_war`: выбор фракции и репутация перед боссом (floor_kb/floor_service).",
            "• Спец-режимы: исследование (4/8/22), комнаты (5/10/24), волны (27 и др.).",
            "",
        ]
    )

    (OUT / "02_ЭТАЖИ_И_ЭФФЕКТЫ_ЛОКАЦИЙ.txt").write_text("\n".join(flines) + "\n", encoding="utf-8")

    ix = (
        "\n".join(
            [
                "============================================================================",
                "  Индекс документов docs_guides/",
                "============================================================================",
                "",
                "• 00_КЛАССЫ_И_НАВЫКИ.txt",
                "• 01_НПЦ_И_КВЕСТЫ.txt",
                "• 02_ЭТАЖИ_И_ЭФФЕКТЫ_ЛОКАЦИЙ.txt",
                "",
                "Перегенерация содержимого из кода игры:",
                "  cd tower_bot",
                "  python docs_guides/_gen_catalog_guides.py",
                "",
            ]
        )
        + "\n"
    )
    (OUT / "03_ИНДЕКС_СПРАВОЧНИКОВ.txt").write_text(ix, encoding="utf-8")
    print("OK", OUT)


if __name__ == "__main__":
    main()
