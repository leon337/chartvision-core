import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.outcome_storage_provider import ExposureHistoryUnknownError
from app.domain.models.outcome import ExposureTrackingState
from app.domain.models.session import Session
from app.infrastructure.db.models import AnalysisRecord, SessionRecord
from app.infrastructure.storage.outcome_postgres_repository import OutcomePostgresStorageRepository
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
def repositories(engine):
    with engine.begin() as connection:
        connection.execute(delete(AnalysisRecord))
        connection.execute(delete(SessionRecord))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return (
        PostgresStorageRepository(session_factory=factory),
        OutcomePostgresStorageRepository(session_factory=factory),
    )


def _session(session_id: str) -> Session:
    return Session(
        session_id=session_id,
        source_id="replay",
        asset="SAMPLE",
        timeframe="1m",
        started_at=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
    )


def test_legacy_save_path_fails_closed(repositories) -> None:
    legacy_repository, outcome_repository = repositories
    legacy_repository.save_session(_session("legacy-session"))

    state = outcome_repository.get_session_exposure_state("legacy-session")

    assert state is not None
    assert state.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN
    assert state.session_origin_time is None
    assert state.session_exposure_watermark is None
    with pytest.raises(ExposureHistoryUnknownError):
        outcome_repository.record_session_exposure(
            "legacy-session",
            datetime(2026, 8, 12, 10, 1, tzinfo=timezone.utc),
        )


def test_tracked_session_starts_at_deterministic_origin(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)

    repository.save_tracked_session(_session("tracked-session"), session_origin_time=origin)
    state = repository.get_session_exposure_state("tracked-session")

    assert state is not None
    assert state.tracking_state is ExposureTrackingState.TRACKED
    assert state.session_origin_time == origin
    assert state.session_exposure_watermark == origin


def test_exposure_watermark_is_monotonic_and_lower_replay_does_not_rewind(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    repository.save_tracked_session(_session("monotonic"), session_origin_time=origin)

    high = repository.record_session_exposure("monotonic", origin + timedelta(minutes=30))
    lower = repository.record_session_exposure("monotonic", origin + timedelta(minutes=15))
    higher = repository.record_session_exposure("monotonic", origin + timedelta(minutes=45))

    assert high.session_exposure_watermark == origin + timedelta(minutes=30)
    assert lower.session_exposure_watermark == origin + timedelta(minutes=30)
    assert higher.session_exposure_watermark == origin + timedelta(minutes=45)
    assert repository.get_session_exposure_state("monotonic") == higher


def test_reinvoking_tracked_session_save_never_resets_advanced_watermark(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    session = _session("restart-safe")
    repository.save_tracked_session(session, session_origin_time=origin)
    repository.record_session_exposure("restart-safe", origin + timedelta(minutes=30))

    repository.save_tracked_session(session, session_origin_time=origin)
    state = repository.get_session_exposure_state("restart-safe")

    assert state is not None
    assert state.session_exposure_watermark == origin + timedelta(minutes=30)


def test_naive_origin_and_exposure_are_rejected(repositories) -> None:
    _, repository = repositories
    with pytest.raises(ValueError, match="session_origin_time must be timezone-aware"):
        repository.save_tracked_session(
            _session("naive-origin"),
            session_origin_time=datetime(2026, 8, 12, 10, 0),
        )

    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    repository.save_tracked_session(_session("naive-exposure"), session_origin_time=origin)
    with pytest.raises(ValueError, match="exposed_at must be timezone-aware"):
        repository.record_session_exposure(
            "naive-exposure",
            datetime(2026, 8, 12, 10, 1),
        )
