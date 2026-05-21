# Каталоги контента (JSON)

Все файлы в этой папке можно править вручную. После изменений **перезапусти бота** (или вызови `reload_all_catalogs()` в коде).

## Первичное заполнение / обновление из кода

```bash
python -m game.data.catalogs.export_seed
```

Скрипт перезапишет JSON актуальными данными из Python (удобно после правок в коде, чтобы синхронизировать файлы).

---

## Файлы

| Файл | Что редактировать |
|------|-------------------|
| **coliseum_fighters.json** | 50 бойцов колизея: имя, `phrase` (реплика в бою), `victory_quote`, HP/ATK/DEF, награды, `element_tz`, `special`, `loot` |
| **cities_hubs.json** | Города-хабы (якоря 0, 30, 60, 90 между ярусами): лор, `welcome_html`, NPC, таверна, `art` |
| **npcs_index.json** | Путники на этажах, зональные квестодатели (`zone_quest_givers`) |
| **quests_registry.json** | Сводка квестов NPC (этаж ×3): награды, тип, цель — для обзора и будущих правок |
| **archetypes_skills.json** | Активные навыки: урон, MP, эффекты |
| **archetypes_passives.json** | Пассивки: `modifiers` (def_bonus, crit_bonus, …) |
| **archetypes_classes.json** | Классы и специализации (tier 0–2): статы, списки skill/passive ключей |
| **archetypes_skill_trees.json** | Узлы навыков (источник для гримуаров): `parent_keys`, тип узла |

Карточки башни (этажи 1–20): `game/tower_cards/tower_card_catalog.json`.

---

## Колизей — поля бойца

- `phrase` — фраза в бою (показывается в каталоге фраз монстра).
- `victory_quote` — текст после победы игрока.
- `special` — механика: `blind_2`, `fear_30`, `zeus_bolt`, … или `none`.
- `element_tz` — стихия ТЗ; в бою мапится через `element_map` в том же JSON.

## Города

Каждый объект в `hubs` — **отдельная локация**: свой `key`, тексты, `tavern_extras`, `art.hub_menu` (путь от `assets/game_art/`).

## Классы

1. Навыки и пассивки — в `archetypes_skills.json` / `archetypes_passives.json`.
2. Класс ссылается на них по ключам в `archetypes_classes.json`.
3. Дерево — в `archetypes_skill_trees.json` → `trees` → ключ архетипа → узлы.

Типы узлов: `stat_boost`, `passive_bonus`, `active_skill` (в `value` — ключ навыка или словарь модификаторов).

---

## Приоритет данных

Если JSON заполнен, игра **подмешивает** его поверх встроенного Python (колизей и города — полностью из JSON при наличии `fighters` / `hubs`; классы — JSON перекрывает совпадающие ключи).
