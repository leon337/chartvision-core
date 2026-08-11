from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models.analysis import AnalysisConfig, MarketState
from app.domain.models.candle import Candle
from app.domain.models.market_features import BasicTrend
from app.domain.services.analysis_lab_service import AnalysisLabService
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 11, 5, 0, tzinfo=timezone.utc)
CONFIG = AnalysisConfig(
    trend_pairs=2,
    lateralization_window_candles=3,
    lateralization_max_range_ratio=Decimal("0.01"),
    minimum_data_quality=0.8,
)


class StorageStub:
    def __init__(self, candles: tuple[Candle, ...]) -> None:
        self.candles = candles
        self.calls: list[tuple[str, datetime]] = []

    def get_candles_as_of(self, session_id: str, as_of: datetime) -> tuple[Candle, ...]:
        self.calls.append((session_id, as_of))
        return self.candles


def _candle(
    minute: int,
    *,
    high: str,
    low: str,
    close: str = "100",
    is_closed: bool = True,
    vision_confidence: float | None = 0.9,
    source_confidence: float | None = None,
) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="vision",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        is_closed=is_closed,
        vision_confidence=vision_confidence,
        source_confidence=source_confidence,
    )


def _rising_candles(
    qualities: tuple[float | None, ...] = (0.95, 0.91, 0.93),
) -> tuple[Candle, ...]:
    return (
        _candle(-3, high="101", low="97", close="99", vision_confidence=qualities[0]),
        _candle(-2, high="102", low="98", close="100", vision_confidence=qualities[1]),
        _candle(-1, high="103", low="99", close="101", vision_confidence=qualities[2]),
    )


def test_rejects_naive_as_of() -> None:
    service = AnalysisLabService(StorageStub(_rising_candles()))

    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        service.analyze("session-1", datetime(2026, 8, 11, 5, 0), CONFIG)


def test_uses_point_in_time_storage_boundary() -> None:
    storage = StorageStub(_rising_candles())
    service = AnalysisLabService(storage)

    service.analyze("session-1", BASE, CONFIG)

    assert storage.calls == [("session-1", BASE)]


def test_insufficient_history_is_uncertain() -> None:
    service = AnalysisLabService(StorageStub(_rising_candles()[:2]))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.market_state is MarketState.UNCERTAIN
    assert result.confidence == 0.0
    assert result.data_quality is None
    assert result.evidence == (
        "STATE_RULE=INSUFFICIENT_HISTORY",
        "BASIC_TREND=NONE",
        "BASIC_LATERALIZATION=NONE",
        "DATA_QUALITY=NONE",
    )


def test_uses_only_closed_candles_for_required_history() -> None:
    candles = _rising_candles()[:2] + (
        _candle(0, high="500", low="1", is_closed=False, vision_confidence=0.01),
    )
    service = AnalysisLabService(StorageStub(candles))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.market_state is MarketState.UNCERTAIN
    assert result.evidence[0] == "STATE_RULE=INSUFFICIENT_HISTORY"


def test_computes_basic_trend_through_feature_engine(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_basic_trend(candles, trend_pairs):
        seen["trend"] = (candles, trend_pairs)
        return BasicTrend.RISING_STRUCTURE

    monkeypatch.setattr(FeatureEngine, "basic_trend", staticmethod(fake_basic_trend))
    service = AnalysisLabService(StorageStub(_rising_candles()))

    result = service.analyze("session-1", BASE, CONFIG)

    assert seen["trend"] == (_rising_candles(), CONFIG.trend_pairs)
    assert result.market_state is MarketState.UP


def test_computes_basic_lateralization_through_feature_engine(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_lateralization(candles, lateralization_window_candles, lateralization_max_range_ratio):
        seen["lateralization"] = (
            candles,
            lateralization_window_candles,
            lateralization_max_range_ratio,
        )
        return True

    monkeypatch.setattr(
        FeatureEngine,
        "basic_lateralization",
        staticmethod(fake_lateralization),
    )
    service = AnalysisLabService(StorageStub(_rising_candles()))

    result = service.analyze("session-1", BASE, CONFIG)

    assert seen["lateralization"] == (
        _rising_candles(),
        CONFIG.lateralization_window_candles,
        CONFIG.lateralization_max_range_ratio,
    )
    assert result.market_state is MarketState.SIDEWAYS


def test_data_quality_is_minimum_of_required_closed_window() -> None:
    service = AnalysisLabService(StorageStub(_rising_candles((0.95, 0.84, 0.9))))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.market_state is MarketState.UP
    assert result.data_quality == 0.84
    assert result.confidence == 0.84


def test_old_low_quality_outside_required_window_does_not_reduce_quality() -> None:
    candles = (
        _candle(-4, high="100", low="96", close="98", vision_confidence=0.1),
        *_rising_candles((0.95, 0.9, 0.92)),
    )
    service = AnalysisLabService(StorageStub(candles))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.data_quality == 0.9
    assert result.market_state is MarketState.UP


def test_open_candle_does_not_reduce_data_quality() -> None:
    candles = _rising_candles((0.95, 0.9, 0.92)) + (
        _candle(0, high="999", low="1", is_closed=False, vision_confidence=0.01),
    )
    service = AnalysisLabService(StorageStub(candles))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.data_quality == 0.9
    assert result.market_state is MarketState.UP


def test_source_confidence_does_not_affect_data_quality() -> None:
    candles = (
        _candle(-3, high="101", low="97", close="99", vision_confidence=0.95, source_confidence=0.01),
        _candle(-2, high="102", low="98", close="100", vision_confidence=0.9, source_confidence=0.0),
        _candle(-1, high="103", low="99", close="101", vision_confidence=0.92, source_confidence=None),
    )
    service = AnalysisLabService(StorageStub(candles))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.data_quality == 0.9


def test_missing_vision_confidence_produces_none_data_quality() -> None:
    service = AnalysisLabService(StorageStub(_rising_candles((0.95, None, 0.92))))

    result = service.analyze("session-1", BASE, CONFIG)

    assert result.market_state is MarketState.UNCERTAIN
    assert result.data_quality is None
    assert result.confidence == 0.0


@pytest.mark.parametrize("invalid_quality", [-0.01, 1.01, float("inf"), float("nan")])
def test_invalid_vision_confidence_is_rejected(invalid_quality: float) -> None:
    service = AnalysisLabService(
        StorageStub(_rising_candles((0.95, invalid_quality, 0.92)))
    )

    with pytest.raises(ValueError, match="vision_confidence must be between 0.0 and 1.0"):
        service.analyze("session-1", BASE, CONFIG)


def test_invalid_vision_confidence_is_rejected_even_when_another_quality_is_missing() -> None:
    service = AnalysisLabService(
        StorageStub(_rising_candles((None, 1.1, 0.92)))
    )

    with pytest.raises(ValueError, match="vision_confidence must be between 0.0 and 1.0"):
        service.analyze("session-1", BASE, CONFIG)


def test_same_point_in_time_input_is_deterministic() -> None:
    service = AnalysisLabService(StorageStub(_rising_candles((0.95, 0.9, 0.92))))

    first = service.analyze("session-1", BASE, CONFIG)
    second = service.analyze("session-1", BASE, CONFIG)

    assert first == second
