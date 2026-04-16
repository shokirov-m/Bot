"""Кланы: создание, вступление, ссылка на чат, опыт за победы."""

from __future__ import annotations

import html
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.clan import Clan
from db.models.character import Character
from db.repository import clan_repo

_NAME_RE = re.compile(r"^[\w\s\-\.А-Яа-яЁё]{2,64}$")


async def on_monster_win_add_clan_xp(session: AsyncSession, character: Character, *, delta: int = 5) -> None:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return
    await clan_repo.add_clan_xp(session, clan, delta)


async def try_create_clan(session: AsyncSession, leader: Character, raw_name: str) -> tuple[bool, str]:
    name = (raw_name or "").strip()
    if not _NAME_RE.match(name):
        return False, "Имя клана: 2–64 символа (буквы, цифры, пробел, дефис)."
    if await clan_repo.get_membership(session, int(leader.id)) is not None:
        return False, "Ты уже в клане."
    exists = await session.execute(select(Clan.id).where(Clan.name == name))
    if exists.scalar_one_or_none() is not None:
        return False, "Такое имя клана уже занято."
    c = await clan_repo.create_clan(session, name=name, leader=leader)
    return (
        True,
        f"Клан <b>{html.escape(name)}</b> создан. ID клана: <code>{c.id}</code>.\n"
        f"Игроки вступают: <code>/clan join {c.id}</code>",
    )


async def try_join_clan(session: AsyncSession, character: Character, clan_id: int) -> tuple[bool, str]:
    if await clan_repo.get_membership(session, int(character.id)) is not None:
        return False, "Ты уже в клане."
    clan = await clan_repo.get_clan(session, int(clan_id))
    if clan is None:
        return False, "Клан с таким ID не найден."
    await clan_repo.add_member(session, clan_id=int(clan.id), character=character)
    return True, f"Добро пожаловать в клан <b>{html.escape(clan.name)}</b>."


async def try_set_clan_chat(session: AsyncSession, character: Character, url: str) -> tuple[bool, str]:
    u = (url or "").strip()
    if len(u) < 8 or not (u.startswith("http://") or u.startswith("https://") or u.startswith("t.me/")):
        return False, "Укажи ссылку на чат (https://… или t.me/…)."
    if not u.startswith("http"):
        u = "https://" + u.lstrip("/")
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None or m.role != "leader":
        return False, "Только лидер клана может задать ссылку."
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None or int(clan.leader_character_id) != int(character.id):
        return False, "Только лидер может задать ссылку."
    clan.chat_url = u[:256]
    await session.flush()
    return True, "Ссылка на чат клана сохранена."


async def format_clan_card_html(session: AsyncSession, character: Character) -> str:
    m = await clan_repo.get_membership(session, int(character.id))
    if m is None:
        return (
            "⚔️ <b>Кланы</b>\n\n"
            "• <code>/clan create Название</code> — создать клан (ты — лидер).\n"
            "• <code>/clan join ID</code> — вступить по <b>числовому ID</b> клана.\n"
            "• <code>/clan info</code> — карточка твоего клана.\n"
            "• <code>/clan chat https://t.me/...</code> — лидер: ссылка на общий чат.\n\n"
            "<i>За победы над монстрами клан получает XP; уровень растёт автоматически.</i>"
        )
    clan = await clan_repo.get_clan(session, int(m.clan_id))
    if clan is None:
        return "<i>Запись клана не найдена.</i>"
    n = await clan_repo.count_members(session, int(clan.id))
    chat = (
        f'<a href="{html.escape(clan.chat_url)}">перейти в чат</a>'
        if clan.chat_url
        else "<i>не задана — лидер: /clan chat URL</i>"
    )
    return (
        f"⚔️ <b>{html.escape(clan.name)}</b> · ID <code>{clan.id}</code>\n"
        f"👥 Участников: <b>{n}</b> · Ур. клана: <b>{clan.clan_level}</b> · XP: <b>{clan.clan_xp}</b>\n"
        f"💬 Чат: {chat}\n"
        f"<i>Твоя роль: {html.escape(m.role)}</i>"
    )
