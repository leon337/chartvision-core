from datetime import datetime

from app.domain.interfaces.ground_truth_provider import GroundTruthProvider
from app.domain.interfaces.outcome_storage_provider import OutcomeStorageProvider
from app.domain.models.outcome import ExposureTrackingState
from app.domain.models.outcome_evaluation import OutcomeAvailability, OutcomeEvaluationResult
from app.domain.services.outcome_evaluator import OutcomeEvaluator


class OutcomeEvaluationService:
    def __init__(
        self,
        *,
        storage: OutcomeStorageProvider,
        ground_truth_provider: GroundTruthProvider,
    ) -> None:
        self._storage = storage
        self._ground_truth_provider = ground_truth_provider

    def evaluate(
        self,
        analysis_id: str,
        evaluation_as_of: datetime,
    ) -> OutcomeEvaluationResult:
        analysis = self._storage.get_analysis(analysis_id)
        if analysis is None:
            raise ValueError(f"analysis_id {analysis_id!r} does not exist")
        self._require_aware(evaluation_as_of, "evaluation_as_of")
        if evaluation_as_of < analysis.timestamp:
            raise ValueError("evaluation_as_of cannot precede Analysis.timestamp")

        exposure = self._storage.get_session_exposure_state(analysis.session_id)
        if exposure is None or exposure.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN:
            return OutcomeEvaluationResult(OutcomeAvailability.EXPOSURE_HISTORY_UNKNOWN)

        policy = self._storage.get_outcome_evaluation_policy_for_session(analysis.session_id)
        if policy is None:
            return OutcomeEvaluationResult(OutcomeAvailability.UNAVAILABLE_POLICY)
        if policy.bound_at > analysis.timestamp:
            return OutcomeEvaluationResult(OutcomeAvailability.POLICY_BOUND_TOO_LATE)

        existing = self._storage.get_outcome(analysis.analysis_id)
        if existing is not None and existing.evaluation_timestamp <= evaluation_as_of:
            return OutcomeEvaluationResult(OutcomeAvailability.AVAILABLE, existing)

        window = self._ground_truth_provider.get_evaluation_window(
            analysis.session_id,
            analysis.timestamp,
            evaluation_as_of,
            policy.horizon_closed_candles,
        )
        if window.reference_candle is None:
            return OutcomeEvaluationResult(OutcomeAvailability.UNAVAILABLE_REFERENCE)
        if len(window.future_closed_candles) < policy.horizon_closed_candles:
            status = (
                OutcomeAvailability.UNAVAILABLE_END_OF_DATASET
                if window.source_exhausted
                else OutcomeAvailability.PENDING_HORIZON
            )
            return OutcomeEvaluationResult(status)

        final_candle = window.future_closed_candles[policy.horizon_closed_candles - 1]
        if final_candle.close_time > evaluation_as_of:
            raise ValueError("GroundTruthProvider returned future beyond evaluation_as_of")
        outcome = OutcomeEvaluator.evaluate(
            analysis=analysis,
            policy=policy,
            reference_candle=window.reference_candle,
            final_candle=final_candle,
        )
        self._storage.save_outcome(outcome)
        return OutcomeEvaluationResult(OutcomeAvailability.AVAILABLE, outcome)

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
