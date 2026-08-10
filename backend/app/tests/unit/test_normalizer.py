from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models.reconstruction import PriceCandleObservation, TrackedCandle
from app.domain.models.vision import CandleDirection
from app.domain.services.normalizer import NormalizationError, Normalizer


BASE = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _tracked(*, close: str = "101", last_seen_seconds: int = 20) -> TrackedCandle:
    observation = PriceCandleObservation(
        x=500,
        open=Decimal("100"),
        high=Decimal("103"),
        low=Decimal("98"),
        close=Decimal(close),
        direction=CandleDirection.UP,
        confidence=0.91,
        visual_quality=0.85,
    )
    return TrackedCandle(
        track_id="track-1",
        session_id="session-1",
        open_time=BASE,
        close_time=BASE + timedelta(minutes=1),
        observation=observation,
        is_closed=False,
        first_seen_at=BASE + timedelta(seconds=5),
        last_seen_at=BASE + timedelta(seconds=last_seen_seconds),
        confidence=0.88,
    )


def test_normalizes_reconstructed_values_to_canonical_candle() -> None:
    candle = Normalizer(source_id="vision", asset="TEST", timeframe="1m").normalize(_tracked())

    assert candle.open == Decimal("100")
    assert candle.high == Decimal("103")
    assert candle.low == Decimal("98")
    assert candle.close == Decimal("101")
    assert candle.is_closed is False
    assert candle.vision_confidence == 0.88
    assert candle.source_confidence is None


def test_temporal_deduplication_keeps_latest_observation() -> None:
    older = _tracked(close="101", last_seen_seconds=20)
    newer = _tracked(close="102", last_seen_seconds=40)

    candles = Normalizer(source_id="vision", asset="TEST", timeframe="1m").normalize_many(
        (older, newer)
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("102")


def test_invalid_ohlc_fails_explicitly() -> None:
    tracked = _tracked()
    invalid_observation = PriceCandleObservation(
        x=tracked.observation.x,
        open=Decimal("100"),
        high=Decimal("99"),
        low=Decimal("98"),
        close=Decimal("101"),
        direction=CandleDirection.UP,
        confidence=0.9,
        visual_quality=0.8,
    )
    invalid = TrackedCandle(
        track_id=tracked.track_id,
        session_id=tracked.session_id,
        open_time=tracked.open_time,
        close_time=tracked.close_time,
        observation=invalid_observation,
        is_closed=tracked.is_closed,
        first_seen_at=tracked.first_seen_at,
        last_seen_at=tracked.last_seen_at,
        confidence=tracked.confidence,
    )

    with pytest.raises(NormalizationError, match="HIGH_BELOW_BODY"):
        Normalizer(source_id="vision", asset="TEST", timeframe="1m").normalize(invalid)
