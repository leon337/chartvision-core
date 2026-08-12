from app.domain.interfaces.outcome_storage_provider import (
    ExposureHistoryUnknownError,
    OutcomeStorageProvider,
)
from app.domain.models.outcome import ExposureTrackingState
from app.domain.models.outcome_metrics import EvaluatedAnalysis, OutcomeMetricsReport
from app.domain.services.outcome_metrics_engine import OutcomeMetricsEngine


class OutcomeMetricsService:
    def __init__(self, storage: OutcomeStorageProvider) -> None:
        self._storage = storage

    def report(self, policy_id: str) -> OutcomeMetricsReport:
        policy = self._storage.get_outcome_evaluation_policy(policy_id)
        if policy is None:
            raise ValueError(f"policy_id {policy_id!r} does not exist")
        exposure = self._storage.get_session_exposure_state(policy.session_id)
        if exposure is None or exposure.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN:
            raise ExposureHistoryUnknownError(
                f"session_id {policy.session_id!r} has unknown exposure history"
            )

        pairs: list[EvaluatedAnalysis] = []
        for outcome in self._storage.list_outcomes(policy.policy_id):
            analysis = self._storage.get_analysis(outcome.analysis_id)
            if analysis is None:
                raise ValueError(
                    f"persisted outcome references missing analysis_id {outcome.analysis_id!r}"
                )
            pairs.append(EvaluatedAnalysis(analysis=analysis, outcome=outcome))
        return OutcomeMetricsEngine.calculate(policy, tuple(pairs))
