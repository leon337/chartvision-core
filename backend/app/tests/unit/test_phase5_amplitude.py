from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)


def _candle(*, high: Decimal, low: Decimal, is_closed: bool) -> Candle:
    return Candle(
        source_id="source-1",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=BASE,
        close_time=BASE + timedelta(minutes=1),
        open=low,
        high=high,
        low=low,
        close=high,
        is_closed=is_closed,
    )


def test_candle_amplitude_returns_absolute_price_range() -> None:
    candle = _candle(high=Decimal("105"), low=Decimal("98"), is_closed=True)

    result = FeatureEngine.candle_amplitude(candle)

    assert isinstance(result, Decimal)
    assert result == Decimal("7")


def test_candle_amplitude_returns_zero_for_equal_high_and_low() -> None:
    candle = _candle(high=Decimal("100"), low=Decimal("100"), is_closed=True)

    assert FeatureEngine.candle_amplitude(candle) == Decimal("0")


def test_candle_amplitude_preserves_decimal_values_without_float() -> None:
    candle = _candle(high=Decimal("101.25"), low=Decimal("99.75"), is_closed=True)

    result = FeatureEngine.candle_amplitude(candle)

    assert isinstance(result, Decimal)
    assert result == Decimal("1.50")


def test_candle_amplitude_does_not_depend_on_is_closed() -> None:
    high = Decimal("104.50")
    low = Decimal("99.25")
    open_candle = _candle(high=high, low=low, is_closed=False)
    closed_candle = _candle(high=high, low=low, is_closed=True)

    assert FeatureEngine.candle_amplitude(open_candle) == Decimal("5.25")
    assert FeatureEngine.candle_amplitude(closed_candle) == Decimal("5.25")
