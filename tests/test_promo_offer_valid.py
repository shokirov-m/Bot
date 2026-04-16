from datetime import UTC, datetime, timedelta

from db.models.promo_offer import PromoOffer
from db.repository.promo_offer_repo import offer_is_valid_now


def _offer(**kw) -> PromoOffer:
    base = dict(
        code_key="TEST",
        gold=0,
        xp=0,
        rune_stones=0,
        max_uses=10,
        uses_count=0,
        valid_from=datetime.now(UTC) - timedelta(days=1),
        valid_until=None,
        is_active=True,
        note=None,
        created_by_telegram_id=None,
    )
    base.update(kw)
    return PromoOffer(**base)


def test_offer_valid_active() -> None:
    o = _offer()
    assert offer_is_valid_now(o, now=datetime.now(UTC)) is True


def test_offer_invalid_inactive() -> None:
    o = _offer(is_active=False)
    assert offer_is_valid_now(o) is False


def test_offer_invalid_future() -> None:
    t0 = datetime.now(UTC)
    o = _offer(valid_from=t0 + timedelta(days=1))
    assert offer_is_valid_now(o, now=t0) is False


def test_offer_invalid_past_until() -> None:
    t0 = datetime.now(UTC)
    o = _offer(valid_until=t0 - timedelta(hours=1))
    assert offer_is_valid_now(o, now=t0) is False
