from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 11, 0, 0, tzinfo=timezone.utc)


def _candle(
    *,
    high: Decimal,
    is_closed: bool,
    minute: int,
    open_price: Decimal = Decimal("100"),
    low: Decimal = Decimal("95"),
    close: Decimal = Decimal("100"),
) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="source-1",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=open_price,
        high=high,
        low=low,
        close=close,
        is_closed=is_closed,
    )


def test_higher_high_returns_true_when_current_high_is_greater() -> None:
    previous = _candle(high=Decimal("105"), is_closed=True, minute=0)
    current = _candle(high=Decimal("107"), is_closed=True, minute=1)

    assert FeatureEngine.higher_high(current, previous) is True


def test_higher_high_returns_false_when_current_high_is_lower() -> None:
    previous = _candle(high=Decimal("105"), is_closed=True, minute=0)
    current = _candle(high=Decimal("104"), is_closed=True, minute=1)

    assert FeatureEngine.higher_high(current, previous) is False


def test_higher_high_returns_false_when_highs_are_equal() -> None:
    previous = _candle(high=Decimal("105"), is_closed=True, minute=0)
    current = _candle(high=Decimal("105"), is_closed=True, minute=1)

    assert FeatureEngine.higher_high(current, previous) is False


def test_higher_high_returns_none_when_current_candle_is_open() -> None:
    previous = _candle(high=Decimal("105"), is_closed=True, minute=0)
    current = _candle(high=Decimal("107"), is_closed=False, minute=1)

    assert FeatureEngine.higher_high(current, previous) is None


def test_higher_high_returns_none_when_previous_candle_is_open() -> None:
    previous = _candle(high=Decimal("105"), is_closed=False, minute=0)
    current = _candle(high=Decimal("107"), is_closed=True, minute=1)

    assert FeatureEngine.higher_high(current, previous) is None


def test_higher_high_depends_only_on_high_values() -> None:
    previous_a = _candle(
        high=Decimal("105"),
        is_closed=True,
        minute=0,
        open_price=Decimal("100"),
        low=Decimal("95"),
        close=Decimal("104"),
    )
    current_a = _candle(
        high=Decimal("107"),
        is_closed=True,
        minute=1,
        open_price=Decimal("103"),
        low=Decimal("102"),
        close=Decimal("106"),
    )
    previous_b = _candle(
        high=Decimal("105"),
        is_closed=True,
        minute=2,
        open_price=Decimal("50"),
        low=Decimal("10"),
        close=Decimal("90"),
    )
    current_b = _candle(
        high=Decimal("107"),
        is_closed=True,
        minute=3,
        open_price=Decimal("80"),
        low=Decimal("20"),
        close=Decimal("30"),
    )

    assert FeatureEngine.higher_high(current_a, previous_a) is True
    assert FeatureEngine.higher_high(current_b, previous_b) is True
