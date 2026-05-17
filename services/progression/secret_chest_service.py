"""
Тайник на этаже: закрытый сундук → «Открыть» → пусто / золото (~40–50% от награды
обычного монстра этажа) / мимик (элита этажа, 5%). После победы над мимиком —
случайный предмет из каталога с редкостью по этажу (см. game.items.catalog_loot).
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from db.models.character import Character
from db.repository import floor_progress_repo
from game.enemies.floors.spawns import FloorMonsterSpawn, MonsterTemplate, build_spawns_for_floor
from game.tower.progression.rewards import gold_reward
import services.progression.character_service as character_service
from utils.media.image_assets import secret_chest_png

SECRET_CHEST_PENDING_KEY = "secret_chest_pending_visit"
SECRET_ATTEMPT_KEY = "secret_attempt_visit"

MIMIC_SLOT_CODE = "sec_mimic"
MIMIC_TEMPLATE_KEY = "mimic_chest"
# Шанс предмета из каталога после победы над мимиком (раньше было 100%).
MIMIC_CATALOG_DROP_CHANCE = 0.30

# 5% мимик, 20% золото, 75% пустой ларец
CHEST_MIMIC_CHANCE = 0.05
CHEST_GOLD_CHANCE = 0.20


def _floor_progress_extra_as_dict(raw: object) -> dict[str, object]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _int_from_extra(extra: dict[str, object], key: str, default: int = -10_000) -> int:
    v = extra.get(key, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class SecretSearchOutcome:
    """Шаг 1: показать сундук или короткий alert."""

    alert: str | None
    body_html: str | None
    photo_path: str | None = None


@dataclass(slots=True)
class SecretChestOpenOutcome:
    """Шаг 2: результат открытия."""

    alert: str | None = None
    body_html: str | None = None
    photo_path: str | None = None
    mimic_combat_spawn: FloorMonsterSpawn | None = None


def build_mimic_spawn() -> FloorMonsterSpawn:
    tpl = MonsterTemplate(
        MIMIC_TEMPLATE_KEY,
        "Мимик-сундук",
        "📦",
        "dark",
        "Сундучок злобно щёлкает крышкой — это была ловушка!",
    )
    return FloorMonsterSpawn(
        slot_code=MIMIC_SLOT_CODE,
        template=tpl,
        is_elite=True,
        is_mini_boss=False,
        is_major_boss=False,
    )


def _reference_normal_spawn(floor_n: int) -> FloorMonsterSpawn:
    spawns = build_spawns_for_floor(int(floor_n))
    for s in spawns:
        if not s.is_elite and not s.is_mini_boss and not s.is_major_boss:
            return s
    if spawns:
        return spawns[0]
    ref_tpl = MonsterTemplate("fallback", "Тварь", "👾", "earth", "")
    return FloorMonsterSpawn(
        slot_code="x",
        template=ref_tpl,
        is_elite=False,
        is_mini_boss=False,
        is_major_boss=False,
    )


def chest_gold_roll(floor_n: int) -> int:
    ref = _reference_normal_spawn(floor_n)
    base = gold_reward(int(floor_n), ref)
    mult = random.uniform(0.40, 0.50)
    return max(1, int(base * mult))


async def present_secret_chest(session: AsyncSession, character: Character) -> SecretSearchOutcome:
    """Показать закрытый сундук и зафиксировать ожидание открытия на этом заходе."""
    n = int(character.floor_number)
    if n == 1:
        return SecretSearchOutcome(alert="На первом ярусе только город — тайников здесь нет.", body_html=None)

    row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
    visits = int(row.visits or 0)
    extra = _floor_progress_extra_as_dict(row.extra)

    if _int_from_extra(extra, SECRET_ATTEMPT_KEY) == visits:
        return SecretSearchOutcome(
            alert=(
                "🔍 Тайник уже обыскан.\n\n"
                "После каждой победы в бою на этом этаже тайник обновляется — "
                "победи монстра и попробуй снова."
            ),
            body_html=None,
        )

    if _int_from_extra(extra, SECRET_CHEST_PENDING_KEY) != visits:
        extra[SECRET_CHEST_PENDING_KEY] = visits
        row.extra = extra
        flag_modified(row, "extra")
        await session.flush()

    body = (
        "🧰 <b>Сундук</b>\n"
        "В нише за камнем стоит старый ларец. Крышка задёрнута — "
        "осталось решить, открывать ли её."
    )
    return SecretSearchOutcome(
        alert=None,
        body_html=body,
        photo_path=secret_chest_png("closed"),
    )


async def open_secret_chest(
    session: AsyncSession,
    character: Character,
    *,
    telegram_id: int | None = None,
    username: str | None = None,
    bot: Bot | None = None,
) -> SecretChestOpenOutcome:
    """Открыть сундук: расходует попытку за текущий заход."""
    n = int(character.floor_number)
    if n == 1:
        return SecretChestOpenOutcome(alert="Здесь нет тайников.")

    row = await floor_progress_repo.ensure_floor_row(session, character.id, n)
    visits = int(row.visits or 0)
    extra = _floor_progress_extra_as_dict(row.extra)

    if _int_from_extra(extra, SECRET_ATTEMPT_KEY) == visits:
        return SecretChestOpenOutcome(alert="Тайник уже обыскан. Победи монстра и возвращайся.")

    if _int_from_extra(extra, SECRET_CHEST_PENDING_KEY) != visits:
        return SecretChestOpenOutcome(alert="Сначала нажми «🔮 Тайник», чтобы найти сундук.")

    extra.pop(SECRET_CHEST_PENDING_KEY, None)
    extra[SECRET_ATTEMPT_KEY] = visits
    row.extra = extra
    flag_modified(row, "extra")

    u = random.random()
    if u < CHEST_MIMIC_CHANCE:
        row.secret_rooms_found = int(row.secret_rooms_found) + 1
        await session.flush()
        return SecretChestOpenOutcome(
            body_html=(
                "👅 <b>Это мимик!</b>\n"
                "Крышка отлетает — ларец оживает. Придётся драться, как с элитой этажа!"
            ),
            photo_path=secret_chest_png("mimic"),
            mimic_combat_spawn=build_mimic_spawn(),
        )

    if u < CHEST_MIMIC_CHANCE + CHEST_GOLD_CHANCE:
        amt = chest_gold_roll(n)
        await character_service.add_gold_async(
            session,
            character,
            amt,
            source="secret_chest",
            bot=bot,
            telegram_id=telegram_id,
            username=username,
        )
        row.secret_rooms_found = int(row.secret_rooms_found) + 1
        await session.flush()
        return SecretChestOpenOutcome(
            body_html=(
                f"✨ <b>Награда!</b>\n"
                f"Внутри — пригоршня монет: <b>+{amt}</b> золота "
                f"(примерно как у обычного врага этого яруса, но скромнее)."
            ),
            photo_path=secret_chest_png("gold"),
        )

    row.secret_rooms_found = int(row.secret_rooms_found) + 1
    await session.flush()
    return SecretChestOpenOutcome(
        body_html="📭 <b>Пусто.</b>\nТолько пыль да обломок ржавого гвоздя.",
        photo_path=secret_chest_png("empty"),
    )
