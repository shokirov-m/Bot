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
        f"в банковских сейфах <b>{stats.get('econ_safe_gold_sum', 0):,}</b> 💰 "
        f"(<b>{stats.get('econ_safe_user_count', 0)}</b> героев с остатком) · "
        f"должников ростовщику <b>{stats.get('econ_debtor_count', 0)}</b> "
        f"(долг <b>{stats.get('econ_debt_sum', 0):,}</b> 💰)\n"
        f"<i>QA: этажи 3/31/61/91 — город, «Экономика», стражник, кузница.</i>"
    )


def format_referrals_admin_html(
    rows: list[tuple[int, int, str | None, int]],
    *,
    total_with_referrer: int,
    limit_shown: int,
) -> str:
    """Сводка для админки: сколько аккаунтов пришло по чьей реф-ссылке."""
    lines: list[str] = [
        "👥 <b>Регистрации по реферальной ссылке</b>",
        f"Всего аккаунтов с привязкой к пригласившему: <b>{total_with_referrer}</b>",
    ]
    if not rows:
        lines.append("\n<i>Пока нет записей <code>referred_by_user_id</code> в базе.</i>")
        return "\n".join(lines)
    shown_sum = sum(n for *_, n in rows)
    if shown_sum < total_with_referrer:
        lines.append(
            f"\n<i>В списке не все пригласившие: топ-<b>{limit_shown}</b> по числу регистраций "
            f"(сумма в таблице <b>{shown_sum}</b> из <b>{total_with_referrer}</b> аккаунтов с реф-связью).</i>",
        )
    lines.append("\n<b>Пригласивший</b> → <b>сколько зарегистрировалось</b>\n")
    for _inv_id, tid, username, n in rows:
        un = f"@{html.escape(username)}" if username else "—"
        lines.append(f"<code>{tid}</code> {un} → <b>{n}</b>")
    return "\n".join(lines)


def format_admin_player_snapshot_html(
    *,
    telegram_id: int,
    username: str | None,
    display_name: str,
    level: int,
    floor_number: int,
    class_key: str,
    is_banned: bool,
    hp_current: int,
    hp_max: int,
    mp_current: int,
    mp_max: int,
    gold: int,
    unspent_stat_points: int = 0,
    equipped_lines: list[str],
    account_created_at_utc: str,
    hero_created_at_utc: str,
    estimated_playtime_ru: str,
    last_activity_utc: str,
    clan_line: str = "",
    arena_mmr_line: str = "",
    titles_line: str = "",
    mercenaries_line: str = "",
    path_rank_line: str = "",
) -> str:
    """Краткий статус героя и надетые вещи (админка)."""
    ban = "🚫 <b>бан</b>" if is_banned else "✅ активен"
    un = f"@{html.escape(username)}" if username else "—"
    eq_block = "\n".join(equipped_lines) if equipped_lines else "<i>Ничего не надето.</i>"
    pts = int(unspent_stat_points)
    pts_line = f" · своб. очки стата: <b>{pts}</b> <i>(/stats)</i>"
    activity_block = (
        f"Аккаунт с: <b>{html.escape(account_created_at_utc)}</b> · герой с: <b>{html.escape(hero_created_at_utc)}</b>\n"
        f"Время в игре (оценка): <b>{html.escape(estimated_playtime_ru)}</b>\n"
        f"Последняя активность: <b>{html.escape(last_activity_utc)}</b>\n"
        f"<i>Оценка времени — по апдейтам Telegram; между событиями не больше 12 мин за раз, перерыв &gt;48ч не суммируется.</i>\n\n"
    )
    extra = ""
    if clan_line:
        extra += f"{html.escape(clan_line)}\n"
    if arena_mmr_line:
        extra += f"{html.escape(arena_mmr_line)}\n"
    if path_rank_line:
        extra += f"{html.escape(path_rank_line)}\n"
    if titles_line:
        extra += f"{html.escape(titles_line)}\n"
    if mercenaries_line:
        extra += f"{html.escape(mercenaries_line)}\n"
    if extra:
        extra = extra.rstrip() + "\n\n"

    return (
        f"👤 <b>{html.escape(display_name)}</b>\n"
        f"TG <code>{telegram_id}</code> {un}\n"
        f"{ban} · ур. <b>{level}</b> · этаж <b>{floor_number}</b> · класс <code>{html.escape(class_key)}</code>{pts_line}\n"
        f"HP <b>{hp_current}</b>/<b>{hp_max}</b> · MP <b>{mp_current}</b>/<b>{mp_max}</b> · 💰 <b>{gold}</b>\n\n"
        f"{extra}"
        f"{activity_block}"
        f"<b>Надето:</b>\n{eq_block}"
    )
