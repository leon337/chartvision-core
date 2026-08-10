import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.storage_provider import SessionConflictError
from app.domain.models.session import Session
from app.infrastructure.db.models import SessionRecord
from app.infrastructure.storage.postgres_repository import PostgresStorageRepository

TEST_DATABASE_URL = os.getenv("CHARTVISION_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="real PostgreSQL persistence tests require CHARTVISION_POSTGRES_TEST_URL",
)


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[3]
    return Config(str(backend_root / "alembic.ini"))


@pytest.fixture(scope="module")
def engine():
    assert TEST_DATABASE_URL is not None
    command.upgrade(_alembic_config(), "head")
    database_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield database_engine
    database_engine.dispose()


@pytest.fixture()
def repository(engine):
    with engine.begin() as connection:
        connection.execute(delete(SessionRecord))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return PostgresStorageRepository(session_factory=factory)


def _active_session(session_id: str = "session-001") -> Session:
    return Session(
        session_id=session_id,
        source_id="replay-source",
        asset="BTCUSD",
        timeframe="1m",
        started_at=datetime(2026, 8, 10, 15, 0, tzinfo=timezone(timedelta(hours=-3))),
    )


def test_migration_created_sessions_table(engine) -> None:
    inspector = inspect(engine)
    assert "sessions" in inspector.get_table_names()


def test_round_trip_active_session_preserves_all_fields_and_timezone(repository) -> None:
    original = _active_session()

    repository.save_session(original)
    loaded = repository.get_session(original.session_id)

    assert loaded is not None
    assert loaded.session_id == original.session_id
    assert loaded.source_id == original.source_id
    assert loaded.asset == original.asset
    assert loaded.timeframe == original.timeframe
    assert loaded.started_at == original.started_at
    assert loaded.started_at.tzinfo is not None
    assert loaded.started_at.utcoffset() == timedelta(0)
    assert loaded.ended_at is None


def test_round_trip_closed_session_preserves_ended_at(repository) -> None:
    started_at = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)
    original = Session(
        session_id="session-closed",
        source_id="replay-source",
        asset="ETHUSD",
        timeframe="1m",
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=5),
    )

    repository.save_session(original)
    loaded = repository.get_session(original.session_id)

    assert loaded is not None
    assert loaded == original
    assert loaded.ended_at is not None
    assert loaded.ended_at.utcoffset() == timedelta(0)


def test_saving_identical_session_is_idempotent(repository, engine) -> None:
    original = _active_session("session-idempotent")

    repository.save_session(original)
    repository.save_session(original)

    with engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(SessionRecord)).scalar_one()
    assert count == 1


def test_conflicting_payload_for_same_session_id_fails_and_preserves_history(repository) -> None:
    original = _active_session("session-conflict")
    repository.save_session(original)
    conflicting = Session(
        session_id=original.session_id,
        source_id=original.source_id,
        asset="DIFFERENT",
        timeframe=original.timeframe,
        started_at=original.started_at,
    )

    with pytest.raises(SessionConflictError):
        repository.save_session(conflicting)

    assert repository.get_session(original.session_id) == original


def test_constraint_failure_rolls_back_transaction(repository) -> None:
    invalid = Session(
        session_id="session-invalid",
        source_id="",
        asset="BTCUSD",
        timeframe="1m",
        started_at=datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(IntegrityError):
        repository.save_session(invalid)

    assert repository.get_session(invalid.session_id) is None
    repository.save_session(_active_session(invalid.session_id))
    assert repository.get_session(invalid.session_id) is not None


def test_naive_timestamp_is_rejected_explicitly(repository) -> None:
    naive = Session(
        session_id="session-naive",
        source_id="replay-source",
        asset="BTCUSD",
        timeframe="1m",
        started_at=datetime(2026, 8, 10, 18, 0),
    )

    with pytest.raises(ValueError, match="started_at must be timezone-aware"):
        repository.save_session(naive)

    assert repository.get_session(naive.session_id) is None


def test_naive_ended_at_is_rejected_explicitly(repository) -> None:
    started_at = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)
    naive = Session(
        session_id="session-naive-end",
        source_id="replay-source",
        asset="BTCUSD",
        timeframe="1m",
        started_at=started_at,
        ended_at=datetime(2026, 8, 10, 18, 5),
    )

    with pytest.raises(ValueError, match="ended_at must be timezone-aware"):
        repository.save_session(naive)

    assert repository.get_session(naive.session_id) is None
