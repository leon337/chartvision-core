from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median
from typing import Iterable

from app.domain.models.frame import Frame
from app.domain.models.reconstruction import (
    PriceCandleObservation,
    TrackedCandle,
    TrackingResult,
)
from app.domain.models.vision import VisionStatus


class ChartTracker:
    """Track candle identity across frames without using OHLC ground truth."""

    def __init__(
        self,
        timeframe: str,
        *,
        shift_tolerance_px: int = 4,
        spacing_tolerance_ratio: float = 0.35,
    ) -> None:
        self._timeframe = timeframe
        self._duration = self._parse_timeframe(timeframe)
        self._shift_tolerance_px = shift_tolerance_px
        self._spacing_tolerance_ratio = spacing_tolerance_ratio
        self._tracks: dict[datetime, TrackedCandle] = {}
        self._previous_visible_x: dict[datetime, int] = {}
        self._expected_spacing: float | None = None

    def update(
        self,
        frame: Frame,
        candles: Iterable[PriceCandleObservation],
    ) -> TrackingResult:
        ordered = tuple(sorted(candles, key=lambda candle: candle.x))
        if not ordered:
            return self._failure("NO_CANDLES_TO_TRACK")
        if len({candle.x for candle in ordered}) != len(ordered):
            return self._failure("DUPLICATE_CANDLE_X")

        spacing = self._median_spacing(ordered)
        if spacing is not None:
            if self._expected_spacing is None:
                self._expected_spacing = spacing
            elif not self._spacing_is_consistent(ordered, self._expected_spacing):
                return self._failure("INCONSISTENT_CANDLE_SPACING")

        current_open_time = self._floor_to_timeframe(frame.captured_at)
        visible_times = tuple(
            current_open_time - self._duration * slots_from_right
            for slots_from_right in reversed(range(len(ordered)))
        )
        visible_x = {
            open_time: candle.x
            for open_time, candle in zip(visible_times, ordered)
        }

        horizontal_shift = 0
        if self._previous_visible_x:
            common_times = tuple(
                open_time
                for open_time in visible_times
                if open_time in self._previous_visible_x
            )
            if not common_times:
                return self._failure("NO_COMMON_CANDLE_IDENTITY")
            shifts = tuple(
                visible_x[open_time] - self._previous_visible_x[open_time]
                for open_time in common_times
            )
            horizontal_shift = int(round(float(median(shifts))))
            if any(
                abs(shift - horizontal_shift) > self._shift_tolerance_px
                for shift in shifts
            ):
                return self._failure("INCONSISTENT_HORIZONTAL_SHIFT")

        new_ids: list[str] = []
        updated_ids: list[str] = []
        closed_ids: list[str] = []
        visible_tracks: list[TrackedCandle] = []

        for open_time, observation in zip(visible_times, ordered):
            close_time = open_time + self._duration
            is_closed = open_time < current_open_time
            previous = self._tracks.get(open_time)
            track_id = self._track_id(frame.session_id, open_time)
            if previous is None:
                track = TrackedCandle(
                    track_id=track_id,
                    session_id=frame.session_id,
                    open_time=open_time,
                    close_time=close_time,
                    observation=observation,
                    is_closed=is_closed,
                    first_seen_at=frame.captured_at,
                    last_seen_at=frame.captured_at,
                    confidence=observation.confidence,
                )
                new_ids.append(track_id)
            else:
                track = TrackedCandle(
                    track_id=previous.track_id,
                    session_id=previous.session_id,
                    open_time=previous.open_time,
                    close_time=previous.close_time,
                    observation=observation,
                    is_closed=is_closed,
                    first_seen_at=previous.first_seen_at,
                    last_seen_at=frame.captured_at,
                    confidence=min(previous.confidence, observation.confidence),
                )
                updated_ids.append(track.track_id)
                if not previous.is_closed and is_closed:
                    closed_ids.append(track.track_id)

            self._tracks[open_time] = track
            visible_tracks.append(track)

        self._previous_visible_x = visible_x
        if spacing is not None:
            self._expected_spacing = spacing

        return TrackingResult(
            status=VisionStatus.OK,
            candles=tuple(visible_tracks),
            horizontal_shift_px=horizontal_shift,
            new_track_ids=tuple(new_ids),
            updated_track_ids=tuple(updated_ids),
            closed_track_ids=tuple(closed_ids),
        )

    def snapshot(self) -> tuple[TrackedCandle, ...]:
        return tuple(self._tracks[key] for key in sorted(self._tracks))

    def _failure(self, reason: str) -> TrackingResult:
        return TrackingResult(
            status=VisionStatus.TRACKING_LOST,
            candles=(),
            horizontal_shift_px=0,
            failure_reason=reason,
        )

    @staticmethod
    def _track_id(session_id: str, open_time: datetime) -> str:
        return f"{session_id}:{open_time.isoformat()}"

    @staticmethod
    def _median_spacing(candles: tuple[PriceCandleObservation, ...]) -> float | None:
        if len(candles) < 2:
            return None
        gaps = tuple(
            right.x - left.x
            for left, right in zip(candles, candles[1:])
        )
        if any(gap <= 0 for gap in gaps):
            return None
        return float(median(gaps))

    def _spacing_is_consistent(
        self,
        candles: tuple[PriceCandleObservation, ...],
        expected_spacing: float,
    ) -> bool:
        if len(candles) < 2 or expected_spacing <= 0:
            return True
        for left, right in zip(candles, candles[1:]):
            gap = right.x - left.x
            deviation = abs(gap - expected_spacing) / expected_spacing
            if deviation > self._spacing_tolerance_ratio:
                return False
        return True

    def _floor_to_timeframe(self, value: datetime) -> datetime:
        epoch = datetime(1970, 1, 1, tzinfo=value.tzinfo)
        duration_seconds = int(self._duration.total_seconds())
        elapsed_seconds = int((value - epoch).total_seconds())
        floored_seconds = elapsed_seconds - (elapsed_seconds % duration_seconds)
        return epoch + timedelta(seconds=floored_seconds)

    @staticmethod
    def _parse_timeframe(timeframe: str) -> timedelta:
        if len(timeframe) < 2 or not timeframe[:-1].isdigit():
            raise ValueError("UNSUPPORTED_TIMEFRAME")
        amount = int(timeframe[:-1])
        unit = timeframe[-1]
        if amount <= 0:
            raise ValueError("UNSUPPORTED_TIMEFRAME")
        factors = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }
        if unit not in factors:
            raise ValueError("UNSUPPORTED_TIMEFRAME")
        return timedelta(seconds=amount * factors[unit])
