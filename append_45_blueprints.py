# Генерация 45 _reg(...), вставка в recipes_data. Запуск: python append_45_blueprints.py
from __future__ import annotations
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent
REC = ROOT / "game" / "crafting" / "recipes_data.py"


def reg(
    rid: str,
    title: str,
    desc: str,
    prof: str,
    mp: int,
    ms: int,
    mc: int,
    craft: dict[str, int],
    sec: int,
    xp: int,
    result_lines: str,
) -> str:
    cc = ", ".join(f'"{k}": {v}' for k, v in sorted(craft.items()))
    return dedent(
        f"""
    _reg(
        {{
            "id": "{rid}",
            "name_ru": "{title}",
            "description": "{desc}",
            "profession": "{prof}",
            "min_profession_level": {mp},
            "min_station_level": {ms},
            "min_character_level": {mc},
            "cost": {{}},
            "craft_cost": {{{cc}}},
            "forge_instant": False,
            "craft_seconds": {sec},
            "xp_reward": {xp},
            "requires_blueprint": True,
            "result": {{
{result_lines}
            }},
        }},
    ),"""
    )


def main() -> None:
    BS, AL, JW = "blacksmith", "alchemist", "jeweler"
    parts: list[str] = []

    def R(**kw):
        parts.append(reg(**kw))

    # 15 кузнец
    R(rid="bp_sk_chain_hauberk", title="Чертёж: кольчужный хауберк", desc="Медь и железо.", prof=BS, mp=4, ms=1, mc=6, craft={"copper_ingot": 8, "iron_ingot": 5, "steel_ingot": 3}, sec=1200, xp=28, result_lines='                "name": "🦺 Кольчужный хауберк",\n                "kind": "armor",\n                "rarity": "uncommon",\n                "defense": 22,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_iron_gladius", title="Чертёж: железный гладиус", desc="Короткий клинок.", prof=BS, mp=3, ms=1, mc=5, craft={"iron_ingot": 7, "steel_ingot": 4}, sec=1100, xp=26, result_lines='                "name": "⚔️ Железный гладиус",\n                "kind": "weapon",\n                "rarity": "uncommon",\n                "attack": 22,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_silver_kite", title="Чертёж: серебряный щит", desc="Серебро и сталь.", prof=BS, mp=6, ms=2, mc=9, craft={"silver_ingot": 6, "hardened_steel": 4}, sec=2000, xp=44, result_lines='                "name": "🛡️ Серебряный щит",\n                "kind": "shield",\n                "rarity": "rare",\n                "defense": 35,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_dark_longsword", title="Чертёж: меч тёмной стали", desc="Тёмная сталь.", prof=BS, mp=10, ms=2, mc=12, craft={"dark_steel": 4, "mithril_ingot": 2, "dragon_bone": 1}, sec=2800, xp=58, result_lines='                "name": "⚔️ Меч тёмной стали",\n                "kind": "weapon",\n                "rarity": "epic",\n                "attack": 48,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_dragon_gorget", title="Чертёж: горжет из кости дракона", desc="Кость и обсидиан.", prof=BS, mp=11, ms=3, mc=13, craft={"dragon_bone": 4, "obsidian": 3}, sec=3200, xp=64, result_lines='                "name": "⛑️ Горжет из кости дракона",\n                "kind": "helmet",\n                "rarity": "epic",\n                "defense": 32,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_obsidian_greaves", title="Чертёж: обсидиановые поножи", desc="Вулканическое стекло.", prof=BS, mp=9, ms=2, mc=11, craft={"obsidian": 5, "hardened_steel": 3}, sec=2600, xp=52, result_lines='                "name": "👖 Обсидиановые поножи",\n                "kind": "pants",\n                "rarity": "rare",\n                "defense": 26,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_skysteel_spear", title="Чертёж: копьё небесной стали", desc="Небесное железо.", prof=BS, mp=14, ms=3, mc=16, craft={"skysteel": 3, "mithril_ingot": 3, "silver_ingot": 4}, sec=4200, xp=78, result_lines='                "name": "🔱 Копьё небесной стали",\n                "kind": "weapon",\n                "rarity": "legendary",\n                "attack": 52,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_adamant_helm", title="Чертёж: шлем из адамантия", desc="Топ металлов.", prof=BS, mp=17, ms=4, mc=17, craft={"adamantite": 2, "dragon_bone": 3, "skysteel": 2}, sec=5600, xp=92, result_lines='                "name": "⛑️ Шлем из адамантия",\n                "kind": "helmet",\n                "rarity": "legendary",\n                "defense": 38,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_titan_greataxe", title="Чертёж: секира крови титана", desc="Кровь титана.", prof=BS, mp=19, ms=4, mc=18, craft={"titan_blood": 2, "adamantite": 2, "skysteel": 2}, sec=6800, xp=105, result_lines='                "name": "🪓 Секира крови титана",\n                "kind": "weapon",\n                "rarity": "legendary",\n                "attack": 58,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_mithril_fullplate", title="Чертёж: полный латник мифрила", desc="Мифрил.", prof=BS, mp=13, ms=3, mc=15, craft={"mithril_ingot": 6, "dark_steel": 4}, sec=4800, xp=74, result_lines='                "name": "🦺 Полный латник мифрила",\n                "kind": "armor",\n                "rarity": "epic",\n                "defense": 42,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_flame_core_blade", title="Чертёж: клинок огненного ядра", desc="Кость дракона.", prof=BS, mp=12, ms=3, mc=14, craft={"dragon_bone": 3, "obsidian": 4, "mithril_ingot": 2}, sec=4000, xp=68, result_lines='                "name": "🔥 Клинок огненного ядра",\n                "kind": "weapon",\n                "rarity": "epic",\n                "attack": 46,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_storm_breaker", title="Чертёж: грозолом", desc="Небесная сталь.", prof=BS, mp=15, ms=3, mc=16, craft={"skysteel": 4, "dragon_bone": 2, "mithril_ingot": 3}, sec=4500, xp=82, result_lines='                "name": "⚔️ Грозолом",\n                "kind": "weapon",\n                "rarity": "legendary",\n                "attack": 54,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_void_edge", title="Чертёж: кромка пустоты", desc="Обсидиан.", prof=BS, mp=11, ms=3, mc=13, craft={"obsidian": 6, "dark_steel": 4}, sec=3600, xp=60, result_lines='                "name": "⚔️ Кромка пустоты",\n                "kind": "weapon",\n                "rarity": "epic",\n                "attack": 44,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_warden_gauntlets", title="Чертёж: рукавицы стража", desc="Закалённая сталь.", prof=BS, mp=7, ms=2, mc=10, craft={"hardened_steel": 5, "silver_ingot": 4}, sec=2200, xp=46, result_lines='                "name": "🧤 Рукавицы стража",\n                "kind": "gloves",\n                "rarity": "rare",\n                "defense": 16,\n                "attack": 6,\n                "summary": "Чертёж кузнеца.",')
    R(rid="bp_sk_starfall_blade", title="Чертёж: клинок звездопада", desc="Адамантий.", prof=BS, mp=20, ms=4, mc=19, craft={"adamantite": 3, "dragon_bone": 2, "titan_blood": 1}, sec=7200, xp=118, result_lines='                "name": "⚔️ Клинок звездопада",\n                "kind": "weapon",\n                "rarity": "legendary",\n                "attack": 60,\n                "summary": "Чертёж кузнеца.",')

    # 15 алхимик
    R(rid="bp_al_healing_draught", title="Чертёж: целительная настойка", desc="Травы.", prof=AL, mp=2, ms=1, mc=4, craft={"meadow_herb": 8, "blue_berry": 3}, sec=400, xp=18, result_lines='                "name": "🧪 Целительная настойка",\n                "kind": "consumable",\n                "rarity": "common",\n                "use_tag": "heal_hp_pct",\n                "use_value": 25,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_mana_star", title="Чертёж: звезда маны", desc="Пыльца.", prof=AL, mp=3, ms=1, mc=5, craft={"spirit_pollen": 5, "moss_fungus": 4}, sec=500, xp=20, result_lines='                "name": "🧪 Звезда маны",\n                "kind": "consumable",\n                "rarity": "common",\n                "use_tag": "heal_mp_pct",\n                "use_value": 20,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_mandrake_tonic", title="Чертёж: тоник мандрагоры", desc="Корень.", prof=AL, mp=5, ms=1, mc=7, craft={"mandrake_root": 5, "void_rose_thorn": 2}, sec=800, xp=28, result_lines='                "name": "🧪 Тоник мандрагоры",\n                "kind": "consumable",\n                "rarity": "uncommon",\n                "use_tag": "heal_hp_pct",\n                "use_value": 32,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_golem_elixir", title="Чертёж: эликсир голема", desc="Слеза голема.", prof=AL, mp=8, ms=2, mc=10, craft={"golem_tear": 4, "basilisk_scale": 3}, sec=1400, xp=38, result_lines='                "name": "🧪 Эликсир голема",\n                "kind": "consumable",\n                "rarity": "rare",\n                "use_tag": "heal_hp_pct",\n                "use_value": 42,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_moon_veil", title="Чертёж: покров луны", desc="Лунная пыль.", prof=AL, mp=9, ms=2, mc=11, craft={"moon_dust": 4, "spirit_pollen": 4}, sec=1600, xp=42, result_lines='                "name": "🧪 Покров луны",\n                "kind": "consumable",\n                "rarity": "rare",\n                "use_tag": "heal_mp_pct",\n                "use_value": 35,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_phoenix_breath", title="Чертёж: дыхание феникса", desc="Цветок феникса.", prof=AL, mp=11, ms=2, mc=13, craft={"phoenix_flower": 3, "blue_berry": 5, "mandrake_root": 3}, sec=2200, xp=50, result_lines='                "name": "🧪 Дыхание феникса",\n                "kind": "consumable",\n                "rarity": "epic",\n                "use_tag": "heal_hp_pct",\n                "use_value": 48,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_void_philter", title="Чертёж: фильтр бездны", desc="Эссенция бездны.", prof=AL, mp=13, ms=3, mc=14, craft={"void_essence": 2, "moon_dust": 4, "void_rose_thorn": 3}, sec=3000, xp=62, result_lines='                "name": "🧪 Фильтр бездны",\n                "kind": "consumable",\n                "rarity": "epic",\n                "use_tag": "heal_mp_pct",\n                "use_value": 42,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_basilisk_brew", title="Чертёж: отвар василиска", desc="Чешуя.", prof=AL, mp=10, ms=2, mc=12, craft={"basilisk_scale": 5, "golem_tear": 3}, sec=2000, xp=46, result_lines='                "name": "🧪 Отвар василиска",\n                "kind": "consumable",\n                "rarity": "rare",\n                "use_tag": "heal_hp_pct",\n                "use_value": 45,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_starlight_serum", title="Чертёж: сыворотка звездного света", desc="Лунная пыль.", prof=AL, mp=12, ms=3, mc=14, craft={"moon_dust": 5, "phoenix_flower": 2, "void_rose_thorn": 3}, sec=2800, xp=58, result_lines='                "name": "🧪 Сыворотка звездного света",\n                "kind": "consumable",\n                "rarity": "epic",\n                "use_tag": "heal_hp_pct",\n                "use_value": 52,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_golden_dawn", title="Чертёж: золотой рассвет", desc="Золотое яблоко.", prof=AL, mp=18, ms=4, mc=17, craft={"golden_apple": 1, "void_essence": 3, "phoenix_flower": 2}, sec=6000, xp=95, result_lines='                "name": "🧪 Золотой рассвет",\n                "kind": "consumable",\n                "rarity": "legendary",\n                "use_tag": "heal_hp_pct",\n                "use_value": 75,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_nether_sips", title="Чертёж: глотки Нижнего мира", desc="Мох и роза.", prof=AL, mp=4, ms=1, mc=6, craft={"moss_fungus": 6, "meadow_herb": 5, "void_rose_thorn": 1}, sec=700, xp=24, result_lines='                "name": "🧪 Глотки Нижнего мира",\n                "kind": "consumable",\n                "rarity": "uncommon",\n                "use_tag": "heal_mp_pct",\n                "use_value": 22,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_abyss_ink", title="Чертёж: чернила Бездны", desc="Смола на броню.", prof=AL, mp=7, ms=2, mc=9, craft={"void_rose_thorn": 4, "basilisk_scale": 2, "mandrake_root": 3}, sec=1300, xp=36, result_lines='                "name": "🧪 Чернила Бездны",\n                "kind": "consumable",\n                "rarity": "rare",\n                "use_tag": "workshop_alchemy_enchant",\n                "alchemy_enchant_armor": True,\n                "add_fire_resist_pct": 8,\n                "enchant_label_ru": "Бездна I",\n                "summary": "Чертёж: смола на броню.",')
    R(rid="bp_al_sun_tears", title="Чертёж: слёзы солнца", desc="Золотое яблоко.", prof=AL, mp=20, ms=4, mc=18, craft={"golden_apple": 2, "void_essence": 2, "moon_dust": 5}, sec=6400, xp=102, result_lines='                "name": "🧪 Слёзы солнца",\n                "kind": "consumable",\n                "rarity": "legendary",\n                "use_tag": "heal_hp_pct",\n                "use_value": 80,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_witch_honey", title="Чертёж: мёд ведьмы", desc="Травы.", prof=AL, mp=6, ms=1, mc=8, craft={"meadow_herb": 6, "mandrake_root": 4, "spirit_pollen": 3}, sec=1100, xp=32, result_lines='                "name": "🧪 Мёд ведьмы",\n                "kind": "consumable",\n                "rarity": "uncommon",\n                "use_tag": "heal_hp_pct",\n                "use_value": 36,\n                "summary": "Чертёж алхимика.",')
    R(rid="bp_al_oracle_tea", title="Чертёж: чай оракула", desc="Лунная пыль.", prof=AL, mp=15, ms=3, mc=15, craft={"moon_dust": 4, "basilisk_scale": 3, "void_essence": 1}, sec=3400, xp=70, result_lines='                "name": "🧪 Чай оракула",\n                "kind": "consumable",\n                "rarity": "epic",\n                "use_tag": "heal_mp_pct",\n                "use_value": 38,\n                "summary": "Чертёж алхимика.",')

    # 15 ювелир
    R(rid="bp_jw_pearl_ring", title="Чертёж: перстень речной жемчужины", desc="Жемчужина.", prof=JW, mp=2, ms=1, mc=3, craft={"river_pearl": 5, "copper_dust": 4}, sec=500, xp=16, result_lines='                "name": "💍 Перстень речной жемчужины",\n                "kind": "ring",\n                "rarity": "common",\n                "defense": 4,\n                "int": 3,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_tiger_amulet", title="Чертёж: амулет тигрового глаза", desc="Тигровый глаз.", prof=JW, mp=4, ms=1, mc=6, craft={"tiger_eye": 5, "amber": 4}, sec=900, xp=24, result_lines='                "name": "📿 Амулет тигрового глаза",\n                "kind": "amulet",\n                "rarity": "uncommon",\n                "defense": 14,\n                "dex": 5,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_moon_band", title="Чертёж: лунное кольцо", desc="Лунный камень.", prof=JW, mp=5, ms=1, mc=7, craft={"moonstone": 5, "river_pearl": 3}, sec=1000, xp=28, result_lines='                "name": "💍 Лунное кольцо",\n                "kind": "ring",\n                "rarity": "uncommon",\n                "defense": 8,\n                "int": 7,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_ruby_signet", title="Чертёж: кровавая печать", desc="Рубин.", prof=JW, mp=7, ms=2, mc=9, craft={"blood_ruby": 4, "copper_dust": 5}, sec=1600, xp=38, result_lines='                "name": "💍 Кровавая печать",\n                "kind": "ring",\n                "rarity": "rare",\n                "defense": 12,\n                "str": 6,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_storm_pendant", title="Чертёж: медальон бури", desc="Сапфир бури.", prof=JW, mp=9, ms=2, mc=11, craft={"storm_sapphire": 4, "moonstone": 3}, sec=2100, xp=46, result_lines='                "name": "📿 Медальон бури",\n                "kind": "amulet",\n                "rarity": "rare",\n                "defense": 18,\n                "int": 8,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_life_circle", title="Чертёж: кольцо жизни", desc="Изумруд.", prof=JW, mp=8, ms=2, mc=10, craft={"life_emerald": 4, "amber": 4}, sec=1900, xp=44, result_lines='                "name": "💍 Кольцо жизни",\n                "kind": "ring",\n                "rarity": "rare",\n                "defense": 11,\n                "vit": 10,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_black_opal_orb", title="Чертёж: сфера чёрного опала", desc="Чёрный опал.", prof=JW, mp=12, ms=3, mc=13, craft={"black_opal": 5, "tiger_eye": 4}, sec=2800, xp=56, result_lines='                "name": "🔮 Сфера чёрного опала",\n                "kind": "ring",\n                "rarity": "epic",\n                "defense": 16,\n                "int": 12,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_void_diadem", title="Чертёж: диадема пустоты", desc="Алмаз пустоты.", prof=JW, mp=14, ms=3, mc=15, craft={"void_diamond": 4, "black_opal": 3}, sec=3600, xp=66, result_lines='                "name": "📿 Диадема пустоты",\n                "kind": "amulet",\n                "rarity": "epic",\n                "defense": 22,\n                "dex": 10,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_cyclops_band", title="Чертёж: кольцо ока циклопа", desc="Глаз циклопа.", prof=JW, mp=16, ms=3, mc=16, craft={"cyclops_eye": 2, "storm_sapphire": 4, "life_emerald": 3}, sec=4200, xp=76, result_lines='                "name": "💍 Кольцо ока циклопа",\n                "kind": "ring",\n                "rarity": "legendary",\n                "defense": 18,\n                "int": 14,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_starheart_locket", title="Чертёж: медальон сердца звезды", desc="Сердце звезды.", prof=JW, mp=19, ms=4, mc=18, craft={"star_heart": 1, "void_diamond": 3, "cyclops_eye": 1}, sec=6200, xp=98, result_lines='                "name": "📿 Медальон сердца звезды",\n                "kind": "amulet",\n                "rarity": "legendary",\n                "defense": 26,\n                "vit": 14,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_amber_weave", title="Чертёж: янтарное переплетение", desc="Янтарь.", prof=JW, mp=6, ms=1, mc=8, craft={"amber": 6, "tiger_eye": 5}, sec=1200, xp=30, result_lines='                "name": "💍 Янтарное переплетение",\n                "kind": "ring",\n                "rarity": "uncommon",\n                "defense": 9,\n                "dex": 7,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_crimson_loop", title="Чертёж: багряная петля", desc="Рубин и сапфир.", prof=JW, mp=11, ms=2, mc=12, craft={"blood_ruby": 3, "storm_sapphire": 3, "moonstone": 3}, sec=2400, xp=50, result_lines='                "name": "💍 Багряная петля",\n                "kind": "ring",\n                "rarity": "epic",\n                "defense": 14,\n                "str": 10,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_emerald_gaze", title="Чертёж: изумрудный взгляд", desc="Изумруд.", prof=JW, mp=10, ms=2, mc=12, craft={"life_emerald": 5, "river_pearl": 4}, sec=2300, xp=48, result_lines='                "name": "📿 Изумрудный взгляд",\n                "kind": "amulet",\n                "rarity": "rare",\n                "defense": 20,\n                "vit": 12,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_copper_coronet", title="Чертёж: медная диадема", desc="Медная крошка.", prof=JW, mp=3, ms=1, mc=5, craft={"copper_dust": 10, "river_pearl": 4}, sec=700, xp=22, result_lines='                "name": "📿 Медная диадема",\n                "kind": "amulet",\n                "rarity": "common",\n                "defense": 11,\n                "summary": "Чертёж ювелира.",')
    R(rid="bp_jw_opal_chain", title="Чертёж: цепь опалов", desc="Чёрный опал.", prof=JW, mp=13, ms=3, mc=14, craft={"black_opal": 4, "moonstone": 4, "amber": 3}, sec=3200, xp=60, result_lines='                "name": "📿 Цепь опалов",\n                "kind": "amulet",\n                "rarity": "epic",\n                "defense": 24,\n                "int": 11,\n                "summary": "Чертёж ювелира.",')

    assert len(parts) == 45, len(parts)
    blob = "\n".join(parts)
    t = REC.read_text(encoding="utf-8")
    m = "\n]\n\nRECIPES: tuple[dict[str, Any], ...] = tuple(_RECIPES_LIST)"
    i = t.rfind(m)
    if i < 0:
        raise SystemExit("marker")
    rest = t[i + len(m) :]
    t = t[:i] + "\n" + blob + m + rest
    REC.write_text(t, encoding="utf-8")
    print("inserted 45 blueprints")


if __name__ == "__main__":
    main()
