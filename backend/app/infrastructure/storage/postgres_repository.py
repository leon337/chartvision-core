from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from math import isfinite

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as OrmSession

from app.domain.interfaces.storage_provider import (
    AnalysisConflictError,
    CandleConflictError,
    FrameConflictError,
    ObservationConflictError,
    SessionConflictError,
)
from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.observation import Observation
from app.domain.models.session import Session
from app.infrastructure.db.models import (
    AnalysisRecord,
    CandleRecord,
    CandleSnapshotRecord,
    FrameRecord,
    ObservationRecord,
    SessionRecord,
)
from app.infrastructure.db.session import SessionLocal

SessionFactory = Callable[[], OrmSession]


class PostgresStorageRepository:
    """PostgreSQL implementation of the StorageProvider contract."""

    def __init__(self, session_factory: SessionFactory = SessionLocal) -> None:
        self._session_factory = session_factory

    def healthcheck(self) -> bool:
        db = self._session_factory()
        try:
            return db.execute(text("SELECT 1")).scalar_one() == 1
        except SQLAlchemyError:
            db.rollback()
            return False
        finally:
            db.close()

    def save_session(self, session: Session) -> None:
        normalized = self._normalize_session(session)
        db = self._session_factory()
        try:
            with db.begin():
                existing = db.get(SessionRecord, normalized.session_id)
                if existing is None:
                    db.add(self._session_to_record(normalized))
                    db.flush()
                    return

                persisted = self._session_to_domain(existing)
                if persisted == normalized:
                    return

                raise SessionConflictError(
                    f"session_id {normalized.session_id!r} already exists with different data"
                )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_session(self, session_id: str) -> Session | None:
        db = self._session_factory()
        try:
            record = db.get(SessionRecord, session_id)
            if record is None:
                return None
            return self._session_to_domain(record)
        finally:
            db.close()

    def save_frame(self, frame: Frame) -> None:
        normalized = self._normalize_frame(frame)
        db = self._session_factory()
        try:
            with db.begin():
                existing = db.get(FrameRecord, normalized.frame_id)
                if existing is None:
                    db.add(self._frame_to_record(normalized))
                    db.flush()
                    return

                persisted = self._frame_to_domain(existing)
                if persisted == normalized:
                    return

                raise FrameConflictError(
                    f"frame_id {normalized.frame_id!r} already exists with different data"
                )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_frame(self, frame_id: str) -> Frame | None:
        db = self._session_factory()
        try:
            record = db.get(FrameRecord, frame_id)
            if record is None:
                return None
            return self._frame_to_domain(record)
        finally:
            db.close()

    def save_observation(self, observation: Observation) -> None:
        normalized = self._normalize_observation(observation)
        db = self._session_factory()
        try:
            with db.begin():
                existing = db.get(ObservationRecord, normalized.observation_id)
                if existing is None:
                    db.add(self._observation_to_record(normalized))
                    db.flush()
                    return

                persisted = self._observation_to_domain(existing)
                if persisted == normalized:
                    return

                raise ObservationConflictError(
                    f"observation_id {normalized.observation_id!r} already exists with different data"
                )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_observation(self, observation_id: str) -> Observation | None:
        db = self._session_factory()
        try:
            record = db.get(ObservationRecord, observation_id)
            if record is None:
                return None
            return self._observation_to_domain(record)
        finally:
            db.close()

    def save_candle(self, candle: Candle, *, observation_id: str) -> None:
        normalized = self._normalize_candle(candle)
        db = self._session_factory()
        try:
            with db.begin():
                observation = db.get(ObservationRecord, observation_id)
                if observation is None:
                    raise ValueError(f"observation_id {observation_id!r} does not exist")
                if observation.session_id != normalized.session_id:
                    raise CandleConflictError(
                        "observation and candle must belong to the same session"
                    )

                same_timestamp_snapshot = self._snapshot_at_timestamp(
                    db,
                    session_id=normalized.session_id,
                    open_time=normalized.open_time,
                    timestamp=observation.timestamp,
                )
                if (
                    same_timestamp_snapshot is not None
                    and self._snapshot_to_domain(same_timestamp_snapshot) != normalized
                ):
                    raise CandleConflictError(
                        "same candle timestamp already has different reconstructed data"
                    )

                identity = (normalized.session_id, normalized.open_time)
                existing = db.get(CandleRecord, identity)
                if existing is None:
                    db.add(self._candle_to_record(normalized))
                    db.flush()
                else:
                    persisted = self._candle_to_domain(existing)
                    if persisted != normalized:
                        latest_timestamp = self._latest_snapshot_timestamp(
                            db,
                            session_id=normalized.session_id,
                            open_time=normalized.open_time,
                        )
                        if (
                            latest_timestamp is not None
                            and observation.timestamp <= latest_timestamp
                        ):
                            self._validate_historical_candle(persisted, normalized)
                        else:
                            self._apply_candle_evolution(existing, persisted, normalized)
                            db.flush()

                snapshot_identity = (
                    observation_id,
                    normalized.session_id,
                    normalized.open_time,
                )
                existing_snapshot = db.get(CandleSnapshotRecord, snapshot_identity)
                if existing_snapshot is None:
                    db.add(self._candle_to_snapshot(normalized, observation_id))
                    db.flush()
                elif self._snapshot_to_domain(existing_snapshot) != normalized:
                    raise CandleConflictError(
                        "persisted candle snapshot cannot be overwritten"
                    )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_candle(self, session_id: str, open_time: datetime) -> Candle | None:
        normalized_open_time = self._normalize_datetime(open_time, "open_time")
        db = self._session_factory()
        try:
            record = db.get(CandleRecord, (session_id, normalized_open_time))
            if record is None:
                return None
            return self._candle_to_domain(record)
        finally:
            db.close()

    def get_candles_for_frame(self, frame_id: str) -> tuple[Candle, ...]:
        db = self._session_factory()
        try:
            statement = (
                select(CandleSnapshotRecord)
                .join(
                    ObservationRecord,
                    CandleSnapshotRecord.observation_id
                    == ObservationRecord.observation_id,
                )
                .where(ObservationRecord.frame_id == frame_id)
                .order_by(ObservationRecord.timestamp, CandleSnapshotRecord.open_time)
            )
            snapshots = db.scalars(statement).all()
            return tuple(self._snapshot_to_domain(snapshot) for snapshot in snapshots)
        finally:
            db.close()

    def get_candles_as_of(self, session_id: str, as_of: datetime) -> tuple[Candle, ...]:
        normalized_as_of = self._normalize_datetime(as_of, "as_of")
        db = self._session_factory()
        try:
            ranked_snapshots = (
                select(
                    CandleSnapshotRecord.observation_id.label("observation_id"),
                    CandleSnapshotRecord.session_id.label("session_id"),
                    CandleSnapshotRecord.open_time.label("open_time"),
                    func.row_number()
                    .over(
                        partition_by=(
                            CandleSnapshotRecord.session_id,
                            CandleSnapshotRecord.open_time,
                        ),
                        order_by=(
                            ObservationRecord.timestamp.desc(),
                            CandleSnapshotRecord.observation_id.desc(),
                        ),
                    )
                    .label("snapshot_rank"),
                )
                .join(
                    ObservationRecord,
                    CandleSnapshotRecord.observation_id
                    == ObservationRecord.observation_id,
                )
                .where(
                    CandleSnapshotRecord.session_id == session_id,
                    ObservationRecord.session_id == session_id,
                    ObservationRecord.timestamp <= normalized_as_of,
                )
                .subquery()
            )
            statement = (
                select(CandleSnapshotRecord)
                .join(
                    ranked_snapshots,
                    (
                        CandleSnapshotRecord.observation_id
                        == ranked_snapshots.c.observation_id
                    )
                    & (CandleSnapshotRecord.session_id == ranked_snapshots.c.session_id)
                    & (CandleSnapshotRecord.open_time == ranked_snapshots.c.open_time),
                )
                .where(ranked_snapshots.c.snapshot_rank == 1)
                .order_by(CandleSnapshotRecord.open_time)
            )
            snapshots = db.scalars(statement).all()
            return tuple(self._snapshot_to_domain(snapshot) for snapshot in snapshots)
        finally:
            db.close()

    def save_analysis(self, analysis: Analysis) -> None:
        normalized = self._normalize_analysis(analysis)
        db = self._session_factory()
        try:
            with db.begin():
                existing = db.get(AnalysisRecord, normalized.analysis_id)
                if existing is not None:
                    persisted = self._analysis_to_domain(existing)
                    if persisted == normalized:
                        return
                    raise AnalysisConflictError(
                        f"analysis_id {normalized.analysis_id!r} already exists with different data"
                    )

                if db.get(SessionRecord, normalized.session_id) is None:
                    raise ValueError(
                        f"session_id {normalized.session_id!r} does not exist"
                    )

                db.add(self._analysis_to_record(normalized))
                db.flush()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_analysis(self, analysis_id: str) -> Analysis | None:
        db = self._session_factory()
        try:
            record = db.get(AnalysisRecord, analysis_id)
            if record is None:
                return None
            return self._analysis_to_domain(record)
        finally:
            db.close()

    @classmethod
    def _snapshot_at_timestamp(
        cls,
        db: OrmSession,
        *,
        session_id: str,
        open_time: datetime,
        timestamp: datetime,
    ) -> CandleSnapshotRecord | None:
        statement = (
            select(CandleSnapshotRecord)
            .join(
                ObservationRecord,
                CandleSnapshotRecord.observation_id == ObservationRecord.observation_id,
            )
            .where(
                CandleSnapshotRecord.session_id == session_id,
                CandleSnapshotRecord.open_time == open_time,
                ObservationRecord.timestamp == timestamp,
            )
            .limit(1)
        )
        return db.scalars(statement).first()

    @staticmethod
    def _latest_snapshot_timestamp(
        db: OrmSession,
        *,
        session_id: str,
        open_time: datetime,
    ) -> datetime | None:
        statement = (
            select(func.max(ObservationRecord.timestamp))
            .join(
                CandleSnapshotRecord,
                CandleSnapshotRecord.observation_id == ObservationRecord.observation_id,
            )
            .where(
                CandleSnapshotRecord.session_id == session_id,
                CandleSnapshotRecord.open_time == open_time,
            )
        )
        return db.execute(statement).scalar_one()

    @classmethod
    def _validate_historical_candle(cls, current: Candle, historical: Candle) -> None:
        cls._validate_candle_identity(current, historical)
        if historical.is_closed:
            if not current.is_closed or historical != current:
                raise CandleConflictError(
                    "historical closed candle conflicts with the persisted final candle"
                )
            return
        if historical.high > current.high or historical.low < current.low:
            raise CandleConflictError(
                "historical candle exceeds the persisted candle price range"
            )

    @classmethod
    def _apply_candle_evolution(
        cls,
        record: CandleRecord,
        current: Candle,
        candidate: Candle,
    ) -> None:
        cls._validate_candle_identity(current, candidate)
        if current.is_closed:
            raise CandleConflictError("closed candle history is immutable")
        if candidate.high < current.high:
            raise CandleConflictError("open candle high cannot decrease")
        if candidate.low > current.low:
            raise CandleConflictError("open candle low cannot increase")

        record.high = candidate.high
        record.low = candidate.low
        record.close = candidate.close
        record.is_closed = candidate.is_closed
        record.vision_confidence = candidate.vision_confidence
        record.source_confidence = candidate.source_confidence

    @staticmethod
    def _validate_candle_identity(current: Candle, candidate: Candle) -> None:
        immutable_fields = (
            "source_id",
            "session_id",
            "asset",
            "timeframe",
            "open_time",
            "close_time",
            "open",
        )
        changed = [
            field
            for field in immutable_fields
            if getattr(current, field) != getattr(candidate, field)
        ]
        if changed:
            raise CandleConflictError(
                f"candle identity fields cannot change: {', '.join(changed)}"
            )

    @classmethod
    def _normalize_session(cls, session: Session) -> Session:
        started_at = cls._normalize_datetime(session.started_at, "started_at")
        ended_at = (
            cls._normalize_datetime(session.ended_at, "ended_at")
            if session.ended_at is not None
            else None
        )
        return Session(
            session_id=session.session_id,
            source_id=session.source_id,
            asset=session.asset,
            timeframe=session.timeframe,
            started_at=started_at,
            ended_at=ended_at,
        )

    @classmethod
    def _normalize_frame(cls, frame: Frame) -> Frame:
        return Frame(
            frame_id=frame.frame_id,
            session_id=frame.session_id,
            captured_at=cls._normalize_datetime(frame.captured_at, "captured_at"),
            image_hash=frame.image_hash,
            width=frame.width,
            height=frame.height,
            changed_since_previous=frame.changed_since_previous,
            storage_reference=frame.storage_reference,
        )

    @classmethod
    def _normalize_observation(cls, observation: Observation) -> Observation:
        return Observation(
            observation_id=observation.observation_id,
            session_id=observation.session_id,
            timestamp=cls._normalize_datetime(observation.timestamp, "timestamp"),
            frame_id=observation.frame_id,
            confidence=observation.confidence,
            visual_quality=observation.visual_quality,
        )

    @classmethod
    def _normalize_candle(cls, candle: Candle) -> Candle:
        return Candle(
            source_id=candle.source_id,
            session_id=candle.session_id,
            asset=candle.asset,
            timeframe=candle.timeframe,
            open_time=cls._normalize_datetime(candle.open_time, "open_time"),
            close_time=cls._normalize_datetime(candle.close_time, "close_time"),
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            is_closed=candle.is_closed,
            vision_confidence=candle.vision_confidence,
            source_confidence=candle.source_confidence,
        )

    @classmethod
    def _normalize_analysis(cls, analysis: Analysis) -> Analysis:
        if not isinstance(analysis.analysis_id, str) or not analysis.analysis_id.strip():
            raise ValueError("analysis_id must be a non-empty string")
        if not isinstance(analysis.session_id, str) or not analysis.session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(analysis.market_state, MarketState):
            raise ValueError("market_state must be a MarketState")
        cls._validate_unit_interval(analysis.confidence, "confidence")
        if analysis.data_quality is not None:
            cls._validate_unit_interval(analysis.data_quality, "data_quality")
        if not isinstance(analysis.evidence, tuple) or any(
            not isinstance(token, str) for token in analysis.evidence
        ):
            raise ValueError("evidence must be a tuple of strings")

        return Analysis(
            analysis_id=analysis.analysis_id,
            session_id=analysis.session_id,
            timestamp=cls._normalize_datetime(analysis.timestamp, "timestamp"),
            market_state=analysis.market_state,
            confidence=float(analysis.confidence),
            data_quality=(
                float(analysis.data_quality)
                if analysis.data_quality is not None
                else None
            ),
            evidence=analysis.evidence,
        )

    @staticmethod
    def _validate_unit_interval(value: float, field_name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be a finite number between 0.0 and 1.0")
        if not isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0")

    @staticmethod
    def _normalize_datetime(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _session_to_record(session: Session) -> SessionRecord:
        return SessionRecord(
            session_id=session.session_id,
            source_id=session.source_id,
            asset=session.asset,
            timeframe=session.timeframe,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )

    @staticmethod
    def _frame_to_record(frame: Frame) -> FrameRecord:
        return FrameRecord(
            frame_id=frame.frame_id,
            session_id=frame.session_id,
            captured_at=frame.captured_at,
            image_hash=frame.image_hash,
            width=frame.width,
            height=frame.height,
            changed_since_previous=frame.changed_since_previous,
            storage_reference=frame.storage_reference,
        )

    @staticmethod
    def _observation_to_record(observation: Observation) -> ObservationRecord:
        return ObservationRecord(
            observation_id=observation.observation_id,
            session_id=observation.session_id,
            timestamp=observation.timestamp,
            frame_id=observation.frame_id,
            confidence=observation.confidence,
            visual_quality=observation.visual_quality,
        )

    @staticmethod
    def _candle_to_record(candle: Candle) -> CandleRecord:
        return CandleRecord(
            session_id=candle.session_id,
            source_id=candle.source_id,
            asset=candle.asset,
            timeframe=candle.timeframe,
            open_time=candle.open_time,
            close_time=candle.close_time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            is_closed=candle.is_closed,
            vision_confidence=candle.vision_confidence,
            source_confidence=candle.source_confidence,
        )

    @staticmethod
    def _candle_to_snapshot(candle: Candle, observation_id: str) -> CandleSnapshotRecord:
        return CandleSnapshotRecord(
            observation_id=observation_id,
            session_id=candle.session_id,
            source_id=candle.source_id,
            asset=candle.asset,
            timeframe=candle.timeframe,
            open_time=candle.open_time,
            close_time=candle.close_time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            is_closed=candle.is_closed,
            vision_confidence=candle.vision_confidence,
            source_confidence=candle.source_confidence,
        )

    @staticmethod
    def _analysis_to_record(analysis: Analysis) -> AnalysisRecord:
        return AnalysisRecord(
            analysis_id=analysis.analysis_id,
            session_id=analysis.session_id,
            timestamp=analysis.timestamp,
            market_state=analysis.market_state.value,
            confidence=analysis.confidence,
            data_quality=analysis.data_quality,
            evidence=list(analysis.evidence),
        )

    @classmethod
    def _session_to_domain(cls, record: SessionRecord) -> Session:
        return Session(
            session_id=record.session_id,
            source_id=record.source_id,
            asset=record.asset,
            timeframe=record.timeframe,
            started_at=cls._normalize_datetime(record.started_at, "started_at"),
            ended_at=(
                cls._normalize_datetime(record.ended_at, "ended_at")
                if record.ended_at is not None
                else None
            ),
        )

    @classmethod
    def _frame_to_domain(cls, record: FrameRecord) -> Frame:
        return Frame(
            frame_id=record.frame_id,
            session_id=record.session_id,
            captured_at=cls._normalize_datetime(record.captured_at, "captured_at"),
            image_hash=record.image_hash,
            width=record.width,
            height=record.height,
            changed_since_previous=record.changed_since_previous,
            storage_reference=record.storage_reference,
        )

    @classmethod
    def _observation_to_domain(cls, record: ObservationRecord) -> Observation:
        return Observation(
            observation_id=record.observation_id,
            session_id=record.session_id,
            timestamp=cls._normalize_datetime(record.timestamp, "timestamp"),
            frame_id=record.frame_id,
            confidence=record.confidence,
            visual_quality=record.visual_quality,
        )

    @classmethod
    def _candle_to_domain(cls, record: CandleRecord) -> Candle:
        return Candle(
            source_id=record.source_id,
            session_id=record.session_id,
            asset=record.asset,
            timeframe=record.timeframe,
            open_time=cls._normalize_datetime(record.open_time, "open_time"),
            close_time=cls._normalize_datetime(record.close_time, "close_time"),
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            is_closed=record.is_closed,
            vision_confidence=record.vision_confidence,
            source_confidence=record.source_confidence,
        )

    @classmethod
    def _snapshot_to_domain(cls, record: CandleSnapshotRecord) -> Candle:
        return Candle(
            source_id=record.source_id,
            session_id=record.session_id,
            asset=record.asset,
            timeframe=record.timeframe,
            open_time=cls._normalize_datetime(record.open_time, "open_time"),
            close_time=cls._normalize_datetime(record.close_time, "close_time"),
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            is_closed=record.is_closed,
            vision_confidence=record.vision_confidence,
            source_confidence=record.source_confidence,
        )

    @classmethod
    def _analysis_to_domain(cls, record: AnalysisRecord) -> Analysis:
        evidence = record.evidence
        if not isinstance(evidence, list) or any(
            not isinstance(token, str) for token in evidence
        ):
            raise ValueError("persisted analysis evidence must be a JSON array of strings")
        return cls._normalize_analysis(
            Analysis(
                analysis_id=record.analysis_id,
                session_id=record.session_id,
                timestamp=record.timestamp,
                market_state=MarketState(record.market_state),
                confidence=record.confidence,
                data_quality=record.data_quality,
                evidence=tuple(evidence),
            )
        )
