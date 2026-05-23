"""
Единый стиль экранов бота: заголовки, секции, цитаты (без замены HP/MP-bar).
"""

from __future__ import annotations

import html
from typing import Any

from utils.telegram.ui import LINE_SEP


def quote_line(text: str, *, max_len: int = 80) -> str:
    t = (text or "").strip()
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return f"💬 <i>«{html.escape(t)}»</i>"


def section(label_emoji: str, label: str, body: str) -> str:
    head = f"{label_emoji} <b>{html.escape(label)}</b>"
    b = (body or "").strip()
    if not b:
        return head
    return f"{head}\n{b}"


def render_screen(
    title: str,
    *blocks: str,
    footer: str | None = None,
    use_sep: bool = False,
) -> str:
    """Собрать HTML-экран: заголовок + блоки + опциональный подвал."""
    parts: list[str] = []
    t = (title or "").strip()
    if t:
        parts.append(t)
    for b in blocks:
        s = (b or "").strip()
        if s:
            parts.append(s)
    if footer and (f := footer.strip()):
        if use_sep:
            parts.append(LINE_SEP)
        parts.append(f)
    if use_sep and len(parts) > 1:
        return f"\n{LINE_SEP}\n".join(parts)
    return "\n".join(parts)


def compact_night_line() -> str:
    return (
        "🌑 <i>Ночь UTC: враги +20% HP/ATK · награда +40% золота и опыта.</i>"
    )


def floor_header_html(floor_number: int, zone_emoji: str, zone_name: str) -> str:
    return (
        f"🏰 <b>Этаж {int(floor_number)}</b> · {zone_emoji} "
        f"<b>{html.escape(zone_name)}</b>"
    )


def truncate_button_label(text: str, max_len: int = 64) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"
