from sqlalchemy import select

from app.domain.interfaces.outcome_storage_provider import (
    ExposureHistoryUnknownError,
    OutcomeEvaluationPolicyConflictError,
)
from app.domain.models.outcome import (
    ExposureTrackingState,
    OutcomeConfig,
    OutcomeEvaluationPolicy,
)
from app.infrastructure.db.phase7_models import OutcomeEvaluationPolicyRecord
from app.infrastructure.storage.outcome_postgres_repository import OutcomePostgresStorageRepository


class Phase7PostgresStorageRepository(OutcomePostgresStorageRepository):
    """PostgreSQL storage with atomic Phase 7 policy registration."""

    def register_outcome_evaluation_policy(
        self,
        *,
        session_id: str,
        policy_id: str,
        config: OutcomeConfig,
    ) -> OutcomeEvaluationPolicy:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError("policy_id must be a non-empty string")

        db = self._session_factory()
        try:
            with db.begin():
                state = self._get_session_exposure_state_locked(db, session_id)
                if state is None:
                    raise ValueError(f"session_id {session_id!r} does not exist")
                if state.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN:
                    raise ExposureHistoryUnknownError(
                        f"session_id {session_id!r} has unknown exposure history"
                    )
                assert state.session_exposure_watermark is not None

                existing_by_id = db.get(OutcomeEvaluationPolicyRecord, policy_id)
                if existing_by_id is not None:
                    persisted = self._policy_to_domain(existing_by_id)
                    if (
                        persisted.session_id == session_id
                        and persisted.config == config
                    ):
                        return persisted
                    raise OutcomeEvaluationPolicyConflictError(
                        f"policy_id {policy_id!r} already exists with different data"
                    )

                existing_for_session = db.scalars(
                    select(OutcomeEvaluationPolicyRecord).where(
                        OutcomeEvaluationPolicyRecord.session_id == session_id
                    )
                ).first()
                if existing_for_session is not None:
                    raise OutcomeEvaluationPolicyConflictError(
                        f"session_id {session_id!r} already has an outcome evaluation policy"
                    )

                policy = OutcomeEvaluationPolicy(
                    policy_id=policy_id,
                    session_id=session_id,
                    horizon_closed_candles=config.horizon_closed_candles,
                    realized_return_threshold=config.realized_return_threshold,
                    bound_at=state.session_exposure_watermark,
                )
                db.add(self._policy_to_record(policy))
                db.flush()
                return policy
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_outcome_evaluation_policy(
        self,
        policy_id: str,
    ) -> OutcomeEvaluationPolicy | None:
        db = self._session_factory()
        try:
            record = db.get(OutcomeEvaluationPolicyRecord, policy_id)
            return self._policy_to_domain(record) if record is not None else None
        finally:
            db.close()

    def get_outcome_evaluation_policy_for_session(
        self,
        session_id: str,
    ) -> OutcomeEvaluationPolicy | None:
        db = self._session_factory()
        try:
            record = db.scalars(
                select(OutcomeEvaluationPolicyRecord).where(
                    OutcomeEvaluationPolicyRecord.session_id == session_id
                )
            ).first()
            return self._policy_to_domain(record) if record is not None else None
        finally:
            db.close()

    @staticmethod
    def _policy_to_record(policy: OutcomeEvaluationPolicy) -> OutcomeEvaluationPolicyRecord:
        return OutcomeEvaluationPolicyRecord(
            policy_id=policy.policy_id,
            session_id=policy.session_id,
            horizon_closed_candles=policy.horizon_closed_candles,
            realized_return_threshold=policy.realized_return_threshold,
            bound_at=policy.bound_at,
        )

    @classmethod
    def _policy_to_domain(
        cls,
        record: OutcomeEvaluationPolicyRecord,
    ) -> OutcomeEvaluationPolicy:
        return OutcomeEvaluationPolicy(
            policy_id=record.policy_id,
            session_id=record.session_id,
            horizon_closed_candles=record.horizon_closed_candles,
            realized_return_threshold=record.realized_return_threshold,
            bound_at=cls._normalize_datetime(record.bound_at, "bound_at"),
        )
