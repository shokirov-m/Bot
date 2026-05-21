"""
Квесты NPC из паков зон (content/data/packs).

meta_progress:
  pack_materials_v1: {material_id: count}
  pack_npc_quests_v1: {quest_id: {current, target, claimed, npc_id, floor}}
"""

from __future__ import annotations

import html
import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from game.crafting.workshop_meta import add_known_blueprint, profession_level
from game.data.packs import load_zone_pack, npcs_for_floor
from game.tower.progression import floor_data
from game.tower.quests.pack_npc_quests import (
    blueprint_label,
    material_label,
    quests_for_npc_on_floor,
    workshop_profession_key,
)

_META_MATERIALS = "pack_materials_v1"
_META_QUESTS = "pack_npc_quests_v1"


def _meta(character: Character) -> dict:
    return dict(character.meta_progress or {})


def _save_meta(character: Character, meta: dict) -> None:
    character.meta_progress = meta
    flag_modified(character, "meta_progress")


def zone_key_for_floor(floor: int) -> str | None:
    z = floor_data.get_zone_for_floor(int(floor))
    pack = load_zone_pack(z.key)
    if pack.get("zone"):
        return z.key
    return None


def list_npcs_on_floor(floor: int) -> list[dict[str, Any]]:
    zk = zone_key_for_floor(floor)
    if not zk:
        return []
    return npcs_for_floor(zk, int(floor))


def pack_material_count(character: Character, material_id: str) -> int:
    raw = _meta(character).get(_META_MATERIALS) or {}
    if not isinstance(raw, dict):
        return 0
    return max(0, int(raw.get(str(material_id), 0) or 0))


def add_pack_material(character: Character, material_id: str, qty: int) -> None:
    if qty <= 0:
        return
    meta = _meta(character)
    raw = dict(meta.get(_META_MATERIALS) or {})
    mid = str(material_id)
    raw[mid] = max(0, int(raw.get(mid, 0))) + int(qty)
    meta[_META_MATERIALS] = raw
    _save_meta(character, meta)


def consume_pack_material(character: Character, material_id: str, qty: int) -> bool:
    have = pack_material_count(character, material_id)
    if have < qty:
        return False
    meta = _meta(character)
    raw = dict(meta.get(_META_MATERIALS) or {})
    mid = str(material_id)
    raw[mid] = have - int(qty)
    meta[_META_MATERIALS] = raw
    _save_meta(character, meta)
    return True


def _all_quests(character: Character) -> dict[str, dict]:
    raw = _meta(character).get(_META_QUESTS) or {}
    return dict(raw) if isinstance(raw, dict) else {}


def _save_quests(character: Character, data: dict[str, dict]) -> None:
    meta = _meta(character)
    meta[_META_QUESTS] = data
    _save_meta(character, meta)


def get_quest_state(character: Character, quest_id: str) -> dict | None:
    q = _all_quests(character).get(str(quest_id))
    return dict(q) if isinstance(q, dict) else None


def _quest_target(qdef: dict) -> tuple[str, int]:
    tgt = qdef.get("target") or {}
    if isinstance(tgt, dict):
        return str(tgt.get("id") or ""), max(0, int(tgt.get("qty") or 0))
    return "", 0


def _current_for_quest(character: Character, qdef: dict) -> int:
    obj = str(qdef.get("objective") or "collect_material")
    if obj == "collect_material":
        mat_id, need = _quest_target(qdef)
        if not mat_id:
            return 0
        return min(pack_material_count(character, mat_id), need)
    return 0


def _profession_ok(character: Character, npc: dict, qdef: dict) -> bool:
    tier_need = qdef.get("profession_tier_min")
    if tier_need is None:
        return True
    prof = workshop_profession_key(str(npc.get("profession") or ""))
    return profession_level(character, prof) >= int(tier_need)


def greeting_line(character: Character, npc: dict, *, reputation: str = "neutral") -> str:
    name = html.escape((character.name or "странник")[:40])
    greets = npc.get("greeting_by_reputation") or {}
    tpl = greets.get(reputation) or greets.get("neutral") or "{player_name}."
    return html.escape(tpl.replace("{player_name}", character.name or "странник"))


def format_hub_html(character: Character, floor: int) -> str:
    zk = zone_key_for_floor(floor) or "?"
    npcs = list_npcs_on_floor(floor)
    lines = [
        f"🦇 <b>Мастера Кровавого Шпиля</b> · этаж <b>{int(floor)}</b>",
        "<i>Поручения дают материалы и чертежи — не готовую экипировку.</i>",
        "",
    ]
    if not npcs:
        lines.append("Сейчас здесь никого из мастеров нет.")
        return "\n".join(lines)
    for npc in npcs:
        emoji = str(npc.get("emoji") or "👤")
        nm = html.escape(str(npc.get("name") or "NPC"))
        prof = html.escape(str(npc.get("profession") or ""))
        qn = len(quests_for_npc_on_floor(npc, floor))
        lines.append(f"{emoji} <b>{nm}</b> · {prof} · поручений: {qn}")
    lines.append("")
    lines.append(f"📦 Материалов в запасе: <b>{_total_materials_stacks(character)}</b> видов")
    stash = format_materials_stash_html(character, zk, limit=8)
    if stash:
        lines.append("")
        lines.append(stash)
    return "\n".join(lines)


def format_materials_stash_html(
    character: Character,
    zone_key: str,
    *,
    limit: int = 12,
) -> str:
    """Список материалов пака в meta_progress."""
    pack = load_zone_pack(zone_key)
    mats = (pack.get("materials") or {}).get("entries") or {}
    if not isinstance(mats, dict):
        return ""
    raw = _meta(character).get(_META_MATERIALS) or {}
    if not isinstance(raw, dict):
        return ""
    rows: list[str] = []
    for mid, cnt in sorted(raw.items(), key=lambda x: -int(x[1] or 0)):
        qty = int(cnt or 0)
        if qty <= 0:
            continue
        name = material_label(zone_key, str(mid))
        rows.append(f"• {html.escape(name)} ×<b>{qty}</b>")
        if len(rows) >= limit:
            break
    if not rows:
        return "<i>Запас пуст — побеждай на ярусах или сдавай поручения.</i>"
    more = _total_materials_stacks(character) - len(rows)
    tail = f"\n<i>…ещё {more} видов</i>" if more > 0 else ""
    return "<b>Запас:</b>\n" + "\n".join(rows) + tail


def _total_materials_stacks(character: Character) -> int:
    raw = _meta(character).get(_META_MATERIALS) or {}
    if not isinstance(raw, dict):
        return 0
    return sum(1 for v in raw.values() if int(v or 0) > 0)


def format_npc_html(character: Character, floor: int, npc_id: str) -> str:
    zk = zone_key_for_floor(floor)
    if not zk:
        return "Зона недоступна."
    npc = npc_by_id(floor, npc_id)
    if npc is None:
        return "NPC не найден."
    lines = [
        f"{npc.get('emoji', '👤')} <b>{html.escape(str(npc.get('name') or npc_id))}</b>",
        f"<i>{greeting_line(character, npc)}</i>",
        "",
    ]
    for qdef in quests_for_npc_on_floor(npc, int(floor)):
        qid = str(qdef.get("id") or "")
        _sync_quest_progress(character, qid, qdef)
        st = get_quest_state(character, qid)
        title = html.escape(str(qdef.get("title") or qid))
        mat_id, need = _quest_target(qdef)
        cur = _current_for_quest(character, qdef) if st else 0
        if st and st.get("claimed"):
            status = "✅ сдано"
        elif st:
            status = f"📋 {cur}/{need}" if need else "📋 в работе"
        elif _profession_ok(character, npc, qdef):
            status = "⚪ доступно"
        else:
            status = "🔒 нужен уровень профессии"
        mat_name = material_label(zk, mat_id) if mat_id else ""
        extra = f" · {html.escape(mat_name)}" if mat_name and need else ""
        lines.append(f"• <b>{title}</b> — {status}{extra}")
    return "\n".join(lines)


def npc_by_id(floor: int, npc_id: str) -> dict[str, Any] | None:
    for npc in list_npcs_on_floor(floor):
        if str(npc.get("id")) == str(npc_id):
            return npc
    return None


def can_take_quest(character: Character, floor: int, npc_id: str, quest_id: str) -> bool:
    npc = npc_by_id(floor, npc_id)
    if npc is None:
        return False
    qdef = _quest_def(npc, quest_id)
    if qdef is None or not _profession_ok(character, npc, qdef):
        return False
    st = get_quest_state(character, quest_id)
    return st is None


def _quest_def(npc: dict, quest_id: str) -> dict | None:
    for q in npc.get("quests") or []:
        if isinstance(q, dict) and str(q.get("id")) == str(quest_id):
            return q
    return None


def take_quest(character: Character, floor: int, npc_id: str, quest_id: str) -> bool:
    if not can_take_quest(character, floor, npc_id, quest_id):
        return False
    npc = npc_by_id(floor, npc_id)
    if npc is None:
        return False
    qdef = _quest_def(npc, quest_id)
    if qdef is None:
        return False
    _, need = _quest_target(qdef)
    all_q = _all_quests(character)
    all_q[str(quest_id)] = {
        "current": 0,
        "target": need,
        "claimed": False,
        "npc_id": str(npc_id),
        "floor": int(floor),
    }
    _save_quests(character, all_q)
    return True


def can_claim_quest(character: Character, quest_id: str) -> bool:
    st = get_quest_state(character, quest_id)
    if st is None or st.get("claimed"):
        return False
    return int(st.get("current", 0)) >= int(st.get("target", 1))


def _sync_quest_progress(character: Character, quest_id: str, qdef: dict) -> None:
    st = get_quest_state(character, quest_id)
    if st is None or st.get("claimed"):
        return
    cur = _current_for_quest(character, qdef)
    _, need = _quest_target(qdef)
    all_q = _all_quests(character)
    row = dict(all_q.get(str(quest_id)) or {})
    row["current"] = cur
    row["target"] = need
    all_q[str(quest_id)] = row
    _save_quests(character, all_q)


async def claim_quest_reward(
    session: AsyncSession,
    character: Character,
    floor: int,
    npc_id: str,
    quest_id: str,
) -> tuple[bool, str]:
    zk = zone_key_for_floor(floor)
    if not zk:
        return False, "Зона недоступна."
    npc = npc_by_id(floor, npc_id)
    if npc is None:
        return False, "NPC не найден."
    qdef = _quest_def(npc, quest_id)
    if qdef is None:
        return False, "Поручение не найдено."
    _sync_quest_progress(character, quest_id, qdef)
    if not can_claim_quest(character, quest_id):
        return False, "Условия ещё не выполнены."
    mat_id, need = _quest_target(qdef)
    if mat_id and need > 0:
        if not consume_pack_material(character, mat_id, need):
            return False, "Не хватает материалов в запасе."

    rewards = qdef.get("rewards") or {}
    parts: list[str] = []
    for row in rewards.get("materials") or []:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("id") or "")
        qty = max(0, int(row.get("qty") or 0))
        if mid and qty:
            add_pack_material(character, mid, qty)
            parts.append(f"{material_label(zk, mid)} ×{qty}")
    for row in rewards.get("blueprints") or []:
        if not isinstance(row, dict):
            continue
        bid = str(row.get("id") or "")
        if bid and add_known_blueprint(character, bid):
            parts.append(blueprint_label(zk, bid))

    all_q = _all_quests(character)
    row = dict(all_q.get(str(quest_id)) or {})
    row["claimed"] = True
    all_q[str(quest_id)] = row
    _save_quests(character, all_q)
    await session.flush()

    if parts:
        return True, "Награда: " + ", ".join(parts)
    return True, "Поручение выполнено."


def maybe_drop_material_on_victory(character: Character, floor: int) -> str | None:
    """После победы на этаже пака — шанс дропа материала (пока фикс. blood_vial)."""
    zk = zone_key_for_floor(floor)
    if zk != "blood_spire":
        return None
    if random.random() > 0.22:
        return None
    choices = ("blood_vial", "bat_wing", "ghoul_hide", "nightshade")
    mid = random.choice(choices)
    add_pack_material(character, mid, 1)
    return material_label(zk, mid)
