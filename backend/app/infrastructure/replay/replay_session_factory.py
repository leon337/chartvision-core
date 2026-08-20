from pathlib import Path
from typing import Sequence

from app.domain.interfaces.outcome_storage_provider import OutcomeStorageProvider
from app.domain.models.candle import Candle
from app.domain.models.session import Session
from app.infrastructure.replay.exposure_tracked_replay import ExposureTrackedReplay
from app.infrastructure.replay.replay_source import ReplaySource, ReplayStatus


class ReplaySessionFactory:
    """Create Phase 7 tracked replay sessions from authoritative replay metadata."""

    def __init__(self, storage: OutcomeStorageProvider) -> None:
        self._storage = storage

    def from_json(
        self,
        path: str | Path,
        *,
        source_id: str = "replay",
        session_id: str = "reference-replay",
    ) -> ExposureTrackedReplay:
        source = ReplaySource.from_json(
            path,
            source_id=source_id,
            session_id=session_id,
        )
        return self._track_pristine_source(source)

    def from_candles(self, candles: Sequence[Candle]) -> ExposureTrackedReplay:
        return self._track_pristine_source(ReplaySource(candles))

    def _track_pristine_source(self, source: ReplaySource) -> ExposureTrackedReplay:
        if (
            source.status is not ReplayStatus.IDLE
            or source.position != 0
            or source.current_time is not None
        ):
            raise ValueError("tracked replay must be created before any replay exposure")

        session = Session(
            session_id=source.session_id,
            source_id=source.source_id,
            asset=source.asset,
            timeframe=source.timeframe,
            started_at=source.origin_time,
        )
        self._storage._initialize_tracked_session(
            session,
            session_origin_time=source.origin_time,
        )
        return ExposureTrackedReplay._from_factory(
            session_id=source.session_id,
            replay_source=source,
            storage=self._storage,
        )
