from app.domain.interfaces.outcome_storage_provider import OutcomeStorageProvider
from app.infrastructure.replay.replay_source import ReplaySnapshot, ReplaySource


class ExposureTrackedReplay:
    """Phase 7 replay adapter that records non-rewindable exposure metadata."""

    def __init__(
        self,
        *,
        session_id: str,
        replay_source: ReplaySource,
        storage: OutcomeStorageProvider,
    ) -> None:
        self._session_id = session_id
        self._replay_source = replay_source
        self._storage = storage

    @property
    def snapshot(self) -> ReplaySnapshot:
        return self._replay_source.snapshot

    def start(self) -> None:
        self._replay_source.start()
        self._record_current_exposure()

    def pause(self) -> None:
        self._replay_source.pause()

    def resume(self) -> None:
        self._replay_source.resume()
        self._record_current_exposure()

    def stop(self) -> None:
        self._replay_source.stop()

    def reset(self) -> None:
        self._replay_source.reset()

    def advance(self, *, seconds: int = 60):
        released = self._replay_source.advance(seconds=seconds)
        self._record_current_exposure()
        return released

    def _record_current_exposure(self) -> None:
        current_time = self._replay_source.current_time
        if current_time is not None:
            self._storage.record_session_exposure(self._session_id, current_time)
