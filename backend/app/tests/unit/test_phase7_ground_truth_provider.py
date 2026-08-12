from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models.candle import Candle
from app.infrastructure.replay.ground_truth_provider import ReplayGroundTruthProvider

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def _candle(index: int, *, session_id: str = "session-1", offset: int | None = None) -> Candle:
    minute = index if offset is None else offset
    open_time = T0 + timedelta(minutes=minute)
    close = Decimal(100 + index)
    return Candle(
        source_id="replay",
        session_id=session_id,
        asset="SAMPLE",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=close,
        high=close,
        low=close,
        close=close,
        is_closed=True,
    )


def test_selects_last_closed_reference_and_exact_horizon() -> None:
    candles = tuple(_candle(index) for index in range(6))
    provider = ReplayGroundTruthProvider(candles)

    window = provider.get_evaluation_window(
        "session-1",
        T0 + timedelta(minutes=2),
        T0 + timedelta(minutes=5),
        3,
    )

    assert window.reference_candle == candles[1]
    assert window.future_closed_candles == candles[2:5]
    assert window.source_exhausted is False


def test_does_not_return_candle_beyond_evaluation_as_of() -> None:
    candles = tuple(_candle(index) for index in range(6))
    provider = ReplayGroundTruthProvider(candles)

    window = provider.get_evaluation_window(
        "session-1",
        T0 + timedelta(minutes=2),
        T0 + timedelta(minutes=3),
        3,
    )

    assert window.reference_candle == candles[1]
    assert window.future_closed_candles == (candles[2],)
    assert all(candle.close_time <= T0 + timedelta(minutes=3) for candle in window.future_closed_candles)


def test_source_exhausted_only_after_dataset_terminal_time() -> None:
    candles = tuple(_candle(index) for index in range(4))
    provider = ReplayGroundTruthProvider(candles)

    pending = provider.get_evaluation_window(
        "session-1",
        T0 + timedelta(minutes=2),
        T0 + timedelta(minutes=3),
        3,
    )
    terminal = provider.get_evaluation_window(
        "session-1",
        T0 + timedelta(minutes=2),
        T0 + timedelta(minutes=4),
        3,
    )

    assert pending.source_exhausted is False
    assert terminal.source_exhausted is True
    assert terminal.future_closed_candles == candles[2:4]


def test_missing_reference_is_explicit() -> None:
    candles = tuple(_candle(index) for index in range(3))
    provider = ReplayGroundTruthProvider(candles)

    window = provider.get_evaluation_window(
        "session-1",
        T0,
        T0,
        2,
    )

    assert window.reference_candle is None
    assert window.future_closed_candles == ()


def test_gaps_are_not_synthesized() -> None:
    candles = (
        _candle(0, offset=0),
        _candle(1, offset=1),
        _candle(2, offset=5),
        _candle(3, offset=9),
    )
    provider = ReplayGroundTruthProvider(candles)

    window = provider.get_evaluation_window(
        "session-1",
        T0 + timedelta(minutes=2),
        T0 + timedelta(minutes=10),
        2,
    )

    assert window.reference_candle == candles[1]
    assert window.future_closed_candles == candles[2:4]


def test_session_isolation_is_required() -> None:
    provider = ReplayGroundTruthProvider((_candle(0, session_id="session-a"),))
    with pytest.raises(ValueError, match="no Ground Truth dataset"):
        provider.get_evaluation_window("session-b", T0, T0, 1)


def test_invalid_temporal_inputs_fail_explicitly() -> None:
    provider = ReplayGroundTruthProvider((_candle(0), _candle(1)))
    with pytest.raises(ValueError, match="timezone-aware"):
        provider.get_evaluation_window(
            "session-1",
            datetime(2026, 8, 12, 10, 0),
            T0,
            1,
        )
    with pytest.raises(ValueError, match="cannot precede"):
        provider.get_evaluation_window(
            "session-1",
            T0 + timedelta(minutes=1),
            T0,
            1,
        )
