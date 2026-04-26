"""
Сервис AFK-таймера боя.

ВАЖНО: фоновая логика «через N секунд без хода — автоматическое поражение»
ПОЛНОСТЬЮ ОТКЛЮЧЕНА.

Причина: фоновая задача срабатывала уже после того, как игрок открыл /floor,
и засчитывала «фантомное» поражение. В цепочке с настоящим боем это приводило
к двойному штрафу за смерть (наблюдалось списание ~16k золота при потолке 8k),
к низким HP/MP «без видимой смерти» и к самопроизвольному закрытию боя.

Функции `arm_combat_idle_after_player_turn` и `cancel_combat_idle_timer`
оставлены как заглушки, чтобы не править все места их вызова в combat_service.
Если когда-нибудь захочется вернуть AFK-таймер — поставь COMBAT_IDLE_ENABLED=True
и верни тело функции из git-истории этого файла.
"""

from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.fsm.context import FSMContext

# Флаг для возможного возврата фичи. По текущему решению — выключено.
COMBAT_IDLE_ENABLED: bool = False
COMBAT_IDLE_SECONDS: int = 0  # значение оставлено для обратной совместимости импортов

_tasks: dict[int, asyncio.Task] = {}


def cancel_combat_idle_timer(telegram_user_id: int) -> None:
    """Снимает любую залежавшуюся задачу AFK-таймера, если такие были."""
    t = _tasks.pop(int(telegram_user_id), None)
    if t is not None and not t.done():
        t.cancel()


async def arm_combat_idle_after_player_turn(
    *,
    bot: Bot,
    state: FSMContext,
    telegram_user_id: int,
) -> None:
    """
    No-op: AFK-таймер боя отключён.

    Сохраняем сигнатуру и точку отмены — на случай, если где-то остался задел
    с предыдущей задачей (аварийный рестарт без чистой остановки и т.п.).
    """
    cancel_combat_idle_timer(telegram_user_id)
    if not COMBAT_IDLE_ENABLED:
        return
