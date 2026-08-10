from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as OrmSession

from app.domain.interfaces.storage_provider import SessionConflictError
from app.domain.models.session import Session
from app.infrastructure.db.models import SessionRecord
from app.infrastructure.db.session import SessionLocal

SessionFactory = Callable[[], OrmSession]


class PostgresStorageRepository:
    """PostgreSQL implementation of the current StorageProvider contract."""

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
                    db.add(self._to_record(normalized))
                    db.flush()
                    return

                persisted = self._to_domain(existing)
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
            return self._to_domain(record)
        finally:
            db.close()

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

    @staticmethod
    def _normalize_datetime(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _to_record(session: Session) -> SessionRecord:
        return SessionRecord(
            session_id=session.session_id,
            source_id=session.source_id,
            asset=session.asset,
            timeframe=session.timeframe,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )

    @classmethod
    def _to_domain(cls, record: SessionRecord) -> Session:
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
