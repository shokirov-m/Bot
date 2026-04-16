"""HTML-сводки для админ-команд.

Команды /admin (ban, give, rollback, рассылки и т.д.) и колбэки панели
реализованы в `bot/handlers/admin.py`; этот модуль — только форматирование
виджетов вроде сводки дашборда (`format_dashboard_html`).
"""

from __future__ import annotations

import html
from typing import Any


def format_dashboard_html(stats: dict[str, Any]) -> str:
    top_u = stats.get("top_username")
    top_user_line = (
        f"@{html.escape(top_u)}"
        if top_u
        else "—"
    )
    return (
        "📊 <b>Сводка бота</b>\n"
        f"Пользователей: <b>{stats.get('total_users', 0)}</b> "
        f"(забанено: <b>{stats.get('banned', 0)}</b>)\n"
        f"Персонажей: <b>{stats.get('total_chars', 0)}</b>\n"
        f"Активных сегодня: <b>{stats.get('active_today', 0)}</b>\n"
        f"Среднее золото (персонажи не в бане): <b>{stats.get('avg_gold', 0)}</b>\n"
        f"Рекорд этажа: <b>{stats.get('top_floor', 0)}</b> "
        f"({html.escape(str(stats.get('top_display_name', '—')))}, {top_user_line})\n"
        f"Алерты 24ч: <b>{stats.get('alerts_24h', 0)}</b> "
        f"(CRITICAL: <b>{stats.get('critical_24h', 0)}</b>)\n"
        f"ANTICHEAT: <code>{html.escape(str(stats.get('anticheat_enabled', False)))}</code>\n"
        f"💸 <b>Sinks (meta):</b> лотерея потрачено суммарно <b>{stats.get('econ_lottery_spent_sum', 0):,}</b> 💰 · "
        f"пожертвования <b>{stats.get('econ_tithe_sum', 0):,}</b> 💰 · "
        f"должников ростовщику <b>{stats.get('econ_debtor_count', 0)}</b> "
        f"(долг <b>{stats.get('econ_debt_sum', 0):,}</b> 💰) · "
        f"опека сейфа: <b>{stats.get('econ_bank_custody_count', 0)}</b> героев\n"
        f"<i>QA: этажи 3/31/61/91 — город, «Экономика», стражник, кузница.</i>"
    )
