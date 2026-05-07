"""
ORM-модели: импорт всех классов для регистрации в metadata и Alembic.
Порядок: User → Character → зависимые таблицы → AdminLog.
"""

from db.models.user import User
from db.models.character import Character
from db.models.inventory import InventoryItem
from db.models.floor_progress import FloorProgress
from db.models.quest import QuestProgress
from db.models.enchant import EnchantLog
from db.models.admin_log import AdminLog
from db.models.app_global import AppGlobal
from db.models.promo_offer import PromoOffer
from db.models.promo_redemption import PromoRedemption
from db.models.game_event import GameEvent
from db.models.auction_lot import AuctionLot
from db.models.clan import Clan, ClanMembership
from db.models.mercenary import Mercenary

__all__ = [
    "AdminLog",
    "AppGlobal",
    "AuctionLot",
    "Clan",
    "ClanMembership",
    "Character",
    "EnchantLog",
    "FloorProgress",
    "GameEvent",
    "InventoryItem",
    "Mercenary",
    "PromoOffer",
    "PromoRedemption",
    "QuestProgress",
    "User",
]
