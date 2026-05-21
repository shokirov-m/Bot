"""
Испытание этажа (пак зоны): угодья, прогресс %, сброс при смерти.

meta_progress[floor_trial_v1] = {
  "floor": 64,
  "zone_key": "blood_spire",
  "trial_type": "defense",
  "progress_pct": 40,
  "checkpoint_pct": 0,
  "grounds_cleared": ["ft_g00", "ft_g01"],
  "grounds_open": ["ft_g00", ..],
  "ground_progress": {"ft_g00": {"wins": 4}},
  "current_ground": "ft_g02",
  "waves_done": 3,
  "deaths": 1,
  "completed": false,
}
"""

from __future__ import annotations

import html
from typing import Any

from db.models.character import Character
from game.enemies.floors.spawns import (
    FloorMonsterSpawn,
    MonsterTemplate,
    floor_spawn_indices,
    zone_monster_templates,
)
from game.tower.progression import floor_data
from game.tower.trials.pack_config import get_trial_config
from game.tower.trials.pack_monsters import (
    NAMED_ELITE_KEYS,
    is_named_elite_key,
    template_from_key,
)
from game.tower.trials import venture as trial_venture_mod

META_KEY = "floor_trial_v1"
_GROUND_LABEL: dict[str, str] = {
    "hunt": "🎯",
    "search": "🔍",
    "rescue": "⛓️",
    "capture": "📍",
    "escort": "🛡️",
    "ritual": "🕯️",
    "defense": "🚧",
}
SLOT_BOSS = "ft_boss"
SLOT_DEFENSE = "ft_def"
SLOT_PREFIX = "ft_g"
SLOT_CHAMBER_PREFIX = "ft_br"


def _slot_for_index(i: int) -> str:
    return f"{SLOT_PREFIX}{i:02d}"


def is_boss_chamber_trial(cfg: dict[str, Any] | None = None, floor: int | None = None) -> bool:
    c = cfg if cfg is not None else _cfg_for_floor(int(floor or 0))
    return str(c.get("trial_type") or "") == "boss_chamber"


def _chamber_slots(cfg: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for row in cfg.get("chambers") or []:
        if isinstance(row, dict) and row.get("slot"):
            out.append(str(row["slot"]))
    return out


def _trial_meta(character: Character) -> dict[str, Any] | None:
    raw = character.meta_progress or {}
    st = raw.get(META_KEY)
    return dict(st) if isinstance(st, dict) else None


def _save_meta(character: Character, st: dict[str, Any]) -> None:
    meta = dict(character.meta_progress or {})
    meta[META_KEY] = st
    character.meta_progress = meta


def _cfg_for_floor(floor: int) -> dict[str, Any]:
    return get_trial_config(int(floor))


def has_trial_on_floor(floor: int) -> bool:
    from game.tower.trials.default_config import is_trial_eligible_floor

    if not is_trial_eligible_floor(int(floor)):
        return False
    cfg = _cfg_for_floor(int(floor))
    if not cfg.get("trial_type"):
        return False
    if is_defense_hub(cfg):
        return int(_waves_total(cfg)) > 0
    return int(cfg.get("grounds_count") or 0) > 0


def is_defense_hub(cfg: dict[str, Any] | None = None, floor: int | None = None) -> bool:
    c = cfg if cfg is not None else _cfg_for_floor(int(floor or 0))
    return str(c.get("trial_type") or "") == "defense" and str(c.get("defense_mode") or "") == "hub"


def _waves_total(cfg: dict[str, Any]) -> int:
    targets = cfg.get("targets") or {}
    if isinstance(targets, dict) and targets.get("waves"):
        return max(1, int(targets["waves"]))
    return max(1, int(cfg.get("waves_total") or 14))


def _waves_loss_on_death(cfg: dict[str, Any]) -> int:
    return max(0, int(cfg.get("waves_loss_on_death") or 2))


def _checkpoint_every_waves(cfg: dict[str, Any]) -> int:
    return max(1, int(cfg.get("checkpoint_every_waves") or cfg.get("checkpoint_every_grounds") or 4))


def is_defense_hub_character(character: Character) -> bool:
    return is_defense_hub(floor=int(character.floor_number))


def is_trial_floor(floor: int) -> bool:
    return has_trial_on_floor(int(floor))


def is_trial_active(character: Character) -> bool:
    fl = int(character.floor_number)
    if not is_trial_floor(fl):
        return False
    st = _trial_meta(character)
    if st is None:
        return True
    if int(st.get("floor", -1)) != fl:
        return True
    return not bool(st.get("completed"))


def is_trial_scenario_active(character: Character) -> bool:
    """Скрыть обычные спавны этажа — только угодья испытания."""
    return is_trial_active(character)


def _grounds_total(cfg: dict[str, Any]) -> int:
    return max(1, int(cfg.get("grounds_count") or 12))


def _wins_per_ground(cfg: dict[str, Any]) -> int:
    return max(1, int(cfg.get("wins_per_ground") or 4))


def _initial_open_count(cfg: dict[str, Any]) -> int:
    total = _grounds_total(cfg)
    initial = int(cfg.get("grounds_visible_initial") or 6)
    return min(total, max(1, initial))


def _required_pct(cfg: dict[str, Any]) -> int:
    return min(100, max(50, int(cfg.get("required_progress_pct") or 90)))


def ensure_started(character: Character) -> None:
    fl = int(character.floor_number)
    if not is_trial_floor(fl):
        return
    cfg = _cfg_for_floor(fl)
    zone = floor_data.get_zone_for_floor(fl)
    st = _trial_meta(character)
    if st is not None and int(st.get("floor", -1)) == fl and "grounds_open" in st:
        return
    total = _grounds_total(cfg)
    if is_boss_chamber_trial(cfg):
        grounds_open = _chamber_slots(cfg) or [_slot_for_index(i) for i in range(total)]
    elif is_defense_hub(cfg):
        grounds_open = [_slot_for_index(i) for i in range(total)]
    else:
        open_n = _initial_open_count(cfg)
        grounds_open = [_slot_for_index(i) for i in range(open_n)]
    fresh: dict[str, Any] = {
        "floor": fl,
        "zone_key": zone.key,
        "trial_type": str(cfg.get("trial_type") or "hunt"),
        "trial_title_ru": str(cfg.get("trial_title_ru") or ""),
        "variant_id": str(cfg.get("variant_id") or ""),
        "defense_mode": str(cfg.get("defense_mode") or ""),
        "progress_pct": 0,
        "checkpoint_pct": 0,
        "checkpoint_grounds": [],
        "checkpoint_waves": 0,
        "grounds_cleared": [],
        "grounds_open": grounds_open,
        "ground_progress": {},
        "current_ground": None,
        "waves_done": 0,
        "deaths": 0,
        "completed": False,
        "stats": {"fights": 0, "elites": 0, "named": 0},
    }
    _save_meta(character, fresh)


def _trial_stats(st: dict[str, Any]) -> dict[str, int]:
    raw = st.get("stats") or {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "fights": max(0, int(raw.get("fights") or 0)),
        "elites": max(0, int(raw.get("elites") or 0)),
        "named": max(0, int(raw.get("named") or 0)),
    }


def _bump_stats(st: dict[str, Any], *, is_elite: bool, is_named: bool) -> None:
    stats = _trial_stats(st)
    stats["fights"] += 1
    if is_elite:
        stats["elites"] += 1
    if is_named:
        stats["named"] += 1
    st["stats"] = stats


def _targets_block(cfg: dict[str, Any], st: dict[str, Any]) -> str:
    targets = cfg.get("targets")
    if not isinstance(targets, dict) or not targets:
        return ""
    stats = _trial_stats(st)
    bits: list[str] = []
    for key, label in (
        ("fights", "бои"),
        ("elites", "элиты"),
        ("named", "именные"),
        ("named_elites", "именные"),
        ("clues", "улики"),
        ("contracts", "контракты"),
        ("trophies", "трофеи"),
        ("nodes", "узлы"),
        ("prisoners", "пленные"),
        ("camps", "лагеря"),
        ("waves", "волны"),
        ("chambers", "залы"),
        ("guardians", "стражи"),
    ):
        need = int(targets.get(key) or 0)
        if need <= 0:
            continue
        cur_key = "named" if key == "named_elites" else key
        cur = stats.get(cur_key, 0) if cur_key in stats else 0
        if key in ("clues", "contracts", "nodes"):
            cur = min(cur, stats["fights"])
        bits.append(f"{label} {cur}/{need}")
    if not bits:
        return ""
    return "Цели: " + " · ".join(bits[:4])


def progress_percent(character: Character) -> int:
    st = _trial_meta(character)
    if st is None:
        return 0
    return min(100, max(0, int(st.get("progress_pct") or 0)))


def _calc_progress(st: dict[str, Any], cfg: dict[str, Any]) -> int:
    if is_defense_hub(cfg):
        wt = _waves_total(cfg)
        wdone = int(st.get("waves_done") or 0)
        wave_part = int(min(70, wdone / wt * 70)) if wt else 0
        gt = _grounds_total(cfg)
        gc = len(st.get("grounds_cleared") or [])
        ground_part = int(min(30, gc / gt * 30)) if gt else 0
        return min(99 if not st.get("completed") else 100, wave_part + ground_part)
    total = _grounds_total(cfg)
    cleared = len(st.get("grounds_cleared") or [])
    return min(99 if not st.get("completed") else 100, int(cleared / total * 100) if total else 0)


def _maybe_checkpoint(st: dict[str, Any], cfg: dict[str, Any]) -> None:
    if is_defense_hub(cfg):
        every = _checkpoint_every_waves(cfg)
        wd = int(st.get("waves_done") or 0)
        if wd > 0 and wd % every == 0:
            st["checkpoint_waves"] = wd
            st["checkpoint_pct"] = int(st.get("progress_pct") or 0)
            st["checkpoint_grounds"] = list(st.get("grounds_cleared") or [])
        return
    every = int(cfg.get("checkpoint_every_grounds") or 3)
    cleared = st.get("grounds_cleared") or []
    if len(cleared) > 0 and len(cleared) % every == 0:
        st["checkpoint_pct"] = int(st.get("progress_pct") or 0)
        st["checkpoint_grounds"] = list(cleared)


def _open_next_ground(st: dict[str, Any], cfg: dict[str, Any]) -> None:
    total = _grounds_total(cfg)
    open_list = list(st.get("grounds_open") or [])
    if len(open_list) >= total:
        return
    next_i = len(open_list)
    nxt = _slot_for_index(next_i)
    if nxt not in open_list:
        open_list.append(nxt)
    st["grounds_open"] = open_list


def is_boss_unlocked(character: Character) -> bool:
    st = _trial_meta(character)
    if st is None:
        return False
    cfg = _cfg_for_floor(int(character.floor_number))
    if is_defense_hub(cfg):
        return (
            int(st.get("waves_done") or 0) >= _waves_total(cfg)
            and progress_percent(character) >= _required_pct(cfg)
        )
    return progress_percent(character) >= _required_pct(cfg)


def defense_waves_complete(character: Character) -> bool:
    cfg = _cfg_for_floor(int(character.floor_number))
    st = _trial_meta(character) or {}
    return int(st.get("waves_done") or 0) >= _waves_total(cfg)


def trial_ready_for_ascent(character: Character, cleared_slots: frozenset[str] | set[str]) -> bool:
    """Все условия испытания для кнопки подъёма."""
    cfg = _cfg_for_floor(int(character.floor_number))
    st = _trial_meta(character) or {}
    if bool(st.get("completed")):
        return SLOT_BOSS in cleared_slots
    if is_defense_hub(cfg):
        need_g = {_slot_for_index(i) for i in range(_grounds_total(cfg))}
        cleared_g = set(st.get("grounds_cleared") or [])
        return (
            defense_waves_complete(character)
            and need_g.issubset(cleared_g)
            and SLOT_BOSS in cleared_slots
        )
    if is_boss_chamber_trial(cfg):
        need_g = set(_chamber_slots(cfg))
        cleared_g = set(st.get("grounds_cleared") or [])
        return need_g.issubset(cleared_g) and SLOT_BOSS in cleared_slots
    need_g = {_slot_for_index(i) for i in range(_grounds_total(cfg))}
    cleared_g = set(st.get("grounds_cleared") or [])
    return need_g.issubset(cleared_g) and SLOT_BOSS in cleared_slots


def mark_completed(character: Character) -> None:
    st = dict(_trial_meta(character) or {})
    st["completed"] = True
    st["progress_pct"] = 100
    _save_meta(character, st)
    try:
        import services.progression.class_mentor_quest_service as mentor_quest_mod

        mentor_quest_mod.record_trial_completed(character)
    except Exception:
        pass


def _wins_for_slot(cfg: dict[str, Any], slot_code: str) -> int:
    if is_boss_chamber_trial(cfg):
        from game.tower.trials.boss_chambers import chamber_for_slot

        row = chamber_for_slot(cfg, slot_code)
        if row:
            return max(1, int(row.get("wins_need") or _wins_per_ground(cfg)))
    return _wins_per_ground(cfg)


def _spawn_for_chamber(
    floor: int,
    chamber_slot: str,
    *,
    wins: int,
    wins_need: int,
    cleared: bool,
    cfg: dict[str, Any],
) -> FloorMonsterSpawn:
    from game.tower.trials.boss_chambers import chamber_for_slot

    row = chamber_for_slot(cfg, chamber_slot) or {}
    zone = floor_data.get_zone_for_floor(floor)
    pool = zone_monster_templates(zone.key) or zone_monster_templates("blood_spire")
    idx = int(str(chamber_slot).replace(SLOT_CHAMBER_PREFIX, "") or 0)
    pi = floor_spawn_indices(floor + idx * 11, 1)[0] % max(1, len(pool))
    pick = pool[pi]
    is_elite = bool(row.get("is_elite")) or bool(row.get("is_guardian"))
    is_guardian = bool(row.get("is_guardian"))
    name_ru = str(row.get("name_ru") or f"Зал {idx + 1}")
    emoji = str(row.get("emoji") or "🏛️")
    prefix = "🛡️" if is_guardian else "🚪"
    prog = f" {wins}/{wins_need}" if not cleared else ""
    label = f"{prefix} {name_ru}{prog}"
    tpl = MonsterTemplate(
        pick.key,
        label[:36],
        emoji,
        pick.element,
        str(row.get("blurb_ru") or pick.blurb),
    )
    return FloorMonsterSpawn(
        slot_code=chamber_slot,
        template=tpl,
        is_elite=is_elite,
        is_mini_boss=False,
        is_major_boss=False,
    )


def _spawn_for_ground(
    floor: int,
    ground_slot: str,
    *,
    wins: int,
    wins_need: int,
    cleared: bool,
    cfg: dict[str, Any] | None = None,
) -> FloorMonsterSpawn:
    cfg = cfg or _cfg_for_floor(floor)
    zone = floor_data.get_zone_for_floor(floor)
    pool = zone_monster_templates(zone.key)
    if not pool:
        pool = zone_monster_templates("blood_spire")
    idx = int(ground_slot.replace(SLOT_PREFIX, "") or 0)
    targets = cfg.get("targets") or {}
    want_named = int(targets.get("named") or targets.get("named_elites") or 0) > 0
    pick: MonsterTemplate | None = None
    is_named = False
    if want_named and idx % 4 == 1:
        nkey = NAMED_ELITE_KEYS[idx % len(NAMED_ELITE_KEYS)]
        pick = template_from_key(nkey)
        is_named = pick is not None
    if pick is None:
        pick = pool[floor_spawn_indices(floor, 1)[0] % len(pool)] if pool else MonsterTemplate(
            "vamp_ghoul", "Гуль", "🧟", "dark", ""
        )
        if len(pool) > 1:
            pi = floor_spawn_indices(floor + idx, 1)[0] % len(pool)
            pick = pool[pi]
    is_elite = is_named or (idx % 3 == 2) or wins >= wins_need - 1
    ttype = str(cfg.get("trial_type") or "")
    prefix = str(cfg.get("ground_prefix") or _GROUND_LABEL.get(ttype, "⚔️"))
    ep = floor_data.epithet_for_floor(zone, floor + idx)
    short = ep if len(ep) <= 12 else ep[:10] + "…"
    if is_named:
        short = pick.name[:12]
    prog = f" {wins}/{wins_need}" if not cleared else ""
    tpl_name = f"{prefix} {short}{prog}"
    return FloorMonsterSpawn(
        slot_code=ground_slot,
        template=MonsterTemplate(pick.key, tpl_name.strip(), pick.emoji, pick.element, pick.blurb),
        is_elite=is_elite,
        is_mini_boss=False,
        is_major_boss=False,
    )


def _boss_spawn(floor: int, cfg: dict[str, Any] | None = None) -> FloorMonsterSpawn:
    from game.enemies.floors.spawns import major_boss_for_zone

    cfg = cfg or _cfg_for_floor(floor)
    boss_key = str(cfg.get("boss_key") or "").strip()
    tpl = template_from_key(boss_key) if boss_key else None
    is_mini = boss_key.startswith("mini_")
    if tpl is None:
        zone = floor_data.get_zone_for_floor(floor)
        tpl = major_boss_for_zone(zone, floor)
        is_mini = False
    return FloorMonsterSpawn(
        slot_code=SLOT_BOSS,
        template=tpl,
        is_elite=False,
        is_mini_boss=is_mini,
        is_major_boss=not is_mini,
    )


def _defense_wave_spawn(floor: int, wave_num: int, total: int) -> FloorMonsterSpawn:
    """Текущая волна обороны лагеря (1..total)."""
    zone = floor_data.get_zone_for_floor(floor)
    pool = zone_monster_templates(zone.key) or zone_monster_templates("blood_spire")
    pi = floor_spawn_indices(floor + wave_num * 7, 1)[0] % max(1, len(pool))
    pick = pool[pi]
    is_mini = wave_num in (7, total) and total >= 7
    is_elite = not is_mini and (wave_num % 2 == 0 or wave_num >= 5)
    labels = (
        "Осада лагеря",
        "Штурм стен",
        "Крылатая волна",
        "Гульи в тумане",
        "Алхимик штурма",
    )
    title = labels[(wave_num - 1) % len(labels)]
    name = f"🛡️ {title} ({wave_num}/{total})"
    tpl = MonsterTemplate(pick.key, name, pick.emoji, pick.element, pick.blurb)
    return FloorMonsterSpawn(
        slot_code=SLOT_DEFENSE,
        template=tpl,
        is_elite=is_elite,
        is_mini_boss=is_mini,
        is_major_boss=False,
    )


def build_trial_spawns(character: Character) -> list[FloorMonsterSpawn]:
    fl = int(character.floor_number)
    cfg = _cfg_for_floor(fl)
    ensure_started(character)
    st = _trial_meta(character) or {}
    cleared_set = set(st.get("grounds_cleared") or [])
    spawns: list[FloorMonsterSpawn] = []

    if is_defense_hub(cfg):
        wt = _waves_total(cfg)
        wd = int(st.get("waves_done") or 0)
        if wd < wt:
            spawns.append(_defense_wave_spawn(fl, wd + 1, wt))
        wins_need = _wins_per_ground(cfg)
        gp = dict(st.get("ground_progress") or {})
        for gslot in st.get("grounds_open") or []:
            row = dict(gp.get(gslot) or {"wins": 0})
            wins = int(row.get("wins") or 0)
            spawns.append(
                _spawn_for_ground(
                    fl,
                    str(gslot),
                    wins=wins,
                    wins_need=wins_need,
                    cleared=gslot in cleared_set,
                    cfg=cfg,
                ),
            )
        if is_boss_unlocked(character) and SLOT_BOSS not in cleared_set:
            spawns.append(_boss_spawn(fl, cfg))
        return spawns

    if is_boss_chamber_trial(cfg):
        gp = dict(st.get("ground_progress") or {})
        for gslot in st.get("grounds_open") or []:
            gslot = str(gslot)
            row = dict(gp.get(gslot) or {"wins": 0})
            wins = int(row.get("wins") or 0)
            wneed = _wins_for_slot(cfg, gslot)
            spawns.append(
                _spawn_for_chamber(
                    fl,
                    gslot,
                    wins=wins,
                    wins_need=wneed,
                    cleared=gslot in cleared_set,
                    cfg=cfg,
                ),
            )
        if is_boss_unlocked(character) and SLOT_BOSS not in cleared_set:
            spawns.append(_boss_spawn(fl, cfg))
        return spawns

    wins_need = _wins_per_ground(cfg)
    gp = dict(st.get("ground_progress") or {})
    for gslot in st.get("grounds_open") or []:
        row = dict(gp.get(gslot) or {"wins": 0})
        wins = int(row.get("wins") or 0)
        spawns.append(
            _spawn_for_ground(
                fl,
                str(gslot),
                wins=wins,
                wins_need=wins_need,
                cleared=gslot in cleared_set,
                cfg=cfg,
            ),
        )
    if is_boss_unlocked(character) and SLOT_BOSS not in cleared_set:
        spawns.append(_boss_spawn(fl, cfg))
    return spawns


def spawn_by_slot(character: Character, slot: str) -> FloorMonsterSpawn | None:
    for s in build_trial_spawns(character):
        if s.slot_code == slot:
            return s
    return None


def all_trial_slot_codes(character: Character) -> frozenset[str]:
    return frozenset(s.slot_code for s in build_trial_spawns(character))


def record_victory(
    character: Character,
    slot_code: str,
    *,
    spawn: FloorMonsterSpawn | None = None,
) -> str:
    if not is_trial_slot(slot_code):
        return ""
    fl = int(character.floor_number)
    cfg = _cfg_for_floor(fl)
    ensure_started(character)
    st = dict(_trial_meta(character) or {})
    is_elite = bool(getattr(spawn, "is_elite", False)) if spawn else False
    tpl_key = str(getattr(getattr(spawn, "template", None), "key", "") or "")
    is_named = is_named_elite_key(tpl_key)

    if slot_code == SLOT_BOSS:
        _bump_stats(st, is_elite=True, is_named=is_named)
        _save_meta(character, st)
        mark_completed(character)
        return "\n🏆 <b>Испытание этажа завершено!</b> Можно подниматься выше."

    if slot_code == SLOT_DEFENSE and is_defense_hub(cfg):
        _bump_stats(st, is_elite=is_elite, is_named=is_named)
        st["waves_done"] = int(st.get("waves_done") or 0) + 1
        st["current_ground"] = SLOT_DEFENSE
        st["progress_pct"] = _calc_progress(st, cfg)
        _maybe_checkpoint(st, cfg)
        _save_meta(character, st)
        wd = int(st["waves_done"])
        wt = _waves_total(cfg)
        note = f"\n🛡️ <b>Волна {wd}/{wt} отбита!</b>"
        if wd >= wt:
            note += "\n✅ Все волны отбиты — зачисти периметр и открой босса."
        elif wd % _checkpoint_every_waves(cfg) == 0:
            note += "\n🏕️ <b>Чекпоинт обороны</b> сохранён."
        return note

    _bump_stats(st, is_elite=is_elite, is_named=is_named)
    wins_need = _wins_for_slot(cfg, slot_code)
    gp = dict(st.get("ground_progress") or {})
    row = dict(gp.get(slot_code) or {"wins": 0})
    row["wins"] = int(row.get("wins") or 0) + 1
    st["current_ground"] = slot_code
    note = ""
    cleared = list(st.get("grounds_cleared") or [])
    if row["wins"] >= wins_need and slot_code not in cleared:
        cleared.append(slot_code)
        st["grounds_cleared"] = cleared
        if not is_boss_chamber_trial(cfg):
            _open_next_ground(st, cfg)
        _maybe_checkpoint(st, cfg)
        if is_boss_chamber_trial(cfg):
            from game.tower.trials.boss_chambers import chamber_for_slot

            ch = chamber_for_slot(cfg, slot_code) or {}
            cname = str(ch.get("name_ru") or "зал")
            note = f"\n✅ Зал «{cname}» зачищен ({len(cleared)}/{_grounds_total(cfg)})."
        else:
            note = f"\n✅ Угодье зачищено ({len(cleared)}/{_grounds_total(cfg)})."
    gp[slot_code] = row
    st["ground_progress"] = gp
    st["progress_pct"] = _calc_progress(st, cfg)
    _save_meta(character, st)
    return note


def apply_death_penalty(character: Character) -> str:
    if not is_trial_active(character):
        return ""
    fl = int(character.floor_number)
    cfg = _cfg_for_floor(fl)
    st = dict(_trial_meta(character) or {})
    mode = str(cfg.get("death_reset") or "phase")
    lines: list[str] = []
    progress = int(st.get("progress_pct") or 0)
    checkpoint = int(st.get("checkpoint_pct") or 0)

    cg = st.get("current_ground")
    if cg and cg != SLOT_DEFENSE:
        gp = dict(st.get("ground_progress") or {})
        gp[str(cg)] = {"wins": 0}
        st["ground_progress"] = gp

    if is_defense_hub(cfg):
        loss = _waves_loss_on_death(cfg)
        cw = int(st.get("checkpoint_waves") or 0)
        wd = int(st.get("waves_done") or 0)
        st["waves_done"] = max(cw, wd - loss)
        lines.append(f"Оборона: <b>−{loss}</b> волны (сейчас {st['waves_done']}/{_waves_total(cfg)}).")
        if cg == SLOT_DEFENSE:
            lines.append("Текущая волна начнётся заново.")
        st["grounds_cleared"] = []
        st["ground_progress"] = {}
        lines.append("Периметр сброшен — зачисти сектора заново.")

    if mode == "full_trial":
        st["grounds_cleared"] = list(st.get("checkpoint_grounds") or [])
        st["ground_progress"] = {}
        progress = checkpoint
        lines.append("Испытание этажа откатилось к чекпоинту.")
    else:
        progress = max(checkpoint, progress - 15)
        lines.append("Фаза текущего угодья сброшена.")
        if progress < int(st.get("progress_pct") or 0):
            lines.append(f"Прогресс испытания: <b>{progress}%</b> (не ниже чекпоинта {checkpoint}%).")

    st["progress_pct"] = progress
    st["deaths"] = int(st.get("deaths") or 0) + 1
    st["current_ground"] = None
    _save_meta(character, st)
    return "\n".join(lines)


def format_banner_html(character: Character) -> str:
    if not is_trial_active(character):
        return ""
    fl = int(character.floor_number)
    cfg = _cfg_for_floor(fl)
    st = _trial_meta(character) or {}
    ttype = str(st.get("trial_type") or cfg.get("trial_type") or "trial")
    from game.tower.trials.default_config import trial_type_label_ru

    name = trial_type_label_ru(ttype, cfg)
    variant_note = ""
    vid = str(cfg.get("variant_id") or st.get("variant_id") or "")
    if vid and not vid.startswith("simple_"):
        variant_note = f" <i>({html.escape(vid)})</i>"
    pct = progress_percent(character)
    cleared = len(st.get("grounds_cleared") or [])
    total = _grounds_total(cfg)
    req = _required_pct(cfg)
    boss = "открыт" if is_boss_unlocked(character) else f"с {req}%"
    hard = " · <i>хардкор</i>" if cfg.get("hardcore") else ""
    deaths = int(st.get("deaths") or 0)
    dline = f" · смертей: <b>{deaths}</b>" if deaths else ""
    tgt = _targets_block(cfg, st)
    vline = trial_venture_mod.format_venture_line_html(character)
    extra = ""
    if tgt:
        extra += f"\n<i>{html.escape(tgt)}</i>"
    if vline:
        extra += f"\n<i>{vline}</i>"
    if is_boss_chamber_trial(cfg):
        cd_note = ""
        mn = int(cfg.get("boss_retry_cooldown_min_minutes") or 15)
        mx = int(cfg.get("boss_retry_cooldown_max_minutes") or 20)
        if mn and mx:
            cd_note = f"\n<i>После победы над боссом — пауза {mn}–{mx} мин до повторного боя.</i>"
        return (
            f"👑 <b>{html.escape(name)}</b>{variant_note}{hard}\n"
            f"Залы босса <b>{cleared}/{total}</b> · прогресс <b>{pct}%</b> · "
            f"финал: {boss}{dline}{extra}\n"
            f"<i>У каждого зала свой слот (ft_br) и стражи.</i>{cd_note}"
        )
    if is_defense_hub(cfg):
        wt = _waves_total(cfg)
        wd = int(st.get("waves_done") or 0)
        return (
            f"⚔️ <b>{html.escape(name)}</b>{variant_note}{hard}\n"
            f"Волны <b>{wd}/{wt}</b> · периметр <b>{cleared}/{total}</b> · "
            f"прогресс <b>{pct}%</b> · босс: {boss}{dline}{extra}\n"
            f"<i>Смерть: −{_waves_loss_on_death(cfg)} волны, сброс периметра.</i>"
        )
    return (
        f"⚔️ <b>{html.escape(name)}</b>{variant_note}{hard}\n"
        f"Прогресс <b>{pct}%</b> · угодья <b>{cleared}/{total}</b> · босс: {boss}{dline}{extra}\n"
        f"<i>Смерть сбрасывает фазу угодья"
        f"{' и весь этап' if cfg.get('death_reset') == 'full_trial' else ''}.</i>"
    )


def format_status_line(character: Character) -> str:
    return format_banner_html(character)


def is_trial_slot(slot_code: str) -> bool:
    return (
        slot_code in (SLOT_BOSS, SLOT_DEFENSE)
        or slot_code.startswith(SLOT_PREFIX)
        or slot_code.startswith(SLOT_CHAMBER_PREFIX)
    )
