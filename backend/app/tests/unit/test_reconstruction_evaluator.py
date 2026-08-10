from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.services.reconstruction_evaluator import ReconstructionEvaluator


BASE = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _candle(
    minute: int,
    *,
    open_value: str,
    high: str,
    low: str,
    close: str,
) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="source",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal(open_value),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        is_closed=True,
        vision_confidence=0.9,
    )


def test_calculates_reconstruction_quality_metrics_after_reconstruction() -> None:
    truth = (
        _candle(0, open_value="100", high="103", low="98", close="102"),
        _candle(1, open_value="102", high="104", low="99", close="100"),
    )
    reconstructed = (
        _candle(0, open_value="100.5", high="102.5", low="98.5", close="101.5"),
        _candle(1, open_value="101.5", high="103.5", low="99.5", close="100.5"),
    )

    metrics = ReconstructionEvaluator().evaluate(reconstructed, truth)

    assert metrics.open_error == Decimal("0.5")
    assert metrics.high_error == Decimal("0.5")
    assert metrics.low_error == Decimal("0.5")
    assert metrics.close_error == Decimal("0.5")
    assert metrics.candle_detection_rate == 1.0
    assert metrics.direction_accuracy == 1.0
    assert metrics.duplicate_rate == 0.0
    assert metrics.missing_candle_rate == 0.0


def test_reports_duplicate_and_missing_rates() -> None:
    truth = (
        _candle(0, open_value="100", high="103", low="98", close="102"),
        _candle(1, open_value="102", high="104", low="99", close="100"),
    )
    first = _candle(0, open_value="100", high="103", low="98", close="102")

    metrics = ReconstructionEvaluator().evaluate((first, first), truth)

    assert metrics.candle_detection_rate == 0.5
    assert metrics.direction_accuracy == 1.0
    assert metrics.duplicate_rate == 0.5
    assert metrics.missing_candle_rate == 0.5
