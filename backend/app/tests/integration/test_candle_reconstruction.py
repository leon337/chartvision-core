from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.vision import VisionStatus
from app.domain.services.reconstruction_evaluator import ReconstructionEvaluator
from app.infrastructure.vision.reconstruction_pipeline import CandleReconstructionPipeline
from app.tests.phase3_reference import (
    FRAME1_CANDLES,
    FRAME2_CANDLES,
    FRAME3_CANDLES,
    phase3_chart_png,
)


BASE = datetime(2026, 8, 10, 11, 58, tzinfo=timezone.utc)


def _frame(frame_id: str, captured_at: datetime) -> Frame:
    return Frame(
        frame_id=frame_id,
        session_id="session-1",
        captured_at=captured_at,
        image_hash=frame_id,
        width=800,
        height=560,
        changed_since_previous=True,
    )


def _truth(minute: int, open_: str, high: str, low: str, close: str) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="ground-truth",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        is_closed=True,
        source_confidence=1.0,
    )


def test_phase3_pipeline_tracks_multiple_frames_and_evaluates_after_reconstruction() -> None:
    pipeline = CandleReconstructionPipeline(source_id="vision", asset="TEST", timeframe="1m")

    first = pipeline.process(
        phase3_chart_png(FRAME1_CANDLES),
        _frame("f1", datetime(2026, 8, 10, 12, 0, 20, tzinfo=timezone.utc)),
    )
    second = pipeline.process(
        phase3_chart_png(FRAME2_CANDLES),
        _frame("f2", datetime(2026, 8, 10, 12, 0, 45, tzinfo=timezone.utc)),
    )
    third = pipeline.process(
        phase3_chart_png(FRAME3_CANDLES),
        _frame("f3", datetime(2026, 8, 10, 12, 1, 5, tzinfo=timezone.utc)),
    )

    assert first.status is VisionStatus.OK
    assert second.status is VisionStatus.OK
    assert third.status is VisionStatus.OK
    assert first.tracking is not None
    assert second.tracking is not None
    assert third.tracking is not None
    assert len(second.tracking.new_track_ids) == 0
    assert third.tracking.horizontal_shift_px == -70
    assert len(third.tracking.new_track_ids) == 1
    assert len(third.tracking.closed_track_ids) == 1

    reconstructed = tuple(candle for candle in pipeline.snapshot() if candle.is_closed)
    assert len(reconstructed) == 3
    assert reconstructed[2].open == Decimal("96.50")
    assert reconstructed[2].high == Decimal("101.75")
    assert reconstructed[2].low == Decimal("94.00")
    assert reconstructed[2].close == Decimal("99.50")

    ground_truth = (
        _truth(0, "100", "103", "98.75", "101.75"),
        _truth(1, "102", "103.75", "97.25", "99.25"),
        _truth(2, "96.5", "101.75", "94", "99.5"),
    )
    metrics = ReconstructionEvaluator().evaluate(reconstructed, ground_truth)

    assert metrics.open_error == Decimal("0")
    assert metrics.high_error == Decimal("0")
    assert metrics.low_error == Decimal("0")
    assert metrics.close_error == Decimal("0")
    assert metrics.candle_detection_rate == 1.0
    assert metrics.direction_accuracy == 1.0
    assert metrics.duplicate_rate == 0.0
    assert metrics.missing_candle_rate == 0.0
