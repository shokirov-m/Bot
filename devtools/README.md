# Devtools (не входит в runtime бота)

| Папка | Назначение |
|-------|------------|
| `assets/` | PNG-заглушки, junction `assets` → `content/assets`, проверка путей |
| `docs/` | Генераторы справочников → вывод в `tower_bot/docs/` |
| `db/` | Опасные операции с БД (wipe) |

## Частые команды (из `tower_bot/`)

```bash
# Junction assets (Windows)
powershell -File devtools/assets/setup_assets_link.ps1

python devtools/assets/validate_assets.py
python devtools/assets/init_game_art_placeholders.py
python devtools/docs/_gen_catalog_guides.py
python devtools/docs/gen_monster_reference_all.py
python devtools/docs/export_equipment_catalog_txt.py
python devtools/gen_room_clear_instances.py   # room_clear/instances_data.py (после правки CONFIG_*)
```
