from datetime import datetime, timedelta, timezone
from decimal import ROUND_UP, Decimal, localcontext

import pytest

from app.domain.models.candle import Candle
from app.domain.models.market_features import BasicTrend
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 11, 3, 0, tzinfo=timezone.utc)


def _candle(
    *,
    high: Decimal,
    low: Decimal,
    close: Decimal,
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
        open=close,
        high=high,
        low=low,
        close=close,
        is_closed=is_closed,
    )


def _canonical_mixed_window() -> tuple[Candle, ...]:
    return tuple(
        _candle(
            high=Decimal("100.5"),
            low=Decimal("99.5"),
            close=Decimal("100"),
            minute=minute,
        )
        for minute in range(3)
    )


def test_basic_lateralization_returns_true_at_inclusive_threshold() -> None:
    candles = _canonical_mixed_window()

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is True


def test_basic_lateralization_returns_false_above_threshold() -> None:
    candles = _canonical_mixed_window()

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.009"),
    ) is False


def test_basic_lateralization_returns_false_for_rising_structure() -> None:
    candles = (
        _candle(
            high=Decimal("100.2"),
            low=Decimal("99.8"),
            close=Decimal("100"),
            minute=0,
        ),
        _candle(
            high=Decimal("100.3"),
            low=Decimal("99.9"),
            close=Decimal("100"),
            minute=1,
        ),
        _candle(
            high=Decimal("100.4"),
            low=Decimal("100.0"),
            close=Decimal("100"),
            minute=2,
        ),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.RISING_STRUCTURE
    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is False


def test_basic_lateralization_returns_false_for_falling_structure() -> None:
    candles = (
        _candle(
            high=Decimal("100.4"),
            low=Decimal("100.0"),
            close=Decimal("100"),
            minute=0,
        ),
        _candle(
            high=Decimal("100.3"),
            low=Decimal("99.9"),
            close=Decimal("100"),
            minute=1,
        ),
        _candle(
            high=Decimal("100.2"),
            low=Decimal("99.8"),
            close=Decimal("100"),
            minute=2,
        ),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.FALLING_STRUCTURE
    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is False


def test_basic_lateralization_returns_false_for_mixed_wide_range() -> None:
    candles = tuple(
        _candle(
            high=Decimal("105"),
            low=Decimal("95"),
            close=Decimal("100"),
            minute=minute,
        )
        for minute in range(3)
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.MIXED_STRUCTURE
    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.05"),
    ) is False


def test_basic_lateralization_returns_none_for_zero_reference_price() -> None:
    candles = tuple(
        _candle(
            high=Decimal("0.5"),
            low=Decimal("-0.5"),
            close=Decimal("0"),
            minute=minute,
        )
        for minute in range(3)
    )

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("1"),
    ) is None


def test_basic_lateralization_uses_absolute_first_close() -> None:
    candles = tuple(
        _candle(
            high=Decimal("-99.5"),
            low=Decimal("-100.5"),
            close=Decimal("-100"),
            minute=minute,
        )
        for minute in range(3)
    )

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.009"),
    ) is False


def test_basic_lateralization_returns_none_for_insufficient_closed_history() -> None:
    candles = _canonical_mixed_window()[:2]

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is None


def test_basic_lateralization_excludes_open_candles_when_history_is_sufficient() -> None:
    closed = _canonical_mixed_window()
    open_candle = _candle(
        high=Decimal("500"),
        low=Decimal("1"),
        close=Decimal("100"),
        minute=1,
        is_closed=False,
    )
    candles = (closed[0], open_candle, closed[1], closed[2])

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is True


def test_basic_lateralization_returns_none_after_open_candles_are_excluded() -> None:
    closed = _canonical_mixed_window()
    open_candle = _candle(
        high=Decimal("100.5"),
        low=Decimal("99.5"),
        close=Decimal("100"),
        minute=1,
        is_closed=False,
    )
    candles = (closed[0], open_candle, closed[2])

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is None


def test_basic_lateralization_uses_only_last_required_closed_candles() -> None:
    old = _candle(
        high=Decimal("500"),
        low=Decimal("1"),
        close=Decimal("100"),
        minute=-1,
    )
    candles = (old, *_canonical_mixed_window())

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is True


def test_basic_lateralization_rejects_window_below_three() -> None:
    with pytest.raises(
        ValueError,
        match="lateralization_window_candles must be at least 3",
    ):
        FeatureEngine.basic_lateralization(
            (),
            lateralization_window_candles=2,
            lateralization_max_range_ratio=Decimal("0.01"),
        )


def test_basic_lateralization_rejects_zero_window() -> None:
    with pytest.raises(
        ValueError,
        match="lateralization_window_candles must be at least 3",
    ):
        FeatureEngine.basic_lateralization(
            (),
            lateralization_window_candles=0,
            lateralization_max_range_ratio=Decimal("0.01"),
        )


def test_basic_lateralization_rejects_negative_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="lateralization_max_range_ratio must be non-negative",
    ):
        FeatureEngine.basic_lateralization(
            (),
            lateralization_window_candles=3,
            lateralization_max_range_ratio=Decimal("-0.001"),
        )


def test_basic_lateralization_accepts_zero_threshold_for_zero_range() -> None:
    candles = tuple(
        _candle(
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            minute=minute,
        )
        for minute in range(3)
    )

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0"),
    ) is True


def test_basic_lateralization_is_independent_from_global_decimal_context() -> None:
    candles = tuple(
        _candle(
            high=Decimal("5"),
            low=Decimal("3"),
            close=Decimal("3"),
            minute=minute,
        )
        for minute in range(3)
    )

    with localcontext() as context:
        context.prec = 4
        context.rounding = ROUND_UP
        result = FeatureEngine.basic_lateralization(
            candles,
            lateralization_window_candles=3,
            lateralization_max_range_ratio=Decimal("0.66668"),
        )

    assert result is True


def test_basic_lateralization_allows_mixed_structure_from_equality() -> None:
    candles = (
        _candle(
            high=Decimal("100.4"),
            low=Decimal("99.6"),
            close=Decimal("100"),
            minute=0,
        ),
        _candle(
            high=Decimal("100.4"),
            low=Decimal("99.7"),
            close=Decimal("100"),
            minute=1,
        ),
        _candle(
            high=Decimal("100.5"),
            low=Decimal("99.8"),
            close=Decimal("100"),
            minute=2,
        ),
    )

    assert FeatureEngine.basic_trend(candles, 2) is BasicTrend.MIXED_STRUCTURE
    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is True


def test_basic_lateralization_uses_basic_trend_for_same_window() -> None:
    candles = _canonical_mixed_window()
    window = candles[-3:]

    assert FeatureEngine.basic_trend(
        window,
        trend_pairs=2,
    ) is BasicTrend.MIXED_STRUCTURE
    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.01"),
    ) is True


def test_basic_lateralization_returns_true_below_threshold() -> None:
    candles = _canonical_mixed_window()

    assert FeatureEngine.basic_lateralization(
        candles,
        lateralization_window_candles=3,
        lateralization_max_range_ratio=Decimal("0.02"),
    ) is True
