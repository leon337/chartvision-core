from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, getcontext, localcontext

import pytest

from app.domain.models.candle import Candle
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)


def _candle(*, close: Decimal, is_closed: bool, minute: int) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="source-1",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=close,
        high=close,
        low=close,
        close=close,
        is_closed=is_closed,
    )


def test_simple_volatility_uses_population_standard_deviation() -> None:
    candles = (
        _candle(close=Decimal("100"), is_closed=True, minute=0),
        _candle(close=Decimal("110"), is_closed=True, minute=1),
        _candle(close=Decimal("99"), is_closed=True, minute=2),
    )

    result = FeatureEngine.simple_volatility(candles, volatility_window_candles=3)

    assert isinstance(result, Decimal)
    assert result == Decimal("0.10")


def test_simple_volatility_is_zero_for_identical_returns() -> None:
    candles = (
        _candle(close=Decimal("100"), is_closed=True, minute=0),
        _candle(close=Decimal("110"), is_closed=True, minute=1),
        _candle(close=Decimal("121"), is_closed=True, minute=2),
    )

    assert FeatureEngine.simple_volatility(candles, 3) == Decimal("0")


def test_simple_volatility_returns_none_for_insufficient_closed_history() -> None:
    candles = (
        _candle(close=Decimal("100"), is_closed=True, minute=0),
        _candle(close=Decimal("110"), is_closed=True, minute=1),
        _candle(close=Decimal("120"), is_closed=False, minute=2),
    )

    assert FeatureEngine.simple_volatility(candles, 3) is None


def test_simple_volatility_rejects_window_below_three() -> None:
    with pytest.raises(ValueError, match="volatility_window_candles must be at least 3"):
        FeatureEngine.simple_volatility((), 2)


def test_simple_volatility_excludes_open_candles() -> None:
    candles = (
        _candle(close=Decimal("100"), is_closed=True, minute=0),
        _candle(close=Decimal("110"), is_closed=True, minute=1),
        _candle(close=Decimal("99"), is_closed=True, minute=2),
        _candle(close=Decimal("500"), is_closed=False, minute=3),
    )

    assert FeatureEngine.simple_volatility(candles, 3) == Decimal("0.10")


def test_simple_volatility_uses_suffix_of_latest_closed_candles() -> None:
    candles = (
        _candle(close=Decimal("50"), is_closed=True, minute=0),
        _candle(close=Decimal("100"), is_closed=True, minute=1),
        _candle(close=Decimal("110"), is_closed=True, minute=2),
        _candle(close=Decimal("99"), is_closed=True, minute=3),
    )

    assert FeatureEngine.simple_volatility(candles, 3) == Decimal("0.10")


def test_simple_volatility_returns_none_when_window_has_zero_denominator() -> None:
    candles = (
        _candle(close=Decimal("0"), is_closed=True, minute=0),
        _candle(close=Decimal("10"), is_closed=True, minute=1),
        _candle(close=Decimal("11"), is_closed=True, minute=2),
    )

    assert FeatureEngine.simple_volatility(candles, 3) is None


def test_simple_volatility_uses_fixed_local_decimal_context() -> None:
    candles = (
        _candle(close=Decimal("3"), is_closed=True, minute=0),
        _candle(close=Decimal("4"), is_closed=True, minute=1),
        _candle(close=Decimal("5"), is_closed=True, minute=2),
    )
    original_context = getcontext().copy()

    with localcontext() as external_context:
        external_context.prec = 6
        external_context.rounding = ROUND_DOWN

        result = FeatureEngine.simple_volatility(candles, 3)

        assert result == Decimal("0.04166666666666666666666666665")
        assert getcontext().prec == 6
        assert getcontext().rounding == ROUND_DOWN

    assert getcontext().prec == original_context.prec
    assert getcontext().rounding == original_context.rounding
