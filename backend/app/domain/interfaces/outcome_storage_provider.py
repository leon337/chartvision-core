from datetime import datetime
from typing import Protocol

from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.models.outcome import OutcomeConfig, OutcomeEvaluationPolicy
from app.domain.models.session import Session
from app.domain.models.session_exposure import SessionExposureState


class ExposureHistoryUnknownError(ValueError):
    """Raised when Phase 7 provenance cannot be proven for a session."""


class OutcomeEvaluationPolicyConflictError(ValueError):
    """Raised when an immutable policy identity or session policy conflicts."""


class OutcomeStorageProvider(StorageProvider, Protocol):
    def save_tracked_session(
        self,
        session: Session,
        *,
        session_origin_time: datetime,
    ) -> None: ...

    def get_session_exposure_state(self, session_id: str) -> SessionExposureState | None: ...

    def record_session_exposure(
        self,
        session_id: str,
        exposed_at: datetime,
    ) -> SessionExposureState: ...

    def register_outcome_evaluation_policy(
        self,
        *,
        session_id: str,
        policy_id: str,
        config: OutcomeConfig,
    ) -> OutcomeEvaluationPolicy: ...
