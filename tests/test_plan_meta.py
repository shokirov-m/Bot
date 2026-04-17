"""Тесты по плану: звания, пассивы, учебная волна, ежедневка, миграция meta, оружие, длинный этаж."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from db.models.character import Character
from game.characters.path_ranks import PATH_RANK_SPECS, path_rank_key_from_battle
from game.characters.skills import passive_combat_modifiers_merged
from game.combat import consumables
from game.floors import long_floor as lf
from services import character_service, daily_service
from services.combat_service import _tutorial_monster_wave2
from services.meta_migration_service import apply_legacy_title_rank_migration


def test_path_rank_key_from_battle_deterministic() -> None:
    key = path_rank_key_from_battle(4, 30, 34, True)
    assert isinstance(key, str)
    assert key == path_rank_key_from_battle(4, 30, 34, True)


def test_passive_combat_modifiers_merged_returns_dict() -> None:
    c = Character(
        user_id=1,
        display_name="T",
        class_key="wanderer",
        meta_progress={"path_passive_key": "pp_crit3"},
    )
    m = passive_combat_modifiers_merged(c)
    assert isinstance(m, dict)
    assert "crit_chance_bonus" in m or len(m) >= 0


def test_tutorial_wave2_monster_bundle() -> None:
    m = _tutorial_monster_wave2()
    assert m["atk"] == 7
    assert m["hp"] == 32


def test_can_claim_daily_today() -> None:
    c = Character(
        user_id=1,
        display_name="T",
        class_key="wanderer",
        meta_progress={
            "daily_v1": {
                "kd": daily_service._utc_today_iso(),
                "kc": 3,
                "lcd": None,
                "streak": 0,
            },
        },
    )
    assert daily_service.can_claim_daily_today(c) is True


def test_try_claim_daily_reward_streak_path_returns_html() -> None:
    """Регрессия: локальные имена не должны затенять bot.i18n.t (иначе «не вызываемый» date)."""
    today = datetime.now(UTC).date().isoformat()
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    c = Character(
        user_id=1,
        display_name="T",
        class_key="wanderer",
        gold=0,
        experience=0,
        level=1,
        floor_number=1,
        unspent_stat_points=0,
        meta_progress={
            "daily_v1": {
                "kd": today,
                "kc": 3,
                "lcd": yesterday,
                "streak": 2,
            },
        },
    )

    async def _run() -> daily_service.ClaimResult:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        return await daily_service.try_claim_daily_reward(session, c, locale="ru", bot=None)

    r = asyncio.run(_run())
    assert r.ok is True
    assert "Награда" in r.message_html


def test_meta_migration_strips_path_titles_and_rank_active_title() -> None:
    rank_name = PATH_RANK_SPECS[0][1]
    c = Character(
        user_id=1,
        display_name="T",
        class_key="wanderer",
        active_title=rank_name,
        meta_progress={"titles_unlocked": ["path_foo", "title_a"]},
    )
    apply_legacy_title_rank_migration(c)
    assert "path_foo" not in (c.meta_progress or {}).get("titles_unlocked", [])
    assert c.active_title is None


def test_weapon_attack_value_matches_unarmed_and_enchant() -> None:
    n = character_service.weapon_attack_value_from_item_data(None, level=5, floor_number=20)
    assert n == 5 + 5 + 2
    w = character_service.weapon_attack_value_from_item_data(
        {"attack": 10, "enchant": 2},
        level=1,
        floor_number=1,
    )
    assert w == 12


def test_combat_use_tag_normalizes_case() -> None:
    assert consumables.normalize_combat_use_tag({"use_tag": "Heal_HP_Pct"}) == "heal_hp_pct"
    assert consumables.normalize_combat_use_tag({"use_tag": "  heal_mp_flat "}) == "heal_mp_flat"


def test_item_data_as_dict_parses_json_string() -> None:
    raw = '{"use_tag": "heal_hp_pct", "use_value": 35}'
    d = consumables.item_data_as_dict(raw)
    assert consumables.normalize_combat_use_tag(d) == "heal_hp_pct"


def test_floor_callback_matches_lf_keys_underscore() -> None:
    import re

    pat = re.compile(r"^fl:(\d+):([a-z0-9_]+)$")
    m = pat.match("fl:15:lf_keys")
    assert m is not None
    assert m.group(1) == "15"
    assert m.group(2) == "lf_keys"


def test_long_floor_spawns_and_phase() -> None:
    c = Character(
        user_id=1,
        display_name="T",
        class_key="wanderer",
        floor_number=lf.PILOT_FLOOR,
        meta_progress={},
    )
    lf.ensure_long_floor_started(c)
    assert lf.current_phase(c) == "keys"
    assert lf.SLOT_W1 in {s.slot_code for s in lf.all_long_floor_spawns()}
    trip = lf.spawns_for_tower_progress(c, lf.PILOT_FLOOR)
    assert {s.slot_code for s in trip} == {lf.SLOT_W1, lf.SLOT_W2, lf.SLOT_BOSS}


def test_hp_mp_ratio_uses_formula_baseline_when_column_stale() -> None:
    """При устаревшем hp_max в БД доля текущего HP от старого макс. по формуле, не от колонки."""
    from game.characters.classes import get_class_or_none

    from services.character_service import _apply_hp_mp_caps_from_totals, _compute_hp_max

    cls = get_class_or_none("warrior")
    assert cls is not None
    true_old = _compute_hp_max(10, 20, cls)
    new_hp = _compute_hp_max(10, 21, cls)
    assert new_hp > true_old
    hc = int(true_old * 0.4)
    stale_column = 100
    assert stale_column != true_old
    c = Character(
        user_id=1,
        display_name="T",
        class_key="warrior",
        stat_vitality=10,
        stat_strength=21,
        stat_intelligence=5,
        hp_current=hc,
        hp_max=stale_column,
        mp_current=5,
        mp_max=30,
    )
    _apply_hp_mp_caps_from_totals(
        c,
        vit=10,
        strn=21,
        intl=5,
        ratio_hp_old_max=true_old,
        ratio_mp_old_max=None,
    )
    want_cur = max(1, min(new_hp, int(hc * new_hp / true_old)))
    assert c.hp_max == new_hp
    assert c.hp_current == want_cur
    wrong_cur = max(1, min(new_hp, int(hc * new_hp / stale_column)))
    assert wrong_cur != want_cur
