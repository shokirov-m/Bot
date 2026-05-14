"""
Ядро пошагового боя: атака, скиллы, ход монстра, проверка исхода.
Всё состояние — JSON-словарь (FSM).
"""

from __future__ import annotations

import html
import random
from typing import Any, Literal

from game.balance import (
    MONSTER_ARMOR_PENETRATION,
    MONSTER_ARMOR_PENETRATION_MAJOR_BOSS,
    MONSTER_DAMAGE_DEALT_MULT,
)
from game.characters.skills import SkillDef, passive_combat_modifiers, skills_for_class
from game.coliseum import coliseum_combat_hooks as coliseum_hooks
from game.combat import companions as companions_mod
from game.combat import effects, formulas, monster_ai
from game.combat.monster_abilities import (
    apply_pre_turn_abilities,
    apply_post_hit_abilities,
    apply_rune_golem_absorb,
    apply_shatter_death,
    check_and_consume_monster_shield,
    check_zombie_undying,
    get_extra_pierce_fraction,
    roll_monster_double_turn,
)
from game.items.runes import ELEMENTS, RuneData, rune_burn_params_for_rank
from game.combat import passive_gear
from game.floors.floor_entry_mods import maybe_lightning_execute_after_monster_damaged

Outcome = Literal["continue", "win", "lose"]

COMBO_BONUS_MULT = 1.15


def _log_weapon_rune_elemental_once(state: dict[str, Any], elem_bonus: int, logs: list[str]) -> None:
    """
    Строка в лог боя: как руны и таблица слабостей пересекаются со стихией врага.
    pct — итог (weapon_rune_bonus_pct + элементальная таблица), уже учтён в формуле.
    """
    pct = int(elem_bonus)
    payloads = list(state.get("weapon_rune_payloads") or [])
    mon = state.get("monster") or {}
    mon_el_raw = str(mon.get("element") or "earth")
    mon_meta = ELEMENTS.get(mon_el_raw.strip().lower(), ELEMENTS["earth"])
    mon_lbl = f"{mon_meta.get('emoji', '')} {mon_meta.get('name', mon_el_raw)}".strip()
    if not payloads:
        if pct > 0:
            head = "🎯 <b>Слабое звено стихии!</b>" if pct >= 30 else "✨ <b>Стихийный резонанс</b>"
            logs.append(f"{head} против <i>{mon_lbl}</i>: <b>+{pct}%</b> к урону.")
        elif pct < 0:
            logs.append(f"🛡️ <b>Стихия врага сопротивляется:</b> <b>{pct}%</b> к урону vs <i>{mon_lbl}</i>.")
        return
    bits: list[str] = []
    for raw in payloads:
        rd = raw if isinstance(raw, dict) else {}
        try:
            r = RuneData.from_dict(rd)
        except (ValueError, TypeError, KeyError):
            continue
        em = ELEMENTS.get(r.element, {}).get("emoji", "·")
        rom = ("", "I", "II", "III", "IV", "V")[r.rank] if 1 <= r.rank <= 5 else str(r.rank)
        bits.append(f"{em}{rom}")
    rune_lbl = " ".join(bits) if bits else "руны"
    if pct <= 0:
        if bits and not state.get("rune_neutral_logged"):
            state["rune_neutral_logged"] = True
            if pct < 0:
                logs.append(f"⚠️ Руны ({rune_lbl}) vs <i>{mon_lbl}</i>: итого <b>{pct}%</b> к урону.")
            else:
                logs.append(f"⚪ Руны ({rune_lbl}) без преимущества против <i>{mon_lbl}</i>.")
        return
    head = "🎯 <b>Слабое звено стихии!</b>" if pct >= 30 else "✨ <b>Удар по стихии</b>"
    logs.append(f"{head} — {rune_lbl} vs <i>{mon_lbl}</i>: <b>+{pct}%</b> к урону.")


COMBO_STREAK_TO_TRIGGER = 3


def _rune_added_damage_log_line(elem_scaled: int, flat_el: int) -> str | None:
    """Строка боя: сколько урона дали руны (стихийный % + плоский)."""
    tot = int(elem_scaled) + int(flat_el)
    if tot <= 0:
        return None
    if elem_scaled <= 0:
        return f"✳ Руны добавили +{flat_el} урона (плоский урон рун)."
    if flat_el <= 0:
        return f"✳ Руны добавили +{elem_scaled} урона (стихийный бонус рун)."
    return f"✳ Руны добавили +{tot} урона (стихийный бонус +{elem_scaled}, плоский +{flat_el})."


def _maybe_log_rune_element_hidden_by_armor(
    state: dict[str, Any],
    logs: list[str],
    *,
    elem_bonus_pct: int,
    scaled_elem: int,
    flat_el: int,
) -> None:
    """
    Если стихийный бонус есть, а строка «✳ Руны добавили…» не вывелась — пояснить один раз за бой.
    Причины: (1) после брони дельта «с элементом / без» = 0; (2) дельта есть, но доля в финальном
    ударе округлилась до 0 и плоского урона рун нет в этом билде.
    """
    if state.get("rune_elem_armor_floored_tip"):
        return
    if scaled_elem > 0 or flat_el > 0:
        return
    rb = int(state.get("weapon_rune_bonus_pct", 0))
    if elem_bonus_pct <= 0 and rb <= 0:
        return
    state["rune_elem_armor_floored_tip"] = True
    logs.append(
        "💡 <b>Вклад стихии/рун в этом ударе не показан отдельной строкой</b>: чаще всего "
        "из‑за <b>очень высокой брони</b> разница «с элементом / без» после вычитания брони "
        "схлопывается, либо доля в финальном ударе слишком мала и округляется до нуля. "
        "Проценты рун при этом уже могли заложиться в базу удара."
    )


def combo_break_on_player_hurt(state: dict[str, Any]) -> None:
    """Сброс серии комбо при любом потере HP игроком (не считая добровольные эффекты)."""
    state["combo_streak"] = 0
    state["combo_next_mult"] = 1.0


def combo_apply_outgoing_damage(state: dict[str, Any], dmg: int, logs: list[str]) -> int:
    """
    Три удара подряд по врагу без получения урона → сообщение «КОМБО x3» и +15% к следующему удару.
    Вызывать после расчёта урона, до списания HP монстра.
    """
    if state.get("is_tutorial"):
        return dmg
    if dmg <= 0:
        return dmg
    pending = float(state.get("combo_next_mult") or 1.0)
    if pending > 1.001:
        new_dmg = max(1, round(dmg * pending))
        if new_dmg > dmg:
            logs.append("🔥 <b>Комбо-удар!</b> +15% к этому удару.")
        dmg = new_dmg
        state["combo_next_mult"] = 1.0
    st = int(state.get("combo_streak", 0)) + 1
    if st >= COMBO_STREAK_TO_TRIGGER:
        logs.append("⚡ <b>КОМБО x3!</b> Следующий удар по врагу <b>+15%</b>.")
        st = 0
        state["combo_next_mult"] = COMBO_BONUS_MULT
    state["combo_streak"] = st
    return dmg


def _m(state: dict[str, Any]) -> dict[str, Any]:
    return state["monster"]


def record_player_last_damage_to_monster(state: dict[str, Any], amount: int) -> None:
    """Последний урон по HP монстра (удар, скилл, DoT по врагу за тик, контрудар блока) — для UI, не сумма за бой."""
    if amount <= 0:
        return
    state["player_last_damage_to_monster"] = int(amount)


def record_monster_last_damage_to_player(state: dict[str, Any], amount: int) -> None:
    """Последний урон по HP игрока от удара монстра в его ход (после щита) — для UI."""
    if amount <= 0:
        return
    state["monster_last_damage_to_player"] = int(amount)


def _stats(state: dict[str, Any]) -> dict[str, int]:
    return state["stats"]


def _mods(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("passive_mods")
    if isinstance(raw, dict):
        return raw
    mods = passive_combat_modifiers(str(state.get("class_key") or "wanderer"))
    state["passive_mods"] = mods
    return mods


def apply_equipment_on_hit_procs(state: dict[str, Any], mods: dict[str, Any], logs: list[str]) -> None:
    """Проки статусов и оглушения с экипировки после успешного удара по HP монстра."""
    obc = float(mods.get("on_hit_bleed_chance", 0.0))
    if obc > 0 and random.random() < obc:
        effects.add_effect("monster", state, "Кровотечение", "bleed", 3, {"potency_percent": 4})
        logs.append("🩸 Враг кровоточит от твоего удара!")
    obrn = float(mods.get("on_hit_burn_chance", 0.0))
    if obrn > 0 and random.random() < obrn:
        effects.add_effect("monster", state, "Поджог", "burn", 3, {"potency_percent": 4})
        logs.append("🔥 Враг охвачен огнём!")
    ofz = float(mods.get("on_hit_freeze_chance", 0.0))
    if ofz > 0 and random.random() < ofz:
        state["monster_skip_next"] = True
        logs.append("❄️ Враг скован льдом — пропустит ход!")
    opo = float(mods.get("on_hit_poison_chance", 0.0))
    if opo > 0 and random.random() < opo:
        effects.add_effect("monster", state, "Яд", "poison", 3, {"potency_percent": 4})
        logs.append("☠️ Враг отравлен!")
    ost = float(mods.get("stun_chance", 0.0))
    if ost > 0 and random.random() < ost:
        state["monster_skip_next"] = True
        logs.append("⭐ Экипировка оглушает — враг может пропустить ход!")


def apply_floor_aura_effects(state: dict[str, Any]) -> list[str]:
    logs = []
    aura = state.get("floor_aura")
    if not aura: return []
    
    # HP Loss (Player)
    if "hp_loss_turn_pct" in aura:
        loss = max(1, int(state["player_hp"] * aura.get("hp_loss_turn_pct", 0)))
        state["player_hp"] = max(0, int(state["player_hp"]) - loss)
        logs.append(f"{aura['emoji']} <b>{aura['name']}</b>: вы теряете {loss} HP от окружения.")
        combo_break_on_player_hurt(state)

    # Regen (Player)
    if "player_regen_turn_pct_max" in aura:
        pct = float(aura.get("player_regen_turn_pct_max", 0) or 0)
        if pct > 0:
            heal = max(1, int(int(state["player_hp_max"]) * pct))
            pre = int(state["player_hp"])
            if pre > 0 and pre < int(state["player_hp_max"]):
                state["player_hp"] = min(int(state["player_hp_max"]), pre + heal)
                logs.append(f"{aura['emoji']} <b>{aura['name']}</b>: вы восстановили {int(state['player_hp']) - pre} HP.")
        
    # Regen (Monster)
    if "monster_regen_pct" in aura:
        m = state["monster"]
        regen = int(int(m["max_hp"]) * aura.get("monster_regen_pct", 0))
        if regen > 0:
            m["hp"] = min(int(m["max_hp"]), int(m["hp"]) + regen)
            logs.append(f"{aura['emoji']} <b>{aura['name']}</b>: враг восстановил {regen} HP.")
            
    # Blizzard (Miss Chance Period)
    period = aura.get("miss_chance_mod_period")
    if period:
        # Use monster_turn + 1 because this is called at start of turn
        mt = int(state.get("monster_turn", 0)) + 1
        if mt % period == 0:
            state["player_aura_miss_chance"] = aura.get("miss_chance_mod_value", 0)
            logs.append(f"{aura['emoji']} <b>{aura['name']}</b>: видимость падает, меткость снижена!")
        else:
            state["player_aura_miss_chance"] = 0
            
    return logs


def apply_elixir_buffs(state: dict[str, Any], dmg: int) -> int:
    """Apply multipliers from active elixirs and passive tree bonuses."""
    mult = float(_mods(state).get("atk_mult", 1.0))
    bonus_pct = float(_mods(state).get("atk_bonus_pct", 0.0))
    return max(1, int(int(dmg) * mult * (1.0 + bonus_pct / 100.0)))


def apply_dot_damage_player(state: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    pre_hp = int(state["player_hp"])
    mx = int(state["player_hp_max"])
    hp = int(state["player_hp"])
    new_eff: list[dict[str, Any]] = []
    for e in list(state.get("player_effects", [])):
        if e.get("key") == "burn":
            dmg = max(1, int(mx * int(e.get("potency_percent", 5)) / 100))
            hp -= dmg
            logs.append(f"→ 👤 🔥 Поджог: −{dmg} HP")
        elif e.get("key") == "poison":
            dmg = max(1, int(mx * int(e.get("potency_percent", 3)) / 100))
            hp -= dmg
            logs.append(f"→ 👤 💀 Яд: −{dmg} HP")
        elif e.get("key") == "bleed":
            dmg = max(1, int(mx * int(e.get("potency_percent", 2)) / 100))
            hp -= dmg
            logs.append(f"→ 👤 🩸 Кровотечение: −{dmg} HP")
        elif e.get("key") == "hot":
            heal = max(1, int(mx * int(e.get("potency_percent", 5)) / 100))
            hp = min(mx, hp + heal)
            logs.append(f"→ 👤 🌿 Исцеление со временем: +{heal} HP")
        turns = int(e.get("turns", 0)) - 1
        if turns > 0:
            e["turns"] = turns
            new_eff.append(e)
    state["player_hp"] = max(0, hp)
    state["player_effects"] = new_eff
    if int(state["player_hp"]) < pre_hp:
        combo_break_on_player_hurt(state)
    return logs


def apply_dot_damage_monster(state: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    m = _m(state)
    hp = int(m["hp"])
    pre_hp = hp
    mx = int(m["max_hp"])
    new_eff: list[dict[str, Any]] = []
    for e in list(state.get("monster_effects", [])):
        if e.get("key") == "burn":
            dmg = max(1, int(mx * int(e.get("potency_percent", 3)) / 100))
            hp -= dmg
            logs.append(f"→ 👹 🔥 Враг горит: −{dmg} HP")
        elif e.get("key") == "bleed":
            dmg = max(1, int(mx * int(e.get("potency_percent", 4)) / 100))
            hp -= dmg
            logs.append(f"→ 👹 🩸 Враг истекает кровью: −{dmg} HP")
        elif e.get("key") == "poison":
            dmg = max(1, int(mx * int(e.get("potency_percent", 3)) / 100))
            hp -= dmg
            logs.append(f"→ 👹 ☠️ Яд: −{dmg} HP")
        turns = int(e.get("turns", 0)) - 1
        if turns > 0:
            e["turns"] = turns
            new_eff.append(e)
    m["hp"] = max(0, hp)
    state["monster_effects"] = new_eff
    dealt = pre_hp - int(m["hp"])
    if dealt > 0:
        record_player_last_damage_to_monster(state, dealt)
    return logs


def regen_mp_passive(state: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    regen = int(_mods(state).get("mp_regen_turn", 0))
    if regen > 0:
        cur = int(state["player_mp"])
        mx = int(state["player_mp_max"])
        new = min(mx, cur + regen)
        state["player_mp"] = new
        if new > cur:
            logs.append(f"💙 MP +{new - cur} (пассив класса).")
    hp_pct = float(_mods(state).get("hp_regen_pct_turn", 0.0))
    if hp_pct > 0.0:
        cur_hp = int(state["player_hp"])
        mx_hp = int(state["player_hp_max"])
        if cur_hp > 0 and cur_hp < mx_hp:
            heal = max(1, int(mx_hp * hp_pct))
            new_hp = min(mx_hp, cur_hp + heal)
            state["player_hp"] = new_hp
            if new_hp > cur_hp:
                logs.append(f"💚 HP +{new_hp - cur_hp} (пассив класса).")
    return logs


def tick_cooldowns(state: dict[str, Any]) -> None:
    for k in list(state.get("skill_cd", {}).keys()):
        v = int(state["skill_cd"][k])
        if v > 0:
            state["skill_cd"][k] = v - 1
    cd = int(state.get("monster_special_cd", 0))
    if cd > 0:
        state["monster_special_cd"] = cd - 1


def player_weapon_attack_value(state: dict[str, Any]) -> int:
    """
    Атака из состояния боя: combat_service выставляет weapon_attack через
    character_service.weapon_attack_value_from_item_data (scaled_weapon_attack_value + заточка).
    """
    return int(state.get("weapon_attack", 3))


def player_defense_value(state: dict[str, Any]) -> int:
    vit = int(_stats(state)["vit"])
    base = vit // 2
    gear = int(state.get("player_equipment_defense", 0))
    arm_m = float(state.get("rune_armor_mult", 1.0))
    if arm_m != 1.0:
        gear = int(gear * arm_m)
    total = int(
        base
        + float(_mods(state).get("def_bonus", 0))
        + int(state.get("player_fortify_bonus", 0))
        + int(state.get("player_level_def_bonus", 0))
        + gear,
    )
    return max(0, int(total * float(_mods(state).get("def_mult", 1.0))))


def monster_armor_value(state: dict[str, Any]) -> int:
    """Эффективная броня: база − разложение + временное укрепление."""
    m = _m(state)
    base = int(m["defense"])
    shred = int(state.get("monster_def_mod", 0))
    fort = int(state.get("monster_fortify_flat", 0))
    return max(0, base - shred + fort)


def elemental_bonus_percent(attacker_element: str | None, defender_element: str | None) -> int:
    """
    Элементальный бонус атаки:
    +25% если атакуем слабость врага, -15% если атакуем устойчивость,
    +10% если стихии совпадают (синергия одинаковых стихий).
    """
    from game.items.runes import ELEMENT_RESISTANCE, ELEMENT_WEAKNESS, ELEMENTS

    a = str(attacker_element or "").strip().lower()
    d = str(defender_element or "").strip().lower()
    if not a or not d or a not in ELEMENTS or d not in ELEMENTS:
        return 0
    # Check weakness: defender is weak to attacker's element
    if ELEMENT_WEAKNESS.get(d) == a:
        return 25
    # Check resistance: defender resists attacker's element
    if ELEMENT_RESISTANCE.get(d) == a:
        return -15
    # Same-element synergy
    if a == d:
        return 10
    return 0


def player_attack_element_for_matchup(state: dict[str, Any], *, magic_skill: bool = False) -> str | None:
    """
    Стихия атакующего игрока для таблицы слабостей.
    Физ. удары: приоритет у элементов рун на оружии, иначе стихия персонажа.
    Магические навыки: стихия персонажа (руны задают отдельный % в combat_state).
    """
    from game.items.runes import ELEMENTS

    if not magic_skill:
        for raw in list(state.get("weapon_rune_payloads") or []):
            if not isinstance(raw, dict):
                continue
            el = str(raw.get("element") or "").strip().lower()
            if el in ELEMENTS:
                return el
    raw_ch = state.get("player_character_element")
    ch = str(raw_ch).strip().lower() if raw_ch else ""
    return ch if ch in ELEMENTS else None


_ELEMENTAL_DAMAGE_PCT_CAP = 250
_ELEMENTAL_DAMAGE_PCT_FLOOR = -50


def combined_player_elemental_damage_percent(state: dict[str, Any], *, magic_skill: bool = False) -> int:
    """weapon_rune_bonus_pct + таблица слабостей для цели текущего боя."""
    rb = int(state.get("weapon_rune_bonus_pct", 0))
    mon = str((_m(state)).get("element") or "earth").strip().lower()
    atk_el = player_attack_element_for_matchup(state, magic_skill=magic_skill)
    table = elemental_bonus_percent(atk_el, mon)
    vip_ex = int(state.get("vip_frostlord_elem_bonus_pct", 0))
    total = rb + table + vip_ex
    return max(_ELEMENTAL_DAMAGE_PCT_FLOOR, min(_ELEMENTAL_DAMAGE_PCT_CAP, total))


def _apply_weapon_mastery_to_damage(state: dict[str, Any], dmg: int) -> int:
    mult = float(state.get("weapon_mastery_mult", 1.0))
    return max(1, int(dmg * mult))


def _mark_weapon_mastery_strike(state: dict[str, Any]) -> None:
    if state.get("player_weapon_type"):
        state["mastery_strike_pending"] = True


def _rune_status_proc_logs(state: dict[str, Any]) -> list[str]:
    """Случайные статусы на врага от вставленных рун."""
    logs: list[str] = []
    for raw in list(state.get("weapon_rune_payloads") or []):
        if not isinstance(raw, dict):
            continue
        try:
            r = RuneData.from_dict(raw)
        except (ValueError, TypeError, KeyError):
            continue
        if random.random() >= r.status_chance:
            continue
        meta = ELEMENTS.get(r.element, {})
        se = str(meta.get("status_effect", "burn"))
        if se == "burn":
            bt, bp = rune_burn_params_for_rank(r.rank)
            effects.add_effect(
                "monster",
                state,
                "Рунный жар",
                "burn",
                bt,
                {"potency_percent": bp},
            )
            logs.append(f"🔥 Руна поджигает врага на {bt} х.!")
        elif se == "freeze":
            state["monster_skip_next"] = True
            logs.append("❄️ Ледяная руна заледенила врага!")
        elif se == "paralyze":
            state["monster_skip_next"] = True
            logs.append("⚡ Паралич от руны!")
        elif se == "fear":
            state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.82)
            state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
            logs.append("🌑 Тьма руны сеет страх!")
        elif se == "blind":
            state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.75)
            state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
            logs.append("✨ Вспышка руны ослепляет!")
        elif se == "slow":
            state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.78)
            state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
            logs.append("🌿 Земля руны сковывает шаги!")
        elif se == "poison":
            effects.add_effect(
                "monster",
                state,
                "Рунный яд",
                "poison",
                3,
                {"potency_percent": 3},
            )
            logs.append("☠️ Руна отравляет врага!")
    return logs


def player_attack(state: dict[str, Any]) -> tuple[list[str], Outcome, int]:
    logs: list[str] = []
    st = _stats(state)
    luck = int(st["luck"])
    mods = _mods(state)

    # Оглушение — следующее действие пропущено
    if state.get("player_skip_next_action"):
        del state["player_skip_next_action"]
        logs.append("💫 Оглушён! Атака пропущена.")
        return logs, "continue", 0

    # Щит монстра (Valkyrie) — блокирует один удар
    if check_and_consume_monster_shield(state, logs):
        return logs, "continue", 0

    # Проверка промаха (зависит от ЛОВ; extra_miss_chance из ауры и экипировки / мастерства)
    aura_miss = float(state.get("player_aura_miss_chance", 0.0))
    mod_miss = float(mods.get("extra_miss_chance", 0.0))
    if formulas.roll_miss(int(st["dex"]), extra_miss_chance=aura_miss + mod_miss):
        logs.append("💨 Промах! Удар не достиг цели.")
        return logs, "continue", 0

    elem_bonus = combined_player_elemental_damage_percent(state)
    _log_weapon_rune_elemental_once(state, elem_bonus, logs)

    d_yes, _d_ne, elem_extra = formulas.physical_damage_split(
        int(st["str"]),
        player_weapon_attack_value(state),
        monster_armor_value(state),
        elemental_bonus_percent=elem_bonus,
    )
    dmg = d_yes
    crit = formulas.roll_crit(luck, crit_bonus_flat=float(mods.get("crit_bonus", 0.0)))
    if crit:
        dmg = int(dmg * formulas.crit_multiplier())
        cdm = int(state.get("rune_crit_damage_bonus_percent", 0))
        if cdm > 0:
            dmg = int(dmg * (1.0 + cdm / 100.0))
    dmg = _apply_weapon_mastery_to_damage(state, dmg)
    dmg = apply_elixir_buffs(state, dmg)
    dmg = combo_apply_outgoing_damage(state, dmg, logs)
    before_flat = dmg
    flat_el = int(state.get("weapon_rune_flat_elemental", 0))
    scaled_elem = (
        int(round(elem_extra * (before_flat / max(1, d_yes)))) if elem_extra > 0 else 0
    )
    dmg += flat_el
    rline = _rune_added_damage_log_line(scaled_elem, flat_el)
    if rline:
        logs.append(rline)
    else:
        _maybe_log_rune_element_hidden_by_armor(
            state,
            logs,
            elem_bonus_pct=elem_bonus,
            scaled_elem=scaled_elem,
            flat_el=flat_el,
        )

    # Проклятие (снижает урон игрока)
    pdm = float(state.get("player_damage_mult", 1.0))
    if pdm < 0.999:
        dmg = max(1, int(dmg * pdm))

    _m_obj = _m(state)
    is_boss_target = bool(_m_obj.get("is_major_boss")) or bool(_m_obj.get("is_mini_boss"))
    is_elite_target = str(state.get("spawn_slot") or "") == "e"
    bdm = float(mods.get("boss_dmg_mult", 1.0))
    if is_boss_target and bdm > 1.0001:
        dmg = max(1, int(round(dmg * bdm)))
    edm = float(mods.get("elite_dmg_mult", 1.0))
    if is_elite_target and edm > 1.0001:
        dmg = max(1, int(round(dmg * edm)))

    dmg, _cx = coliseum_hooks.after_player_damage_to_monster(state, dmg)
    logs.extend(_cx)
    if dmg <= 0:
        return logs, "continue", 0

    dmg = apply_rune_golem_absorb(state, dmg, logs)

    if crit:
        logs.append(f"→ 👤 Герой: 🗡️ {dmg} урона [КРИТ💥]")
    else:
        logs.append(f"→ 👤 Герой: 🗡️ {dmg} урона")

    apply_equipment_on_hit_procs(state, mods, logs)

    syn = str(state.get("rune_synergy_name") or "")
    if syn and not state.get("rune_syn_logged"):
        state["rune_syn_logged"] = True
        logs.append(f"🔗 Синергия рун: {syn}")

    logs.extend(_rune_status_proc_logs(state))

    _m(state)["hp"] = max(0, int(_m(state)["hp"]) - dmg)
    passive_gear.apply_lifesteal_for_damage(state, dmg, logs)
    lnx = maybe_lightning_execute_after_monster_damaged(state, logs)
    if lnx == "win":
        record_player_last_damage_to_monster(state, dmg)
        _mark_weapon_mastery_strike(state)
        undying_logs: list[str] = []
        if check_zombie_undying(state, undying_logs):
            logs.extend(undying_logs)
            return logs, "continue", dmg
        apply_shatter_death(state, logs)
        return logs, "win", dmg
    record_player_last_damage_to_monster(state, dmg)
    _mark_weapon_mastery_strike(state)
    if int(_m(state)["hp"]) <= 0:
        # Способность Нежить (zombie): выживает один раз
        undying_logs = []
        if check_zombie_undying(state, undying_logs):
            logs.extend(undying_logs)
            return logs, "continue", dmg
        apply_shatter_death(state, logs)
        return logs, "win", dmg
    return logs, "continue", dmg


def player_skill_blocked_reason(state: dict[str, Any], index: int) -> str | None:
    """
    Проверка до расхода хода: пустой слот, перезарядка или нехватка MP.
    Оглушение обрабатывается отдельно в player_skill (тратит ход).
    """
    skill_src = str(state.get("combat_skill_class_key") or state.get("class_key") or "wanderer")
    skills: tuple[SkillDef, SkillDef, SkillDef] = state.get("combat_skills") or skills_for_class(skill_src)
    if index < 0 or index > 2:
        return "Нет такого навыка."
    sk: SkillDef = skills[index]
    if sk.key == "_empty":
        return "Пустой слот навыка — назначь способность в профиле."
    cd = int(state["skill_cd"].get(str(index), 0))
    if cd > 0:
        return f"Навык на перезарядке ({cd} х.)."
    mp = int(state["player_mp"])
    cost = sk.mp_cost
    mp_mult = float(state.get("player_mp_cost_mult", 1.0))
    if mp_mult != 1.0:
        cost = int(cost * mp_mult)
    if mp < cost:
        return f"Недостаточно MP (нужно {cost})."
    return None


def player_skill(state: dict[str, Any], index: int) -> tuple[list[str], Outcome | None, int]:
    """
    Возвращает (логи, исход, урон_по_врагу) или (логи, None, 0) если навык не применён.
    Урон — только по веткам, наносящим HP-урон монстру (после всех множителей).
    """
    logs: list[str] = []

    # Оглушение — следующее действие пропущено
    if state.get("player_skip_next_action"):
        del state["player_skip_next_action"]
        logs.append("💫 Оглушён! Навык не сработал.")
        return logs, "continue", 0

    blocked = player_skill_blocked_reason(state, index)
    if blocked is not None:
        logs.append(blocked)
        return logs, None, 0

    skill_src = str(state.get("combat_skill_class_key") or state.get("class_key") or "wanderer")
    skills: tuple[SkillDef, SkillDef, SkillDef] = state.get("combat_skills") or skills_for_class(skill_src)
    sk: SkillDef = skills[index]

    mp = int(state["player_mp"])
    cost = sk.mp_cost
    mp_mult = float(state.get("player_mp_cost_mult", 1.0))
    if mp_mult != 1.0:
        cost = int(cost * mp_mult)

    state["player_mp"] = mp - cost
    state["skill_cd"][str(index)] = sk.cooldown

    st = _stats(state)
    mods = _mods(state)
    luck = int(st["luck"])

    if sk.effect_key == "heal":
        heal = int(state["player_hp_max"] * 0.25)
        state["player_hp"] = min(int(state["player_hp_max"]), int(state["player_hp"]) + heal)
        logs.append(f"{sk.name}: +{heal} HP.")
        return logs, "continue", 0

    if sk.effect_key == "block_next":
        state["player_block_next"] = True
        logs.append(f"{sk.name}: готов отразить следующий удар.")
        return logs, "continue", 0

    if sk.effect_key == "dodge_buff":
        state["player_temp_dodge"] = float(state.get("player_temp_dodge", 0.0)) + 0.18
        state["player_temp_dodge_turns"] = max(int(state.get("player_temp_dodge_turns", 0)), 3)
        logs.append(f"{sk.name}: +18% к шансу уклонения на 3 хода.")
        return logs, "continue", 0

    if sk.effect_key == "shield":
        absorb = max(14, int(int(state["player_hp_max"]) * 0.18))
        state["player_shield_hp"] = int(state.get("player_shield_hp", 0)) + absorb
        logs.append(f"{sk.name}: щит поглощает до {absorb} урона (накопительно).")
        return logs, "continue", 0

    if sk.effect_key == "smoke":
        state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.62)
        state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 3)
        logs.append(f"{sk.name}: враг бьёт слабее (~−38% урона, 3 х.).")
        return logs, "continue", 0

    if sk.effect_key == "fortify" and sk.power == 0:
        state["player_fortify_bonus"] = int(state.get("player_fortify_bonus", 0)) + 10
        state["player_fortify_turns"] = max(int(state.get("player_fortify_turns", 0)), 3)
        logs.append(f"{sk.name}: +10 к защите на 3 хода.")
        return logs, "continue", 0

    if sk.effect_key == "hot":
        effects.add_effect("player", state, "Тотем исцеления", "hot", 4, {"potency_percent": 5})
        logs.append(f"{sk.name}: восстановление HP в начале твоих ходов (4 х.).")
        return logs, "continue", 0

    if sk.effect_key == "shred_armor":
        state["monster_def_mod"] = int(state.get("monster_def_mod", 0)) + 3
        logs.append(f"{sk.name}: броня врага ослаблена.")

    if sk.power == 0:
        return logs, "continue", 0

    mdef = monster_armor_value(state)

    elem_for_tip = 0
    elem_skill = 0
    if sk.kind == "mag":
        mag_elem = combined_player_elemental_damage_percent(state, magic_skill=True)
        elem_for_tip = mag_elem
        _log_weapon_rune_elemental_once(state, mag_elem, logs)
        base = formulas.magical_damage(
            int(st["int"]),
            max(2, player_weapon_attack_value(state) // 2),
            mdef,
            mag_bonus_percent=int(mods.get("mag_bonus_percent", 0)),
            elemental_bonus_percent=mag_elem,
        )
        base = int(base * formulas.int_skill_mag_extra_scale(int(st["int"])))
    else:
        rb = combined_player_elemental_damage_percent(state, magic_skill=False)
        elem_for_tip = rb
        _log_weapon_rune_elemental_once(state, rb, logs)
        d_yes, d_ne, _ = formulas.physical_damage_split(
            int(st["str"]),
            player_weapon_attack_value(state),
            mdef,
            elemental_bonus_percent=rb,
        )
        t_phys = formulas.int_skill_phys_tuning_multiplier(int(st["int"]))
        base_y = int(d_yes * t_phys)
        base_n = int(d_ne * t_phys)
        if sk.power:
            dmg_y = int(base_y * sk.power)
            dmg_n = int(base_n * sk.power)
        else:
            dmg_y = base_y
            dmg_n = base_n
        elem_skill = max(0, dmg_y - dmg_n)
        base = base_y

    dmg = int(base * sk.power) if sk.power else int(base)
    dmg_start = dmg

    mon = _m(state)
    mhp, mmx = int(mon["hp"]), int(mon["max_hp"])
    if sk.effect_key == "backstab" and mmx > 0 and mhp / mmx > 0.70:
        dmg = int(dmg * 1.28)
        logs.append("В спину! Дополнительный урон.")
    if sk.effect_key == "low_hp_bonus":
        php = int(state["player_hp"]) / max(1, int(state["player_hp_max"]))
        if php < 0.42:
            dmg = int(dmg * 1.38)
            logs.append("Кровь усиливает ярость!")

    crit = formulas.roll_crit(luck, crit_bonus_flat=float(mods.get("crit_bonus", 0.0)))
    if crit:
        dmg = int(dmg * formulas.crit_multiplier())

    dmg = _apply_weapon_mastery_to_damage(state, dmg)
    dmg = apply_elixir_buffs(state, dmg)
    dmg = combo_apply_outgoing_damage(state, dmg, logs)
    before_flat = dmg
    flat_el = int(state.get("weapon_rune_flat_elemental", 0))
    scaled_elem = (
        int(round(elem_skill * (before_flat / max(1, dmg_start)))) if elem_skill > 0 else 0
    )
    dmg += flat_el
    rline = _rune_added_damage_log_line(scaled_elem, flat_el)
    if rline:
        logs.append(rline)
    else:
        _maybe_log_rune_element_hidden_by_armor(
            state,
            logs,
            elem_bonus_pct=elem_for_tip,
            scaled_elem=scaled_elem,
            flat_el=flat_el,
        )
    logs.extend(_rune_status_proc_logs(state))

    if sk.effect_key == "burn" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect(
            "monster",
            state,
            "Поджог",
            "burn",
            3,
            {"potency_percent": 5},
        )
        logs.append("Враг горит!")
    if sk.effect_key == "freeze" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Враг заледенел и пропустит ход!")
    if sk.effect_key == "paralyze" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Паралич! Враг может пропустить ход.")
    if sk.effect_key == "stun" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Оглушение! Враг пропустит ход.")
    if sk.effect_key == "root" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_skip_next"] = True
        logs.append("Капкан! Враг пропустит ход.")
    if sk.effect_key == "slow" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        state["monster_outgoing_mult"] = min(float(state.get("monster_outgoing_mult", 1.0)), 0.78)
        state["monster_debuff_turns"] = max(int(state.get("monster_debuff_turns", 0)), 2)
        logs.append("Оковы: враг бьёт слабее (~−22% урона, 2 х.).")
    if sk.effect_key == "poison" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect(
            "monster",
            state,
            "Яд",
            "poison",
            3,
            {"potency_percent": 3},
        )
        logs.append("Яд разъедает врага!")
    if sk.effect_key == "bleed" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect(
            "monster",
            state,
            "Кровотечение",
            "bleed",
            3,
            {"potency_percent": 4},
        )
        logs.append("Кровотечение!")

    # Проклятие (снижает урон игрока от навыков тоже)
    pdm = float(state.get("player_damage_mult", 1.0))
    if pdm < 0.999:
        dmg = max(1, int(dmg * pdm))

    dmg, _cxs = coliseum_hooks.after_player_damage_to_monster(state, dmg)
    logs.extend(_cxs)
    if dmg <= 0:
        return logs, "continue", 0

    # Щит монстра (valkyrie) блокирует удар навыком
    if check_and_consume_monster_shield(state, logs):
        # MP потрачено, кулдаун поставлен, но урон поглощён
        state["skill_cd"][str(index)] = sk.cooldown
        return logs, "continue", 0

    # Поглощение рун голема
    dmg = apply_rune_golem_absorb(state, dmg, logs)

    tag = "🔮" if sk.kind == "mag" else "🗡️"
    if crit:
        logs.append(f"→ 👤 Герой: {tag} {sk.name}: {dmg} урона [КРИТ💥]")
    else:
        logs.append(f"→ 👤 Герой: {tag} {sk.name}: {dmg} урона")

    apply_equipment_on_hit_procs(state, mods, logs)

    mon["hp"] = max(0, mhp - dmg)
    passive_gear.apply_lifesteal_for_damage(state, dmg, logs)
    lnx2 = maybe_lightning_execute_after_monster_damaged(state, logs)
    if lnx2 == "win":
        udg2: list[str] = []
        if check_zombie_undying(state, udg2):
            logs.extend(udg2)
        else:
            record_player_last_damage_to_monster(state, dmg)
            _mark_weapon_mastery_strike(state)
            apply_shatter_death(state, logs)
            return logs, "win", dmg
    record_player_last_damage_to_monster(state, dmg)
    _mark_weapon_mastery_strike(state)

    if sk.effect_key == "self_bleed" and sk.effect_chance > 0 and effects.roll_chance(sk.effect_chance):
        effects.add_effect("player", state, "Кровожадность", "bleed", 2, {"potency_percent": 2})
        logs.append("Ты ранишь себя в ярости…")

    if sk.effect_key == "drain":
        ch = sk.effect_chance if sk.effect_chance > 0 else 1.0
        if effects.roll_chance(ch):
            heal = max(1, int(dmg * 0.35))
            curp = int(state["player_hp"])
            mxp = int(state["player_hp_max"])
            state["player_hp"] = min(mxp, curp + heal)
            logs.append(f"↩️ Поглощение жизни: +{heal} HP.")

    if int(mon["hp"]) <= 0:
        # Нежить (zombie): выживает один раз
        undying_logs: list[str] = []
        if check_zombie_undying(state, undying_logs):
            logs.extend(undying_logs)
            return logs, "continue", dmg
        apply_shatter_death(state, logs)
        return logs, "win", dmg
    return logs, "continue", dmg


_ELEMENT_INCOMING_RESIST: dict[str, tuple[str, str, str]] = {
    "fire": ("player_fire_resist_pct", "🔥", "огню"),
    "ice": ("player_ice_resist_pct", "❄️", "льду"),
    "lightning": ("player_lightning_resist_pct", "⚡", "молнии"),
    "poison": ("player_poison_resist_pct", "☠️", "яду"),
    "dark": ("player_dark_resist_pct", "🌑", "тьме"),
}


def _coliseum_bump_monster_turn(state: dict[str, Any], logs: list[str]) -> None:
    state["monster_turn"] = int(state.get("monster_turn", 0)) + 1
    logs.extend(coliseum_hooks.after_monster_turn_increment(state))


def _apply_elemental_resist_to_incoming_damage(
    state: dict[str, Any],
    monster: dict[str, Any],
    dmg: int,
    logs: list[str],
) -> int:
    """Снижает входящий урон, если у игрока сопротивление стихии атакующего монстра."""
    el = str(monster.get("element") or "").strip().lower()
    meta = _ELEMENT_INCOMING_RESIST.get(el)
    if meta is None:
        return dmg
    sk, icon, label_ru = meta
    rp = int(state.get(sk, 0) or 0)
    if rp <= 0:
        return dmg
    factor = 1.0 - min(0.75, rp / 100.0)
    new_d = max(1, int(round(dmg * factor)))
    if new_d < dmg:
        logs.append(f"{icon} Сопротивление {label_ru}: урон {dmg} → {new_d}.")
    return new_d


def monster_turn(state: dict[str, Any]) -> tuple[list[str], Outcome]:
    logs: list[str] = []
    m = _m(state)
    tk = str(m.get("template_key", ""))

    logs.extend(monster_ai.update_monster_mode(state))
    logs.extend(monster_ai.sync_boss_phase(state))

    # ── Эффекты этажа (Ауры 21-30) ──
    logs.extend(apply_floor_aura_effects(state))

    # ── Уникальные способности до хода (регенерация, щит, дыхание) ───────────
    pre_logs: list[str] = []
    apply_pre_turn_abilities(state, pre_logs)
    logs.extend(pre_logs)

    if state.get("monster_skip_next"):
        state["monster_skip_next"] = False
        logs.append("Враг пропускает ход.")
        _coliseum_bump_monster_turn(state, logs)
        return logs, "continue"

    dodge_flat = float(_mods(state).get("dodge_bonus", 0.0)) + float(state.get("player_temp_dodge", 0.0))
    if formulas.roll_dodge(int(_stats(state)["dex"]), dodge_bonus_flat=dodge_flat):
        logs.append("🏃 Ты увернулся от атаки!")
        _coliseum_bump_monster_turn(state, logs)
        return logs, "continue"

    action = monster_ai.decide_action(state)

    if action == "taunt_only":
        logs.append(f"💬 «{monster_ai.pick_taunt(m['name'], tk)}»")
        _coliseum_bump_monster_turn(state, logs)
        return logs, "continue"

    php = int(state["player_hp"]) / max(1, int(state["player_hp_max"]))
    if php > 0.80 and random.random() < 0.35:
        logs.append(f"💬 «{monster_ai.pick_provocation_taunt(m['name'], tk)}»")

    if action == "fortify":
        state["monster_fortify_flat"] = 8
        state["monster_fortify_turns"] = 3
        logs.append(f"🛡️ {m.get('emoji', '👹')} Укрепление! Броня +8 на 3 хода.")
        _coliseum_bump_monster_turn(state, logs)
        return logs, "continue"

    mult = monster_ai.monster_damage_multiplier(state)
    atk = int(m["atk"])
    out_m = float(state.get("monster_outgoing_mult", 1.0))
    base = int(atk * random.uniform(0.9, 1.1) * mult * out_m)
    base = max(1, int(base * float(MONSTER_DAMAGE_DEALT_MULT)))
    defense = player_defense_value(state)
    raw_pen = m.get("armor_penetration", None)
    if raw_pen is not None:
        try:
            pen = float(raw_pen)
        except (TypeError, ValueError):
            pen = (
                float(MONSTER_ARMOR_PENETRATION_MAJOR_BOSS)
                if bool(m.get("is_major_boss")) or bool(m.get("is_mini_boss"))
                else float(MONSTER_ARMOR_PENETRATION)
            )
    else:
        pen = (
            float(MONSTER_ARMOR_PENETRATION_MAJOR_BOSS)
            if bool(m.get("is_major_boss")) or bool(m.get("is_mini_boss"))
            else float(MONSTER_ARMOR_PENETRATION)
        )
    # Дополнительное пробивание от уникальной способности монстра
    extra_pierce = get_extra_pierce_fraction(tk)
    if extra_pierce > 0:
        pen = min(0.95, pen + extra_pierce)
        if not state.get("ability_pierce_logged"):
            state["ability_pierce_logged"] = True
            logs.append(f"⚔️ Враг пробивает броню (+{int(extra_pierce * 100)}% игнора).")

    pen = max(0.0, min(0.95, pen))
    eff_defense = int(defense * (1.0 - pen))

    cd = int(state.get("monster_special_cd", 0))
    is_special = action == "special" and cd == 0
    if is_special:
        base = int(base * 1.5)
        logs.append(f"Враг применил {monster_ai.pick_skill_line(state, special=True)}!")
        state["monster_special_cd"] = 2
    else:
        logs.append(f"Враг: {monster_ai.pick_skill_line(state, special=False)}.")

    # Огненное дыхание (drake: каждые N ходов — ×2 урон)
    if state.pop("monster_breath_active", False):
        base = int(base * 2.0)
        logs.append(f"🐉 {m.get('emoji', '🐉')} <b>Огненное дыхание!</b> Урон удвоен!")

    if state.get("player_block_next"):
        state["player_block_next"] = False
        counter = max(1, int(base * 0.5))
        m["hp"] = max(0, int(m["hp"]) - counter)
        record_player_last_damage_to_monster(state, counter)
        logs.append(f"🛡️ Блок! Контрудар: −{counter} HP врагу.")
        if int(m["hp"]) <= 0:
            _coliseum_bump_monster_turn(state, logs)
            return logs, "win"

    dmg = max(1, base - eff_defense)
    ftkm = float(state.get("fe_monster_to_player_mult", 1.0))
    if ftkm < 0.999:
        dmg = max(1, int(round(dmg * ftkm)))
    dtm = float(_mods(state).get("dmg_taken_mult", 1.0))
    if dtm < 0.999:
        dmg = max(1, int(round(dmg * dtm)))
    extra_mult = float(m.get("strike_ailment_mult") or 0.0)
    if extra_mult > 0:
        extra = max(0, int(base * extra_mult))
        if extra > 0:
            dmg += extra
            em = str(m.get("strike_ailment_emoji") or "✨")
            lab = str(m.get("strike_ailment_label_ru") or "особым ударом")
            logs.append(f"{em} Доп. урон {lab}: −{extra} HP")
    dmg = _apply_elemental_resist_to_incoming_damage(state, m, dmg, logs)
    blk_p = float(_mods(state).get("block_chance", 0.0))
    if blk_p > 0.0 and dmg > 0 and random.random() < min(0.85, blk_p):
        new_d = max(1, int(round(dmg * 0.38)))
        if new_d < dmg:
            logs.append("🛡️ Блок экипировки — входящий урон снижен.")
        dmg = new_d
    dmg = coliseum_hooks.mulan_reduce_incoming_damage(state, dmg, logs)
    dmg = companions_mod.apply_tank_intercept_to_player_damage(state, dmg, logs)
    pre_php = int(state["player_hp"])
    shield = int(state.get("player_shield_hp", 0))
    if shield > 0:
        absorbed = min(shield, dmg)
        state["player_shield_hp"] = shield - absorbed
        dmg -= absorbed
        if absorbed > 0:
            logs.append(f"🛡️ Щит поглотил {absorbed} урона.")
    state["player_hp"] = max(0, int(state["player_hp"]) - dmg)
    if int(state["player_hp"]) < pre_php:
        combo_break_on_player_hurt(state)
    if dmg > 0:
        em = str(m.get("emoji") or "👹")
        mn = html.escape(str(m.get("name") or "Враг"))
        logs.append(f"→ {em} <b>{mn}</b>: −{dmg} HP")
        record_monster_last_damage_to_player(state, dmg)
        if int(state["player_hp"]) > 0:
            if bool(m.get("applies_poison_on_hit")) and random.random() < 0.42:
                effects.add_effect(
                    "player",
                    state,
                    "Яд",
                    "poison",
                    3,
                    {"potency_percent": 4},
                )
                logs.append("☠️ Яд проникает в раны!")
            # Уникальные постатаки монстра (яд, ожог, оглушение, проклятие…)
            post_logs: list[str] = []
            apply_post_hit_abilities(state, dmg, post_logs)
            logs.extend(post_logs)

    _coliseum_bump_monster_turn(state, logs)

    # Двойная атака (time_phantom)
    if int(state["player_hp"]) > 0 and roll_monster_double_turn(state):
        logs.append(f"⏩ <b>Временной скачок!</b> Враг атакует снова!")
        base2 = int(atk * random.uniform(0.85, 1.05) * mult * out_m)
        base2 = max(1, int(base2 * float(MONSTER_DAMAGE_DEALT_MULT)))
        dmg2 = max(1, base2 - eff_defense)
        if ftkm < 0.999:
            dmg2 = max(1, int(round(dmg2 * ftkm)))
        if dtm < 0.999:
            dmg2 = max(1, int(round(dmg2 * dtm)))
        dmg2 = _apply_elemental_resist_to_incoming_damage(state, m, dmg2, logs)
        blk_p2 = float(_mods(state).get("block_chance", 0.0))
        if blk_p2 > 0.0 and dmg2 > 0 and random.random() < min(0.85, blk_p2):
            nd2 = max(1, int(round(dmg2 * 0.38)))
            if nd2 < dmg2:
                logs.append("🛡️ Блок экипировки — второй удар ослаблен.")
            dmg2 = nd2
        dmg2 = coliseum_hooks.mulan_reduce_incoming_damage(state, dmg2, logs)
        dmg2 = companions_mod.apply_tank_intercept_to_player_damage(state, dmg2, logs)
        shield2 = int(state.get("player_shield_hp", 0))
        if shield2 > 0:
            absorbed2 = min(shield2, dmg2)
            state["player_shield_hp"] = shield2 - absorbed2
            dmg2 -= absorbed2
            if absorbed2 > 0:
                logs.append(f"🛡️ Щит поглотил {absorbed2} урона.")
        state["player_hp"] = max(0, int(state["player_hp"]) - dmg2)
        if dmg2 > 0:
            combo_break_on_player_hurt(state)
            logs.append(f"→ {m.get('emoji', '👹')} Второй удар: −{dmg2} HP")
            record_monster_last_damage_to_player(state, dmg2)

    if int(state["player_hp"]) <= 0:
        return logs, "lose"
    return logs, "continue"


def opening_taunt(state: dict[str, Any]) -> str:
    return monster_ai.opening_taunt_line(state)


def end_round_tick(state: dict[str, Any]) -> list[str]:
    """Конец раунда: длительности эффектов и ослабление брони."""
    logs: list[str] = []
    logs.extend(effects.tick_effect_turns("player", state))
    logs.extend(effects.tick_effect_turns("monster", state))
    if int(state.get("monster_def_mod", 0)) > 0:
        state["monster_def_mod"] = max(0, int(state["monster_def_mod"]) - 1)
    ft = int(state.get("monster_fortify_turns", 0))
    if ft > 0:
        state["monster_fortify_turns"] = ft - 1
        if int(state["monster_fortify_turns"]) <= 0:
            state["monster_fortify_flat"] = 0
            logs.append("🛡️ Укрепление врага спало.")

    td = int(state.get("player_temp_dodge_turns", 0))
    if td > 0:
        state["player_temp_dodge_turns"] = td - 1
        if int(state["player_temp_dodge_turns"]) <= 0:
            state["player_temp_dodge"] = 0.0
            logs.append("💨 Бонус к уклонению спал.")

    pft = int(state.get("player_fortify_turns", 0))
    if pft > 0:
        state["player_fortify_turns"] = pft - 1
        if int(state["player_fortify_turns"]) <= 0:
            state["player_fortify_bonus"] = 0
            logs.append("🛡️ Твоё укрепление спало.")

    md = int(state.get("monster_debuff_turns", 0))
    if md > 0:
        state["monster_debuff_turns"] = md - 1
        if int(state["monster_debuff_turns"]) <= 0:
            state["monster_outgoing_mult"] = 1.0
            logs.append("🌫️ Ослабление атаки врага спало.")

    # Тик проклятия (снижение урона игрока)
    pc = int(state.get("player_curse_turns", 0))
    if pc > 0:
        state["player_curse_turns"] = pc - 1
        if int(state["player_curse_turns"]) <= 0:
            state["player_damage_mult"] = 1.0
            logs.append("🌑 Проклятие спало.")

    return logs
