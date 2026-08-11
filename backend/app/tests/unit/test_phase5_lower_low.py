from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 11, 0, 0, tzinfo=timezone.utc)


def _candle(
    *,
    low: Decimal,
    is_closed: bool,
    minute: int,
    open_price: Decimal = Decimal("100"),
    high: Decimal = Decimal("110"),
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


def test_lower_low_returns_true_when_current_low_is_lower() -> None:
    previous = _candle(low=Decimal("95"), is_closed=True, minute=0)
    current = _candle(low=Decimal("93"), is_closed=True, minute=1)

    assert FeatureEngine.lower_low(current, previous) is True


def test_lower_low_returns_false_when_current_low_is_greater() -> None:
    previous = _candle(low=Decimal("95"), is_closed=True, minute=0)
    current = _candle(low=Decimal("97"), is_closed=True, minute=1)

    assert FeatureEngine.lower_low(current, previous) is False


def test_lower_low_returns_false_when_lows_are_equal() -> None:
    previous = _candle(low=Decimal("95"), is_closed=True, minute=0)
    current = _candle(low=Decimal("95"), is_closed=True, minute=1)

    assert FeatureEngine.lower_low(current, previous) is False


def test_lower_low_returns_none_when_current_candle_is_open() -> None:
    previous = _candle(low=Decimal("95"), is_closed=True, minute=0)
    current = _candle(low=Decimal("93"), is_closed=False, minute=1)

    assert FeatureEngine.lower_low(current, previous) is None


def test_lower_low_returns_none_when_previous_candle_is_open() -> None:
    previous = _candle(low=Decimal("95"), is_closed=False, minute=0)
    current = _candle(low=Decimal("93"), is_closed=True, minute=1)

    assert FeatureEngine.lower_low(current, previous) is None


def test_lower_low_returns_none_when_both_candles_are_open() -> None:
    previous = _candle(low=Decimal("95"), is_closed=False, minute=0)
    current = _candle(low=Decimal("93"), is_closed=False, minute=1)

    assert FeatureEngine.lower_low(current, previous) is None


def test_lower_low_depends_only_on_low_values() -> None:
    previous_a = _candle(
        low=Decimal("95"),
        is_closed=True,
        minute=0,
        open_price=Decimal("100"),
        high=Decimal("105"),
        close=Decimal("104"),
    )
    current_a = _candle(
        low=Decimal("93"),
        is_closed=True,
        minute=1,
        open_price=Decimal("101"),
        high=Decimal("107"),
        close=Decimal("106"),
    )
    previous_b = _candle(
        low=Decimal("95"),
        is_closed=True,
        minute=2,
        open_price=Decimal("200"),
        high=Decimal("250"),
        close=Decimal("210"),
    )
    current_b = _candle(
        low=Decimal("93"),
        is_closed=True,
        minute=3,
        open_price=Decimal("150"),
        high=Decimal("160"),
        close=Decimal("155"),
    )

    assert FeatureEngine.lower_low(current_a, previous_a) is True
    assert FeatureEngine.lower_low(current_b, previous_b) is True
    assert FeatureEngine.higher_high(current_a, previous_a) is True
    assert FeatureEngine.lower_high(current_b, previous_b) is True


def test_lower_low_and_higher_low_have_expected_relation() -> None:
    previous_lower = _candle(low=Decimal("95"), is_closed=True, minute=0)
    current_lower = _candle(low=Decimal("93"), is_closed=True, minute=1)
    previous_greater = _candle(low=Decimal("95"), is_closed=True, minute=2)
    current_greater = _candle(low=Decimal("97"), is_closed=True, minute=3)
    previous_equal = _candle(low=Decimal("95"), is_closed=True, minute=4)
    current_equal = _candle(low=Decimal("95"), is_closed=True, minute=5)

    assert FeatureEngine.lower_low(current_lower, previous_lower) is True
    assert FeatureEngine.higher_low(current_lower, previous_lower) is False

    assert FeatureEngine.lower_low(current_greater, previous_greater) is False
    assert FeatureEngine.higher_low(current_greater, previous_greater) is True

    assert FeatureEngine.lower_low(current_equal, previous_equal) is False
    assert FeatureEngine.higher_low(current_equal, previous_equal) is False


def test_higher_high_and_lower_low_can_both_be_true() -> None:
    previous = _candle(
        low=Decimal("95"),
        is_closed=True,
        minute=0,
        high=Decimal("105"),
    )
    current = _candle(
        low=Decimal("93"),
        is_closed=True,
        minute=1,
        high=Decimal("107"),
    )

    assert FeatureEngine.higher_high(current, previous) is True
    assert FeatureEngine.lower_low(current, previous) is True
