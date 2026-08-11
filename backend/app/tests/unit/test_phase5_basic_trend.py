from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models.candle import Candle
from app.domain.models.market_features import BasicTrend
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 11, 2, 0, tzinfo=timezone.utc)


def _candle(
    *,
    high: Decimal,
    low: Decimal,
    minute: int,
    is_closed: bool = True,
) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="source-1",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal("100"),
        high=high,
        low=low,
        close=Decimal("100"),
        is_closed=is_closed,
    )


def test_basic_trend_returns_rising_structure_for_two_rising_pairs() -> None:
    candles = (
        _candle(high=Decimal("105"), low=Decimal("95"), minute=0),
        _candle(high=Decimal("106"), low=Decimal("96"), minute=1),
        _candle(high=Decimal("107"), low=Decimal("97"), minute=2),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.RISING_STRUCTURE


def test_basic_trend_returns_falling_structure_for_two_falling_pairs() -> None:
    candles = (
        _candle(high=Decimal("105"), low=Decimal("95"), minute=0),
        _candle(high=Decimal("104"), low=Decimal("94"), minute=1),
        _candle(high=Decimal("103"), low=Decimal("93"), minute=2),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.FALLING_STRUCTURE


def test_basic_trend_returns_mixed_for_higher_high_and_lower_low() -> None:
    previous = _candle(high=Decimal("105"), low=Decimal("95"), minute=0)
    current = _candle(high=Decimal("107"), low=Decimal("93"), minute=1)

    assert FeatureEngine.higher_high(current, previous) is True
    assert FeatureEngine.lower_low(current, previous) is True
    assert FeatureEngine.basic_trend((previous, current), 1) is BasicTrend.MIXED_STRUCTURE


def test_basic_trend_returns_mixed_for_lower_high_and_higher_low() -> None:
    previous = _candle(high=Decimal("105"), low=Decimal("95"), minute=0)
    current = _candle(high=Decimal("103"), low=Decimal("97"), minute=1)

    assert FeatureEngine.lower_high(current, previous) is True
    assert FeatureEngine.higher_low(current, previous) is True
    assert FeatureEngine.basic_trend((previous, current), 1) is BasicTrend.MIXED_STRUCTURE


def test_basic_trend_returns_mixed_when_highs_are_equal() -> None:
    previous = _candle(high=Decimal("105"), low=Decimal("95"), minute=0)
    current = _candle(high=Decimal("105"), low=Decimal("96"), minute=1)

    assert FeatureEngine.higher_high(current, previous) is False
    assert FeatureEngine.lower_high(current, previous) is False
    assert FeatureEngine.basic_trend((previous, current), 1) is BasicTrend.MIXED_STRUCTURE


def test_basic_trend_returns_mixed_when_lows_are_equal() -> None:
    previous = _candle(high=Decimal("105"), low=Decimal("95"), minute=0)
    current = _candle(high=Decimal("106"), low=Decimal("95"), minute=1)

    assert FeatureEngine.higher_low(current, previous) is False
    assert FeatureEngine.lower_low(current, previous) is False
    assert FeatureEngine.basic_trend((previous, current), 1) is BasicTrend.MIXED_STRUCTURE


def test_basic_trend_returns_none_for_insufficient_closed_history() -> None:
    candles = (_candle(high=Decimal("105"), low=Decimal("95"), minute=0),)

    assert FeatureEngine.basic_trend(candles, 1) is None


def test_basic_trend_excludes_open_candles_when_closed_history_is_sufficient() -> None:
    candles = (
        _candle(high=Decimal("105"), low=Decimal("95"), minute=0),
        _candle(
            high=Decimal("500"),
            low=Decimal("1"),
            minute=1,
            is_closed=False,
        ),
        _candle(high=Decimal("106"), low=Decimal("96"), minute=2),
        _candle(high=Decimal("107"), low=Decimal("97"), minute=3),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.RISING_STRUCTURE


def test_basic_trend_returns_none_when_open_filtering_leaves_insufficient_history() -> None:
    candles = (
        _candle(high=Decimal("105"), low=Decimal("95"), minute=0),
        _candle(
            high=Decimal("500"),
            low=Decimal("1"),
            minute=1,
            is_closed=False,
        ),
        _candle(high=Decimal("106"), low=Decimal("96"), minute=2),
    )

    assert FeatureEngine.basic_trend(candles, 2) is None


def test_basic_trend_uses_only_last_required_closed_candles() -> None:
    candles = (
        _candle(high=Decimal("108"), low=Decimal("90"), minute=0),
        _candle(high=Decimal("105"), low=Decimal("95"), minute=1),
        _candle(high=Decimal("106"), low=Decimal("96"), minute=2),
        _candle(high=Decimal("107"), low=Decimal("97"), minute=3),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.RISING_STRUCTURE


def test_basic_trend_rejects_zero_trend_pairs() -> None:
    with pytest.raises(ValueError, match="trend_pairs must be at least 1"):
        FeatureEngine.basic_trend((), 0)


def test_basic_trend_rejects_negative_trend_pairs() -> None:
    with pytest.raises(ValueError, match="trend_pairs must be at least 1"):
        FeatureEngine.basic_trend((), -1)


def test_basic_trend_supports_one_rising_pair() -> None:
    candles = (
        _candle(high=Decimal("105"), low=Decimal("95"), minute=0),
        _candle(high=Decimal("106"), low=Decimal("96"), minute=1),
    )

    assert FeatureEngine.basic_trend(candles, 1) is BasicTrend.RISING_STRUCTURE


def test_basic_trend_supports_one_falling_pair() -> None:
    candles = (
        _candle(high=Decimal("105"), low=Decimal("95"), minute=0),
        _candle(high=Decimal("104"), low=Decimal("94"), minute=1),
    )

    assert FeatureEngine.basic_trend(candles, 1) is BasicTrend.FALLING_STRUCTURE


def test_basic_trend_enum_has_exact_authorized_values() -> None:
    assert tuple(member.value for member in BasicTrend) == (
        "RISING_STRUCTURE",
        "FALLING_STRUCTURE",
        "MIXED_STRUCTURE",
    )
