from collections.abc import Sequence
from datetime import datetime

from app.domain.interfaces.ground_truth_provider import GroundTruthWindow
from app.domain.models.candle import Candle


class ReplayGroundTruthProvider:
    """Ground Truth adapter for the controlled replay dataset."""

    def __init__(self, candles: Sequence[Candle]) -> None:
        if not candles:
            raise ValueError("Ground Truth provider requires at least one candle")
        self._candles = tuple(candles)
        self._validate_candles()

    def get_evaluation_window(
        self,
        session_id: str,
        analysis_timestamp: datetime,
        evaluation_as_of: datetime,
        horizon_closed_candles: int,
    ) -> GroundTruthWindow:
        self._require_aware(analysis_timestamp, "analysis_timestamp")
        self._require_aware(evaluation_as_of, "evaluation_as_of")
        if evaluation_as_of < analysis_timestamp:
            raise ValueError("evaluation_as_of cannot precede analysis_timestamp")
        if (
            isinstance(horizon_closed_candles, bool)
            or not isinstance(horizon_closed_candles, int)
            or horizon_closed_candles < 1
        ):
            raise ValueError("horizon_closed_candles must be an integer of at least 1")

        session_candles = tuple(
            candle for candle in self._candles if candle.session_id == session_id and candle.is_closed
        )
        if not session_candles:
            raise ValueError(f"no Ground Truth dataset for session_id {session_id!r}")

        ordered = tuple(sorted(session_candles, key=lambda candle: (candle.close_time, candle.open_time)))
        source_exhausted = evaluation_as_of >= ordered[-1].close_time
        reference_index: int | None = None
        for index, candle in enumerate(ordered):
            if candle.close_time <= analysis_timestamp:
                reference_index = index
            else:
                break

        if reference_index is None:
            return GroundTruthWindow(
                reference_candle=None,
                future_closed_candles=(),
                source_exhausted=source_exhausted,
            )

        reference = ordered[reference_index]
        future = tuple(
            candle
            for candle in ordered[reference_index + 1 :]
            if candle.close_time <= evaluation_as_of
        )[:horizon_closed_candles]
        return GroundTruthWindow(
            reference_candle=reference,
            future_closed_candles=future,
            source_exhausted=source_exhausted,
        )

    def _validate_candles(self) -> None:
        seen: set[tuple[str, datetime]] = set()
        for candle in self._candles:
            self._require_aware(candle.open_time, "candle.open_time")
            self._require_aware(candle.close_time, "candle.close_time")
            if candle.close_time <= candle.open_time:
                raise ValueError("Ground Truth candle close_time must be after open_time")
            identity = (candle.session_id, candle.open_time)
            if identity in seen:
                raise ValueError("Ground Truth contains duplicate candle identity")
            seen.add(identity)

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
