from sqlalchemy import select

from app.domain.interfaces.outcome_storage_provider import (
    ExposureHistoryUnknownError,
    OutcomeConflictError,
)
from app.domain.models.outcome import ExposureTrackingState, Outcome, RealizedState
from app.infrastructure.db.models import AnalysisRecord
from app.infrastructure.db.phase7_models import OutcomeEvaluationPolicyRecord, OutcomeRecord
from app.infrastructure.storage.phase7_postgres_repository import Phase7PostgresStorageRepository


class Phase7OutcomePostgresStorageRepository(Phase7PostgresStorageRepository):
    """Phase 7 PostgreSQL storage including immutable Outcomes."""

    def save_outcome(self, outcome: Outcome) -> None:
        db = self._session_factory()
        try:
            with db.begin():
                existing = db.get(OutcomeRecord, outcome.analysis_id)
                if existing is not None:
                    persisted = self._outcome_to_domain(existing)
                    if persisted == outcome:
                        return
                    raise OutcomeConflictError(
                        f"analysis_id {outcome.analysis_id!r} already has a different outcome"
                    )

                analysis = db.get(AnalysisRecord, outcome.analysis_id)
                if analysis is None:
                    raise ValueError(f"analysis_id {outcome.analysis_id!r} does not exist")
                policy_record = db.get(OutcomeEvaluationPolicyRecord, outcome.policy_id)
                if policy_record is None:
                    raise ValueError(f"policy_id {outcome.policy_id!r} does not exist")
                policy = self._policy_to_domain(policy_record)

                state = self._get_session_exposure_state_locked(db, analysis.session_id)
                if state is None or state.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN:
                    raise ExposureHistoryUnknownError(
                        f"session_id {analysis.session_id!r} has unknown exposure history"
                    )
                if policy.session_id != analysis.session_id:
                    raise OutcomeConflictError("policy and analysis must belong to the same session")
                analysis_timestamp = self._normalize_datetime(analysis.timestamp, "analysis.timestamp")
                if policy.bound_at > analysis_timestamp:
                    raise OutcomeConflictError("policy is too late for the analysis")
                if outcome.horizon_closed_candles != policy.horizon_closed_candles:
                    raise OutcomeConflictError("outcome horizon does not match policy")
                if outcome.realized_return_threshold != policy.realized_return_threshold:
                    raise OutcomeConflictError("outcome threshold does not match policy")

                db.add(self._outcome_to_record(outcome))
                db.flush()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_outcome(self, analysis_id: str) -> Outcome | None:
        db = self._session_factory()
        try:
            record = db.get(OutcomeRecord, analysis_id)
            return self._outcome_to_domain(record) if record is not None else None
        finally:
            db.close()

    def list_outcomes(self, policy_id: str) -> tuple[Outcome, ...]:
        db = self._session_factory()
        try:
            records = db.scalars(
                select(OutcomeRecord)
                .join(AnalysisRecord, OutcomeRecord.analysis_id == AnalysisRecord.analysis_id)
                .where(OutcomeRecord.policy_id == policy_id)
                .order_by(AnalysisRecord.timestamp, OutcomeRecord.analysis_id)
            ).all()
            return tuple(self._outcome_to_domain(record) for record in records)
        finally:
            db.close()

    @staticmethod
    def _outcome_to_record(outcome: Outcome) -> OutcomeRecord:
        return OutcomeRecord(
            analysis_id=outcome.analysis_id,
            policy_id=outcome.policy_id,
            evaluation_timestamp=outcome.evaluation_timestamp,
            reference_candle_open_time=outcome.reference_candle_open_time,
            reference_candle_close_time=outcome.reference_candle_close_time,
            reference_close=outcome.reference_close,
            final_candle_open_time=outcome.final_candle_open_time,
            final_candle_close_time=outcome.final_candle_close_time,
            final_close=outcome.final_close,
            horizon_closed_candles=outcome.horizon_closed_candles,
            realized_return_threshold=outcome.realized_return_threshold,
            realized_return=outcome.realized_return,
            realized_state=outcome.realized_state.value,
            evidence=list(outcome.evidence),
        )

    @classmethod
    def _outcome_to_domain(cls, record: OutcomeRecord) -> Outcome:
        evidence = record.evidence
        if not isinstance(evidence, list) or any(not isinstance(token, str) for token in evidence):
            raise ValueError("persisted outcome evidence must be a JSON array of strings")
        return Outcome(
            analysis_id=record.analysis_id,
            policy_id=record.policy_id,
            evaluation_timestamp=cls._normalize_datetime(
                record.evaluation_timestamp,
                "evaluation_timestamp",
            ),
            reference_candle_open_time=cls._normalize_datetime(
                record.reference_candle_open_time,
                "reference_candle_open_time",
            ),
            reference_candle_close_time=cls._normalize_datetime(
                record.reference_candle_close_time,
                "reference_candle_close_time",
            ),
            reference_close=record.reference_close,
            final_candle_open_time=cls._normalize_datetime(
                record.final_candle_open_time,
                "final_candle_open_time",
            ),
            final_candle_close_time=cls._normalize_datetime(
                record.final_candle_close_time,
                "final_candle_close_time",
            ),
            final_close=record.final_close,
            horizon_closed_candles=record.horizon_closed_candles,
            realized_return_threshold=record.realized_return_threshold,
            realized_return=record.realized_return,
            realized_state=RealizedState(record.realized_state),
            evidence=tuple(evidence),
        )
