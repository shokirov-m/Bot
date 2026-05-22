# Паки этажей и зон

Редактирование контента **без Python** — JSON в `content/data/packs/`.

## Дерево

```
content/data/packs/
  registry.json              — список зон-паков
  zones/
    blood_spire/             — вампиры 61–70
      zone.json
      monsters.json
      npcs.json
      materials.json
      blueprints.json
      trials/
        floor_61.json … floor_70.json
    _template/               — подсказка для новых зон
```

## Файлы

| Файл | Содержимое |
|------|------------|
| `zone.json` | ключ, этажи, emoji, описание |
| `monsters.json` | `pool` + `entries` (мерж в каталог боя) |
| `npcs.json` | NPC, диалоги `{player_name}`, квесты |
| `materials.json` | id материалов для профессий |
| `blueprints.json` | чертежи (не готовые предметы) |
| `trials/floor_N.json` | тип испытания, угодья, хардкор-цели (перекрывает автоген) |

**Испытания на всей башне (1–99):** если JSON нет — `game/tower/trials/default_config.py`.

| Доля | Поведение |
|------|-----------|
| **~60%** ярусов | Уникальный вариант из `trial_variants.py` (лор зоны, псевдорандом по номеру этажа) |
| **~40%** | Упрощённое случайное испытание (без одинакового цикла) |

Примеры вариантов: спасение из леса / тюрьмы / «неизвестные», оборона мельницы / плотины / лагеря, поиск улик миража…
Каталог: `game/tower/trials/trial_variants.py`.

Исключения (legacy): explore 4/8/22, room_clear 5/24/26, wave 27, long_floor 15.

**Этажи ×10 (сильный босс):** тип `boss_chamber` — уникальные залы `ft_br00`… (`boss_chambers.py`). JSON: `packs/zones/<zone>/trials/floor_10.json` … `floor_90.json` (10,20,30,40,50,60,70,80,90). На 10/30/40 залы **заменяют** room_clear.

**Сложность 50+:** `apply_floor_difficulty_tiers` — HP ×3.0 / ATK ×2.6 (50–60), ×4.0 / ×3.2 (61–70), ×5.0 / ×3.8 (71+); опционально `floor_stat_mult` в JSON пака.

**Кулдаун босса:** после победы над сильным боссом повторный бой через **15–20 мин** (`boss_retry_cooldown_*_minutes` в JSON, `game/tower/combat/boss_retry_cooldown.py`).

**Уникальные механики боссов:** `game/combat/boss_uniques.py` — у каждого `boss_*` / `mini_*` свои дебаффы, метеориты по отряду (герой + наёмники), уклонения, безмолвие навыков, уязвимость и т.д. В бою отображается строка «Хардкор» в блоке баффов.

## Мастера зоны (overlay на боевом этаже)

- Кнопка **«Мастера зоны»** на этаже (`pqn:hub`) — не отдельный хаб-этаж.
- NPC с `floors_hub: [N]` видны на hub-этаже зоны (середина диапазона, см. `hub` в `seed_zone_packs.py`).
- На hub-этаже в каталоге NPC показываются **все** поручения этого мастера (не только с `floors`, содержащими N).
- Квесты на других этажах — по полю `quests[].floors` (hub-этаж должен быть в списке, если поручение сдаётся там).
- Приветствие: `{player_name}` → `character.display_name`; репутация `honored` после 2+ сданных квестов NPC.

## Библиотека гримуаров

- Отдельный хаб-этаж **9001** (меню «Локации» → Библиотека). Покупка только на 9001.
- Разблокировка: `highest_floor_reached > 18`.

## Награды NPC

Только `materials` и `blueprints` в `quests[].rewards`.

## Код

- Загрузка: `game.data.packs`
- Испытания на экране этажа: `game.tower.trials.pack_config`
- Квесты NPC пака: `services/progression/pack_npc_quest_service.py`, UI `pqn:*`
- Материалы пака: `meta_progress.pack_materials_v1`
- Зоны 1–99: `content/data/floors.py` (этажи 101+ сняты)

## Этапы внедрения

1. ✅ Паки + вампиры 61–70 + UI квестов NPC (`pqn:hub`)
2. ✅ Движок `floor_trial_v1` — `game/tower/trials/floor_trial.py` (прогресс **по этажам** в meta, не затирается при смене яруса)
3. ✅ Пилот **оборона лагеря** на 64 (`defense_mode: hub`, 14 волн + 3 периметра)
4. ✅ Испытания 61–63, 65–70 по JSON (hunt/search/capture/escort/rescue/ritual)
5. ✅ Города **между** ярусами: 0↔1, 30↔31, 60↔61, 90↔91 (не занимают боевые этажи)
6. ✅ Вылазки (`daily_venture_cap`, `stamina_per_venture`), счётчики целей, боссы из `boss_key`, склад материалов в `pqn:hub`
7. ✅ Авто-испытания 1–99: **~60%** уникальных вариантов (рандом), **~40%** простых
8. ✅ Залы босса на ×10: отдельный `trial_type`, слоты `ft_br*`, каталог по этажам 10–90
