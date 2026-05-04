"""Топ-10 по трём профессиям мастерской; кэш в app_global + флаги титулов в meta."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.app_global import AppGlobal
from db.models.character import Character
from game.crafting.recipes_data import PROF_ALCHEMIST, PROF_BLACKSMITH, PROF_JEWELER
from game.crafting.workshop_meta import WORKSHOP_META_KEY


async def _ensure_app(session: AsyncSession) -> AppGlobal:
    row = await session.get(AppGlobal, 1)
    if row is None:
        row = AppGlobal(id=1, payload={})
        session.add(row)
        await session.flush()
    return row


async def refresh_leaderboards(session: AsyncSession) -> None:
    r = await session.execute(select(Character.id, Character.display_name, Character.meta_progress))
    rows = r.all()
    buckets: dict[str, list[tuple[int, int, int, str]]] = {
        PROF_BLACKSMITH: [],
        PROF_ALCHEMIST: [],
        PROF_JEWELER: [],
    }
    for cid, name, mp in rows:
        if not isinstance(mp, dict):
            continue
        ws = mp.get(WORKSHOP_META_KEY)
        if not isinstance(ws, dict):
            continue
        pls = ws.get("prof_levels") or {}
        pxp = ws.get("prof_xp") or {}
        for pk in buckets:
            lv = int(pls.get(pk, 0))
            if lv <= 0:
                continue
            xp = int(pxp.get(pk, 0))
            buckets[pk].append((lv, xp, int(cid), str(name)))

    tops: dict[str, list[dict[str, object]]] = {}
    top_sets: dict[str, set[int]] = {}
    for pk, lst in buckets.items():
        lst.sort(key=lambda x: (-x[0], -x[1], x[2]))
        cut = lst[:10]
        tops[pk] = [
            {"character_id": c, "name": n, "level": lv, "xp": xp}
            for lv, xp, c, n in cut
        ]
        top_sets[pk] = {c for _, _, c, _ in cut}

    row = await _ensure_app(session)
    p = dict(row.payload or {})
    p["workshop_lb_v1"] = {"tops": tops, "updated_at": datetime.now(UTC).isoformat(timespec="seconds")}
    row.payload = p

    for cid, _, _ in rows:
        ch = await session.get(Character, int(cid))
        if ch is None:
            continue
        mp = dict(ch.meta_progress or {})
        ws = mp.get(WORKSHOP_META_KEY)
        if not isinstance(ws, dict):
            continue
        cid_int = int(cid)
        tal = dict(ws.get("talismans") or {})
        tal["top_blacksmith"] = cid_int in top_sets[PROF_BLACKSMITH]
        tal["top_alchemist"] = cid_int in top_sets[PROF_ALCHEMIST]
        tal["top_jeweler"] = cid_int in top_sets[PROF_JEWELER]
        ws["talismans"] = tal
        mp[WORKSHOP_META_KEY] = ws
        ch.meta_progress = mp
        flag_modified(ch, "meta_progress")

    await session.flush()


def cached_leaderboard_html(session_payload: dict | None) -> str:
    if not isinstance(session_payload, dict):
        return "<i>Рейтинг ещё не собран.</i>"
    raw = session_payload.get("workshop_lb_v1") or {}
    tops = raw.get("tops") or {}
    if not tops:
        return "<i>Пока нет данных рейтинга.</i>"
    lines: list[str] = ["🏆 <b>Мастера (топ-10)</b>", ""]
    labels = {
        PROF_BLACKSMITH: "⚒️ Кузнецы",
        PROF_ALCHEMIST: "⚗️ Алхимики",
        PROF_JEWELER: "💎 Ювелиры",
    }
    for pk, title in labels.items():
        lines.append(f"<b>{title}</b>")
        for i, row in enumerate(tops.get(pk) or [], start=1):
            nm = str(row.get("name", "?"))[:40]
            lv = int(row.get("level", 0))
            lines.append(f"  {i}. {nm} — ур. {lv}")
        lines.append("")
    return "\n".join(lines).strip()
