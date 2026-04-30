"""
Настройки приложения из переменных окружения и файла `.env`.
Путь к `.env` — рядом с этим файлом (каталог `tower_bot/`), независимо от CWD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень пакета tower_bot (где лежат config.py, main.py, .env)
_BASE_DIR = Path(__file__).resolve().parent


def _parse_admin_ids(value: Any) -> list[int]:
    """Парсинг ADMIN_IDS из строки «1,2,3» или пустого значения."""
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    s = str(value).strip()
    if not s:
        return []
    result: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if part:
            result.append(int(part))
    return result


AdminIds = Annotated[list[int], BeforeValidator(_parse_admin_ids)]


class Settings(BaseSettings):
    """Все параметры из ТЗ (технические требования + .env.example)."""

    model_config = SettingsConfigDict(
        env_file=_BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str = Field(description="Токен Telegram-бота от @BotFather")
    BOT_USERNAME: str = Field(
        default="tower_of_trial_bot",
        description="Username бота без @ (ссылки t.me, рефералка)",
    )
    DB_PATH: str = Field(
        default="./data/tower.db",
        description="Путь к SQLite: абсолютный или относительно каталога tower_bot (не CWD)",
    )
    ADMIN_IDS: AdminIds = Field(default_factory=list)
    LOG_LEVEL: str = Field(default="INFO")
    STAMINA_REGEN_INTERVAL: int = Field(
        default=300,
        description="Интервал восстановления 1 ед. стамины, секунды (300 = раз в 5 минут)",
    )
    PASSIVE_HP_MP_INTERVAL_SECONDS: int = Field(
        default=300,
        ge=60,
        description="Интервал полного восстановления HP и MP всем персонажам (фоновая задача), секунды",
    )
    MAX_STAMINA: int = Field(default=25)
    ANTICHEAT_ENABLED: bool = Field(default=True)
    SEASON_DURATION_DAYS: int = Field(default=30)
    DISPLAY_NAME_CHANGE_GOLD: int = Field(
        default=250,
        ge=0,
        description="Стоимость смены отображаемого имени героя (золото)",
    )

    REDIS_URL: str | None = Field(
        default=None,
        description="Если задан — FSM хранится в Redis (переживает перезапуск бота)",
    )
    TELEGRAM_PROXY_URL: str | None = Field(
        default=None,
        description="HTTP(S)-прокси для api.telegram.org (или задайте HTTPS_PROXY в окружении)",
    )

    WEBHOOK_ENABLED: bool = Field(
        default=False,
        description="True — webhook + aiohttp вместо long polling",
    )
    WEBHOOK_BASE_URL: str = Field(
        default="",
        description="Публичный HTTPS URL без завершающего слэша, напр. https://bot.example.com",
    )
    WEBHOOK_PATH: str = Field(default="/webhook")
    WEBHOOK_SECRET: str | None = Field(
        default=None,
        description="Секрет для заголовка X-Telegram-Bot-Api-Secret-Token",
    )
    WEBAPP_HOST: str = Field(default="0.0.0.0")
    WEBAPP_PORT: int = Field(default=8080)

    REQUIRED_CHANNEL_USERNAME: str = Field(
        default="trial_of_darkness",
        description="Канал для ежедневки: username без @ (подписка через get_chat_member)",
    )
    SKIP_CHANNEL_SUBSCRIPTION_CHECK: bool = Field(
        default=False,
        description="True — считать всех подписанными (локальные тесты без канала)",
    )


# Единый экземпляр настроек для импорта из main и сервисов
settings = Settings()


def is_admin(telegram_id: int | None) -> bool:
    """Проверить, является ли пользователь администратором."""
    if telegram_id is None:
        return False
    return int(telegram_id) in settings.ADMIN_IDS
