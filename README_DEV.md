# Башня Испытаний — карта для разработчика

## Куда класть код

| Что | Путь |
|-----|------|
| Статика (баланс, предметы, JSON) | `content/data/` — импорт `game.data.*` |
| PNG / арт | `content/assets/` — пути через `game.core.paths` |
| Логика игры | `game/` (`combat`, `tower`, `enemies`, `items`, …) |
| Оркестрация | `services/<combat\|progression\|economy\|social\|system>/` |
| Telegram UI | `bot/handlers/`, `bot/keyboards/` |
| Общие хелперы | `utils/media/` (PNG), `utils/telegram/` (текст, якоря) |
| Скрипты | `devtools/` (не импортировать из бота) |

## Башня и монстры

- Этажи, зоны, награды: `game/tower/progression/`
- Квесты на этаже: `game/tower/quests/`
- Спавны и каталог монстров: `game/enemies/`
- Спец-механики этажа: `game/tower/mechanics/` — `registry.py` (`room_clear` / `explore` / `wave`, `spawns_for_tower_progress`, `tower_field_repair_allowed`)
- Квесты города/таверны: `game/quests/`

## Предметы

- **Данные** (таблицы лута): `content/data/items/`
- **Логика** (roll, заточка): `game/items/`

## Assets после clone

```powershell
cd tower_bot
powershell -File devtools/assets/setup_assets_link.ps1
python devtools/assets/init_game_art_placeholders.py
```

Подробнее: `.cursor/rules/01-architecture.mdc`, `devtools/README.md`.
