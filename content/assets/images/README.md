# Картинки для бота

Подставь свои **PNG** (или JPEG для ручной замены кода) с теми же именами.

## `locations/`

Фон этажа по **ключу зоны** из `game/tower/progression/floor_data.py`:

| Файл | Зона |
|------|------|
| `forest_beginnings.png` | Лес Начал (1–10) |
| `rotten_swamps.png` | Гнилые Болота |
| `shadow_caves.png` | Пещеры Теней |
| `icy_peaks.png` | Ледяные Пики |
| `desert_oblivion.png` | Пустыня Забвения |
| `volcanic_ruins.png` | Вулканические Руины |
| `sky_citadel.png` | Небесная Крепость |
| `chaos_abyss.png` | Бездна Хаоса |
| `eternity_hall.png` | Зал Вечности |
| `tower_warden.png` | Страж (этаж 100) |
| `default.png` | Если файла зоны нет |

Рекомендуемый размер: **1280×720** или **1024×576** (читаемо в Telegram).

## Монстры

PNG монстров лежат в **`tower_bot/assets/monsters/`** (общий каталог для боя и `monster_image_for_template`). Подпапки `images/monsters/` больше не используются.

## `items/`

`default.png` — заглушка предмета; позже можно добавить `sword_iron.png` и т.д. по `item_data`.

## Генерация заглушек

Из корня `tower_bot`:

```bash
python scripts/generate_image_placeholders.py
```

Скрипт кладёт один минимальный PNG во все нужные пути.
