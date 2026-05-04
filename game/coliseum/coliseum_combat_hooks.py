"""
Особые механики бойцов Колизея. Состояние: combat_state['coliseum'] — счётчики и флаги.
"""

from __future__ import annotations

import random
from typing import Any

from db.models.character import Character
from game.characters import pets as pets_mod
from game.coliseum.coliseum_data import fighter_by_id, SpecialId


def _csub(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("coliseum")
    if isinstance(raw, dict):
        return raw
    d: dict[str, Any] = {}
    state["coliseum"] = d
    return d


def is_coliseum_fight(state: dict[str, Any]) -> bool:
    return int(state.get("coliseum_fighter_id") or 0) > 0


def init_coliseum_fight(
    state: dict[str, Any],
    character: Character,
    fighter_id: int,
) -> list[str]:
    """После _build_combat_dict: инициализация подбоя и реплик."""
    logs: list[str] = []
    fd = int(fighter_id)
    state["coliseum_fighter_id"] = fd
    st = _csub(state)
    st.clear()
    st["fighter_id"] = fd
    # Чистый множитель исходящего урона монстра: иначе ауры/эффекты
    # могли оставить значение >1, и «ярость» Сунь Укуна улетала в потолок 2.5.
    state["monster_outgoing_mult"] = 1.0
    sp = fighter_by_id(fd)
    spec: SpecialId = sp.special if sp else "none"
    st["special"] = spec

    mods = state.get("passive_mods")
    if not isinstance(mods, dict):
        mods = {}
        state["passive_mods"] = mods

    if spec == "blind_2":
        st["blind_player_turns"] = 2
        cur = float(mods.get("extra_miss_chance", 0.0))
        mods["extra_miss_chance"] = cur + 0.30
        logs.append("🌫️ <b>Слепота:</b> меткость −30% (2 твоих хода).")
    if spec == "monster_evasion_30":
        cur = float(mods.get("extra_miss_chance", 0.0))
        mods["extra_miss_chance"] = cur + 0.30
        logs.append("👁️ <b>Аргус:</b> враг «уворачивается» — ты промахиваешься чаще.")
    if spec == "aid_barrier":
        st["aid_barrier_hp"] = 10000
        logs.append("💀 <b>Аид:</b> перед боссом стоят призраки — сначала сносится <b>10 000</b> «щита».")
    if spec == "wukong_rage":
        st["wukong_turns"] = 3
        # +30% к урону, без «наслоения» на чужой множитель; потолок 1.3 (не 2.5).
        state["monster_outgoing_mult"] = 1.3
        logs.append("🐒 <b>Сунь Укун:</b> ярость +30% к урону врага (3 его хода).")
    if spec == "fenrir_pet":
        st["pet_ban_turns"] = 2
        snap = pets_mod.pet_passive_delta(character)
        st["pet_snap"] = {k: float(v) if isinstance(v, (int, float)) else v for k, v in snap.items()}
        logs.append("🐺 <b>Фенрир:</b> питомец выбит из боя на <b>2</b> твоих хода.")
    if spec == "sleep_first":
        st["sleep_after_first_hit"] = True
        logs.append("💤 <b>Айша:</b> после твоего первого попадания ты можешь потерять ритм…")

    # Снимок пассивов для Фенрира
    if "pet_snap" not in st:
        st["pet_snap"] = {}

    return logs


def on_player_phase_start(state: dict[str, Any], character: Character) -> list[str]:
    """В начале хода игрока (перед дотами в callback — вызывать из combat_service)."""
    if not is_coliseum_fight(state):
        return []
    logs: list[str] = []
    st = _csub(state)
    fd = int(st.get("fighter_id", 0))

    # Фенрир: вычитаем пассив питомца
    _apply_pet_ban(state, character)

    if fd == 11 and random.random() < 0.30:
        state["player_skip_next_action"] = True
        logs.append("😨 <b>Страх (Зара):</b> ты дрогнул и теряешь ход!")

    if fd == 49:
        st["kronos_i"] = int(st.get("kronos_i", 0)) + 1
        if int(st["kronos_i"]) % 2 == 0:
            state["player_skip_next_action"] = True
            logs.append("⏳ <b>Кронос:</b> время сжимается — ход пропущен!")

    return logs


def _apply_pet_ban(state: dict[str, Any], character: Character) -> None:
    st = _csub(state)
    turns = int(st.get("pet_ban_turns", 0))
    if turns <= 0:
        return
    snap = st.get("pet_snap") or {}
    if not snap:
        snap = pets_mod.pet_passive_delta(character)
    mods = state.get("passive_mods")
    if not isinstance(mods, dict):
        return
    for k, v in snap.items():
        if k == "def_bonus":
            mods["def_bonus"] = float(mods.get("def_bonus", 0.0)) - float(v)
        elif k == "crit_bonus":
            mods["crit_bonus"] = float(mods.get("crit_bonus", 0.0)) - float(v)
        elif k == "dodge_bonus":
            mods["dodge_bonus"] = float(mods.get("dodge_bonus", 0.0)) - float(v)
        elif k == "mp_regen_turn":
            mods["mp_regen_turn"] = int(mods.get("mp_regen_turn", 0)) - int(v)
        elif k == "mag_bonus_percent":
            mods["mag_bonus_percent"] = int(mods.get("mag_bonus_percent", 0)) - int(v)


def after_player_damage_to_monster(state: dict[str, Any], dmg: int) -> tuple[int, list[str]]:
    """После расчёта урона игрока по монстру, до списания HP; Зефир/Локи/щит Аида."""
    logs: list[str] = []
    if not is_coliseum_fight(state) or dmg <= 0:
        return dmg, logs
    st = _csub(state)
    fd = int(st.get("fighter_id", 0))
    out = dmg

    if fd == 25 and random.random() < 0.20:
        logs.append("💨 <b>Зефир:</b> порыв сносит удар — <b>0</b> урона!")
        return 0, logs

    if state.pop("coliseum_self_hit_next", False):
        php = int(state["player_hp"])
        state["player_hp"] = max(0, php - out)
        state["combo_streak"] = 0
        state["combo_next_mult"] = 1.0
        logs.append(f"🪞 <b>Локи:</b> ты бьёшь себя — <b>−{out}</b> HP!")
        return 0, logs

    barrier = int(st.get("aid_barrier_hp", 0))
    if barrier > 0:
        take = min(barrier, out)
        st["aid_barrier_hp"] = barrier - take
        out -= take
        logs.append(f"💀 Щит духов поглощает <b>{take}</b> урона (осталось {st['aid_barrier_hp']}).")

    if out > 0:
        logs.extend(on_first_player_hit_done(state))

    return out, logs


def on_first_player_hit_done(state: dict[str, Any]) -> list[str]:
    """После успешного удара по HP монстру (остаток урона > 0) — Айша."""
    logs: list[str] = []
    if not is_coliseum_fight(state):
        return logs
    st = _csub(state)
    if not st.get("sleep_after_first_hit"):
        return logs
    st["sleep_after_first_hit"] = False
    state["player_skip_next_action"] = True
    logs.append("💤 <b>Айша:</b> усыпление — ты пропускаешь следующее действие!")
    return logs


def maybe_trigger_loki(state: dict[str, Any]) -> None:
    """В конце хода монстра — шанс иллюзии на следующий удар игрока."""
    if not is_coliseum_fight(state):
        return
    st = _csub(state)
    if int(st.get("fighter_id", 0)) != 43:
        return
    if random.random() < 0.28:
        state["coliseum_self_hit_next"] = True


def after_monster_turn_increment(state: dict[str, Any]) -> list[str]:
    """Сразу после state['monster_turn'] += 1: молния Зевса, триггер Локи."""
    logs: list[str] = []
    if not is_coliseum_fight(state):
        return logs
    st = _csub(state)
    if int(st.get("fighter_id", 0)) == 50:
        mt = int(state.get("monster_turn", 0))
        if mt > 0 and mt % 3 == 0:
            mx = int(state["player_hp_max"])
            zap = max(1, int(mx * 0.12))
            php = int(state["player_hp"])
            state["player_hp"] = max(0, php - zap)
            state["combo_streak"] = 0
            state["combo_next_mult"] = 1.0
            logs.append(f"⚡ <b>Зевс:</b> молния Олимпа — <b>−{zap}</b> HP!")
    maybe_trigger_loki(state)
    return logs


def end_round_coliseum(state: dict[str, Any], character: Character) -> list[str]:
    """После engine.end_round_tick — тики слепоты/вуконга/фенрира."""
    logs: list[str] = []
    if not is_coliseum_fight(state):
        return logs
    st = _csub(state)
    mods = state.get("passive_mods")
    if not isinstance(mods, dict):
        mods = {}
        state["passive_mods"] = mods

    bt = int(st.get("blind_player_turns", 0))
    if bt > 0:
        st["blind_player_turns"] = bt - 1
        if int(st.get("blind_player_turns", 0)) <= 0:
            mods["extra_miss_chance"] = max(0.0, float(mods.get("extra_miss_chance", 0.0)) - 0.30)
            logs.append("🌫️ Слепота спадает.")

    wt = int(st.get("wukong_turns", 0))
    if wt > 0:
        st["wukong_turns"] = wt - 1
        if int(st.get("wukong_turns", 0)) <= 0:
            state["monster_outgoing_mult"] = 1.0
            logs.append("🐒 Ярость Сунь Укуна спала.")

    pb = int(st.get("pet_ban_turns", 0))
    if pb > 0:
        st["pet_ban_turns"] = pb - 1

    return logs


def mulan_reduce_incoming_damage(state: dict[str, Any], dmg: int, logs: list[str]) -> int:
    """Мулан: часть угрозы приходится на питомца (−22% урона по герою)."""
    if not is_coliseum_fight(state) or dmg <= 0:
        return dmg
    if int(_csub(state).get("fighter_id", 0)) != 33:
        return dmg
    logs.append("🐉 <b>Мулан:</b> удар задевает спутника — ты получаешь меньше урона.")
    return max(1, int(dmg * 0.78))
