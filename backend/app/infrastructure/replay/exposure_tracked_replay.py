from __future__ import annotations

from threading import RLock

from app.domain.interfaces.outcome_storage_provider import OutcomeStorageProvider
from app.domain.models.outcome import OutcomeConfig, OutcomeEvaluationPolicy
from app.infrastructure.replay.replay_source import ReplaySnapshot, ReplaySource


_FACTORY_TOKEN = object()


class ExposureTrackedReplay:
    """Phase 7 replay lifecycle with non-rewindable exposure tracking."""

    def __init__(
        self,
        *,
        session_id: str,
        replay_source: ReplaySource,
        storage: OutcomeStorageProvider,
        _factory_token: object | None = None,
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise RuntimeError("ExposureTrackedReplay must be created by ReplaySessionFactory")
        self._session_id = session_id
        self._replay_source = replay_source
        self._storage = storage
        self._lock = RLock()

    @classmethod
    def _from_factory(
        cls,
        *,
        session_id: str,
        replay_source: ReplaySource,
        storage: OutcomeStorageProvider,
    ) -> ExposureTrackedReplay:
        return cls(
            session_id=session_id,
            replay_source=replay_source,
            storage=storage,
            _factory_token=_FACTORY_TOKEN,
        )

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def asset(self) -> str:
        return self._replay_source.asset

    @property
    def timeframe(self) -> str:
        return self._replay_source.timeframe

    @property
    def snapshot(self) -> ReplaySnapshot:
        with self._lock:
            return self._replay_source.snapshot

    def start(self) -> None:
        with self._lock:
            self._replay_source.start()
            self._record_current_exposure()

    def pause(self) -> None:
        with self._lock:
            self._replay_source.pause()

    def resume(self) -> None:
        with self._lock:
            self._replay_source.resume()
            self._record_current_exposure()

    def stop(self) -> None:
        with self._lock:
            self._replay_source.stop()

    def reset(self) -> None:
        with self._lock:
            self._replay_source.reset()

    def advance(self, *, seconds: int = 60):
        with self._lock:
            released = self._replay_source.advance(seconds=seconds)
            self._record_current_exposure()
            return released

    def register_policy(
        self,
        *,
        policy_id: str,
        config: OutcomeConfig,
    ) -> OutcomeEvaluationPolicy:
        with self._lock:
            return self._storage.register_outcome_evaluation_policy(
                session_id=self._session_id,
                policy_id=policy_id,
                config=config,
            )

    def _record_current_exposure(self) -> None:
        current_time = self._replay_source.current_time
        if current_time is not None:
            self._storage.record_session_exposure(self._session_id, current_time)
