from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, getcontext, localcontext

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


def test_candle_return_is_positive_when_close_increases() -> None:
    previous = _candle(close=Decimal("100"), is_closed=True, minute=0)
    current = _candle(close=Decimal("103"), is_closed=True, minute=1)

    result = FeatureEngine.candle_return(current, previous)

    assert isinstance(result, Decimal)
    assert result == Decimal("0.03")


def test_candle_return_is_negative_when_close_decreases() -> None:
    previous = _candle(close=Decimal("100"), is_closed=True, minute=0)
    current = _candle(close=Decimal("97"), is_closed=True, minute=1)

    assert FeatureEngine.candle_return(current, previous) == Decimal("-0.03")


def test_candle_return_is_zero_when_closes_are_equal() -> None:
    previous = _candle(close=Decimal("100"), is_closed=True, minute=0)
    current = _candle(close=Decimal("100"), is_closed=True, minute=1)

    assert FeatureEngine.candle_return(current, previous) == Decimal("0")


def test_candle_return_is_none_when_previous_close_is_zero() -> None:
    previous = _candle(close=Decimal("0"), is_closed=True, minute=0)
    current = _candle(close=Decimal("10"), is_closed=True, minute=1)

    assert FeatureEngine.candle_return(current, previous) is None


def test_candle_return_is_none_when_previous_candle_is_open() -> None:
    previous = _candle(close=Decimal("100"), is_closed=False, minute=0)
    current = _candle(close=Decimal("103"), is_closed=True, minute=1)

    assert FeatureEngine.candle_return(current, previous) is None


def test_candle_return_does_not_depend_on_current_candle_is_closed() -> None:
    previous = _candle(close=Decimal("100"), is_closed=True, minute=0)
    open_current = _candle(close=Decimal("103"), is_closed=False, minute=1)
    closed_current = _candle(close=Decimal("103"), is_closed=True, minute=1)

    assert FeatureEngine.candle_return(open_current, previous) == Decimal("0.03")
    assert FeatureEngine.candle_return(closed_current, previous) == Decimal("0.03")


def test_candle_return_uses_fixed_local_decimal_context() -> None:
    previous = _candle(close=Decimal("3"), is_closed=True, minute=0)
    current = _candle(close=Decimal("4"), is_closed=True, minute=1)
    original_context = getcontext().copy()

    with localcontext() as external_context:
        external_context.prec = 6
        external_context.rounding = ROUND_DOWN

        result = FeatureEngine.candle_return(current, previous)

        assert result == Decimal("0.3333333333333333333333333333")
        assert getcontext().prec == 6
        assert getcontext().rounding == ROUND_DOWN

    assert getcontext().prec == original_context.prec
    assert getcontext().rounding == original_context.rounding
