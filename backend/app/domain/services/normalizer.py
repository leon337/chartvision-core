from collections.abc import Iterable

from app.domain.models.candle import Candle
from app.domain.models.reconstruction import TrackedCandle


class NormalizationError(ValueError):
    """Explicit failure when a tracked visual candle cannot form canonical OHLC."""


class Normalizer:
    def __init__(self, *, source_id: str, asset: str, timeframe: str) -> None:
        if not source_id or not asset or not timeframe:
            raise ValueError("INVALID_NORMALIZER_CONTEXT")
        self._source_id = source_id
        self._asset = asset
        self._timeframe = timeframe

    def normalize(self, tracked: TrackedCandle) -> Candle:
        observation = tracked.observation
        if observation.high < max(observation.open, observation.close):
            raise NormalizationError("HIGH_BELOW_BODY")
        if observation.low > min(observation.open, observation.close):
            raise NormalizationError("LOW_ABOVE_BODY")
        if observation.low > observation.high:
            raise NormalizationError("LOW_ABOVE_HIGH")

        return Candle(
            source_id=self._source_id,
            session_id=tracked.session_id,
            asset=self._asset,
            timeframe=self._timeframe,
            open_time=tracked.open_time,
            close_time=tracked.close_time,
            open=observation.open,
            high=observation.high,
            low=observation.low,
            close=observation.close,
            is_closed=tracked.is_closed,
            vision_confidence=tracked.confidence,
            source_confidence=None,
        )

    def normalize_many(self, tracked: Iterable[TrackedCandle]) -> tuple[Candle, ...]:
        latest: dict[tuple[str, object], TrackedCandle] = {}
        for candle in tracked:
            key = (candle.session_id, candle.open_time)
            previous = latest.get(key)
            if previous is None or candle.last_seen_at >= previous.last_seen_at:
                latest[key] = candle

        ordered = sorted(
            latest.values(),
            key=lambda candle: (candle.open_time, candle.session_id),
        )
        return tuple(self.normalize(candle) for candle in ordered)
