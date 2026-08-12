from datetime import datetime
from typing import Protocol

from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.models.outcome import Outcome, OutcomeConfig, OutcomeEvaluationPolicy
from app.domain.models.session import Session
from app.domain.models.session_exposure import SessionExposureState


class ExposureHistoryUnknownError(ValueError):
    """Raised when Phase 7 provenance cannot be proven for a session."""


class OutcomeEvaluationPolicyConflictError(ValueError):
    """Raised when an immutable policy identity or session policy conflicts."""


class OutcomeConflictError(ValueError):
    """Raised when immutable Outcome data conflicts for one analysis identity."""


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

    def get_outcome_evaluation_policy(
        self,
        policy_id: str,
    ) -> OutcomeEvaluationPolicy | None: ...

    def get_outcome_evaluation_policy_for_session(
        self,
        session_id: str,
    ) -> OutcomeEvaluationPolicy | None: ...

    def save_outcome(self, outcome: Outcome) -> None: ...

    def get_outcome(self, analysis_id: str) -> Outcome | None: ...

    def list_outcomes(self, policy_id: str) -> tuple[Outcome, ...]: ...
