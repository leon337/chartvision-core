from datetime import datetime, timezone
from decimal import Decimal

from app.domain.models.frame import Frame
from app.domain.models.reconstruction import PriceCandleObservation
from app.domain.models.vision import CandleDirection, VisionStatus
from app.domain.services.chart_tracker import ChartTracker


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


def _obs(x: int, *, close: str = "100", direction: CandleDirection = CandleDirection.UP) -> PriceCandleObservation:
    value = Decimal(close)
    return PriceCandleObservation(
        x=x,
        open=value - Decimal("1") if direction is CandleDirection.UP else value + Decimal("1"),
        high=value + Decimal("2"),
        low=value - Decimal("2"),
        close=value,
        direction=direction,
        confidence=0.9,
        visual_quality=0.8,
    )


def test_multiple_frames_update_same_open_candle_without_duplicate() -> None:
    tracker = ChartTracker("1m")
    first = tracker.update(
        _frame("f1", datetime(2026, 8, 10, 12, 0, 20, tzinfo=timezone.utc)),
        (_obs(230), _obs(365), _obs(500, close="100")),
    )
    second = tracker.update(
        _frame("f2", datetime(2026, 8, 10, 12, 0, 45, tzinfo=timezone.utc)),
        (_obs(230), _obs(365), _obs(500, close="101")),
    )

    assert first.status is VisionStatus.OK
    assert second.status is VisionStatus.OK
    assert len(tracker.snapshot()) == 3
    assert len(second.new_track_ids) == 0
    assert len(second.updated_track_ids) == 3
    assert second.candles[-1].observation.close == Decimal("101")
    assert second.candles[-1].is_closed is False


def test_new_candle_closes_previous_open_candle_and_recognizes_shift() -> None:
    tracker = ChartTracker("1m")
    tracker.update(
        _frame("f1", datetime(2026, 8, 10, 12, 0, 20, tzinfo=timezone.utc)),
        (_obs(230), _obs(365), _obs(500)),
    )
    result = tracker.update(
        _frame("f2", datetime(2026, 8, 10, 12, 1, 5, tzinfo=timezone.utc)),
        (_obs(160), _obs(295), _obs(430), _obs(565, close="102")),
    )

    assert result.status is VisionStatus.OK
    assert result.horizontal_shift_px == -70
    assert len(result.new_track_ids) == 1
    assert len(result.closed_track_ids) == 1
    assert result.candles[-2].is_closed is True
    assert result.candles[-1].is_closed is False
    assert len(tracker.snapshot()) == 4


def test_duplicate_frame_does_not_create_duplicate_tracks() -> None:
    tracker = ChartTracker("1m")
    frame = _frame("f1", datetime(2026, 8, 10, 12, 0, 20, tzinfo=timezone.utc))
    candles = (_obs(230), _obs(365), _obs(500))

    tracker.update(frame, candles)
    result = tracker.update(frame, candles)

    assert result.status is VisionStatus.OK
    assert result.new_track_ids == ()
    assert len(tracker.snapshot()) == 3


def test_inconsistent_horizontal_shift_fails_explicitly() -> None:
    tracker = ChartTracker("1m")
    tracker.update(
        _frame("f1", datetime(2026, 8, 10, 12, 0, 20, tzinfo=timezone.utc)),
        (_obs(230), _obs(365), _obs(500)),
    )
    result = tracker.update(
        _frame("f2", datetime(2026, 8, 10, 12, 0, 40, tzinfo=timezone.utc)),
        (_obs(220), _obs(360), _obs(480)),
    )

    assert result.status is VisionStatus.TRACKING_LOST
    assert result.failure_reason in {
        "INCONSISTENT_HORIZONTAL_SHIFT",
        "INCONSISTENT_CANDLE_SPACING",
    }


def test_empty_detection_fails_explicitly() -> None:
    result = ChartTracker("1m").update(
        _frame("f1", datetime(2026, 8, 10, 12, 0, 20, tzinfo=timezone.utc)),
        (),
    )

    assert result.status is VisionStatus.TRACKING_LOST
    assert result.failure_reason == "NO_CANDLES_TO_TRACK"
