from datetime import datetime, timezone

from sqlalchemy import text

from app.domain.interfaces.outcome_storage_provider import ExposureHistoryUnknownError
from app.domain.interfaces.storage_provider import SessionConflictError
from app.domain.models.outcome import ExposureTrackingState
from app.domain.models.session import Session
from app.domain.models.session_exposure import SessionExposureState
from app.infrastructure.db.models import SessionRecord
from app.infrastructure.storage.postgres_repository import PostgresStorageRepository


class OutcomePostgresStorageRepository(PostgresStorageRepository):
    """Phase 7 PostgreSQL extensions without changing legacy Session semantics."""

    def save_tracked_session(
        self,
        session: Session,
        *,
        session_origin_time: datetime,
    ) -> None:
        normalized = self._normalize_session(session)
        origin = self._normalize_datetime(session_origin_time, "session_origin_time")
        db = self._session_factory()
        try:
            with db.begin():
                existing = db.get(SessionRecord, normalized.session_id)
                if existing is None:
                    db.execute(
                        text(
                            """
                            INSERT INTO sessions (
                                session_id, source_id, asset, timeframe, started_at, ended_at,
                                exposure_tracking_state, session_origin_time,
                                session_exposure_watermark
                            ) VALUES (
                                :session_id, :source_id, :asset, :timeframe, :started_at, :ended_at,
                                'TRACKED', :origin, :origin
                            )
                            """
                        ),
                        {
                            "session_id": normalized.session_id,
                            "source_id": normalized.source_id,
                            "asset": normalized.asset,
                            "timeframe": normalized.timeframe,
                            "started_at": normalized.started_at,
                            "ended_at": normalized.ended_at,
                            "origin": origin,
                        },
                    )
                    return

                persisted = self._session_to_domain(existing)
                state = self._get_session_exposure_state_locked(db, normalized.session_id)
                if (
                    persisted == normalized
                    and state is not None
                    and state.tracking_state is ExposureTrackingState.TRACKED
                    and state.session_origin_time == origin
                ):
                    return
                raise SessionConflictError(
                    f"session_id {normalized.session_id!r} already exists with incompatible provenance"
                )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_session_exposure_state(self, session_id: str) -> SessionExposureState | None:
        db = self._session_factory()
        try:
            row = db.execute(
                text(
                    """
                    SELECT exposure_tracking_state, session_origin_time,
                           session_exposure_watermark
                    FROM sessions
                    WHERE session_id = :session_id
                    """
                ),
                {"session_id": session_id},
            ).mappings().first()
            if row is None:
                return None
            return self._exposure_row_to_domain(session_id, row)
        finally:
            db.close()

    def record_session_exposure(
        self,
        session_id: str,
        exposed_at: datetime,
    ) -> SessionExposureState:
        normalized_exposed_at = self._normalize_datetime(exposed_at, "exposed_at")
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
                if normalized_exposed_at > state.session_exposure_watermark:
                    db.execute(
                        text(
                            """
                            UPDATE sessions
                            SET session_exposure_watermark = :watermark
                            WHERE session_id = :session_id
                            """
                        ),
                        {"watermark": normalized_exposed_at, "session_id": session_id},
                    )
                    return SessionExposureState(
                        session_id=session_id,
                        tracking_state=ExposureTrackingState.TRACKED,
                        session_origin_time=state.session_origin_time,
                        session_exposure_watermark=normalized_exposed_at,
                    )
                return state
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _get_session_exposure_state_locked(
        self,
        db,
        session_id: str,
    ) -> SessionExposureState | None:
        row = db.execute(
            text(
                """
                SELECT exposure_tracking_state, session_origin_time,
                       session_exposure_watermark
                FROM sessions
                WHERE session_id = :session_id
                FOR UPDATE
                """
            ),
            {"session_id": session_id},
        ).mappings().first()
        if row is None:
            return None
        return self._exposure_row_to_domain(session_id, row)

    @staticmethod
    def _exposure_row_to_domain(session_id: str, row) -> SessionExposureState:
        origin = row["session_origin_time"]
        watermark = row["session_exposure_watermark"]
        if origin is not None and origin.tzinfo is None:
            origin = origin.replace(tzinfo=timezone.utc)
        if watermark is not None and watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        return SessionExposureState(
            session_id=session_id,
            tracking_state=ExposureTrackingState(row["exposure_tracking_state"]),
            session_origin_time=origin,
            session_exposure_watermark=watermark,
        )
