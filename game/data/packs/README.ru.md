# Паки контента башни

Каждая **зона** — отдельная папка. Редактируйте JSON без правок Python.

## Структура пака зоны

```
packs/zones/<zone_key>/
  zone.json          — название, этажи, описание, floor_type
  monsters.json      — пул и карточки монстров (мерж в monsters_catalog)
  npcs.json          — NPC этажа (имя, профессия, диалоги)
  materials.json     — материалы профессий (id, имя, редкость)
  blueprints.json    — чертежи (id, профессия, tier, рецепт-ссылка)
  trials/
    floor_61.json    — испытание этажа (тип, угодья, цели, хардкор)
    floor_62.json
    ...
```

## Реестр

`packs/registry.json` — список активных паков и диапазон этажей.

## Правила наград NPC

В `npcs.json` → `quests[].rewards` только:

- `materials`: `[{"id": "blood_vial", "qty": 3}]`
- `blueprints`: `[{"id": "blueprint_potion_antibleed_2", "qty": 1}]`
- **без** готовых предметов экипировки

## Загрузка в коде

```python
from game.data.packs import load_zone_pack, trial_for_floor, npcs_for_floor
```
