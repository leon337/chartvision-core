import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.outcome_storage_provider import ExposureHistoryUnknownError
from app.domain.models.outcome import ExposureTrackingState, OutcomeConfig
from app.domain.models.session import Session
from app.infrastructure.storage.phase7_outcome_postgres_repository import (
    Phase7OutcomePostgresStorageRepository,
)
from app.infrastructure.storage.postgres_repository import PostgresStorageRepository

TEST_DATABASE_URL = os.getenv("CHARTVISION_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="real PostgreSQL migration tests require CHARTVISION_POSTGRES_TEST_URL",
)


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[3]
    return Config(str(backend_root / "alembic.ini"))


def test_existing_session_migrates_fail_closed_without_invented_provenance() -> None:
    assert TEST_DATABASE_URL is not None
    config = _alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "0005_create_analyses")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    legacy = PostgresStorageRepository(session_factory=factory)
    session = Session(
        session_id="phase7-preexisting-session",
        source_id="replay",
        asset="SAMPLE",
        timeframe="1m",
        started_at=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM analyses WHERE session_id = :session_id"),
                {"session_id": session.session_id},
            )
            connection.execute(
                text("DELETE FROM sessions WHERE session_id = :session_id"),
                {"session_id": session.session_id},
            )
        legacy.save_session(session)

        command.upgrade(config, "head")
        repository = Phase7OutcomePostgresStorageRepository(session_factory=factory)
        state = repository.get_session_exposure_state(session.session_id)

        assert state is not None
        assert state.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN
        assert state.session_origin_time is None
        assert state.session_exposure_watermark is None
        with pytest.raises(ExposureHistoryUnknownError):
            repository.register_outcome_evaluation_policy(
                session_id=session.session_id,
                policy_id="must-not-exist",
                config=OutcomeConfig(3, Decimal("0.01")),
            )
        assert repository.get_outcome_evaluation_policy("must-not-exist") is None
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM sessions WHERE session_id = :session_id"),
                {"session_id": session.session_id},
            )
        engine.dispose()
