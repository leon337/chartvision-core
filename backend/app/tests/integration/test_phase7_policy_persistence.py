import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.outcome_storage_provider import (
    ExposureHistoryUnknownError,
    OutcomeEvaluationPolicyConflictError,
)
from app.domain.models.outcome import OutcomeConfig
from app.domain.models.session import Session
from app.infrastructure.db.models import AnalysisRecord, SessionRecord
from app.infrastructure.db.phase7_models import OutcomeEvaluationPolicyRecord
from app.infrastructure.storage.phase7_postgres_repository import Phase7PostgresStorageRepository
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
        connection.execute(delete(OutcomeEvaluationPolicyRecord))
        connection.execute(delete(AnalysisRecord))
        connection.execute(delete(SessionRecord))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return (
        PostgresStorageRepository(session_factory=factory),
        Phase7PostgresStorageRepository(session_factory=factory),
    )


def _session(session_id: str) -> Session:
    return Session(
        session_id=session_id,
        source_id="replay",
        asset="SAMPLE",
        timeframe="1m",
        started_at=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
    )


def test_policy_captures_authoritative_watermark(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    repository.save_tracked_session(_session("policy-session"), session_origin_time=origin)
    watermark = origin + timedelta(minutes=30)
    repository.record_session_exposure("policy-session", watermark)

    policy = repository.register_outcome_evaluation_policy(
        session_id="policy-session",
        policy_id="policy-1",
        config=OutcomeConfig(3, Decimal("0.01")),
    )

    assert policy.bound_at == watermark
    assert repository.get_outcome_evaluation_policy("policy-1") == policy
    assert repository.get_outcome_evaluation_policy_for_session("policy-session") == policy


def test_legacy_session_cannot_register_policy(repositories) -> None:
    legacy_repository, repository = repositories
    legacy_repository.save_session(_session("legacy-policy"))

    with pytest.raises(ExposureHistoryUnknownError):
        repository.register_outcome_evaluation_policy(
            session_id="legacy-policy",
            policy_id="policy-legacy",
            config=OutcomeConfig(3, Decimal("0.01")),
        )

    assert repository.get_outcome_evaluation_policy("policy-legacy") is None


def test_identical_policy_is_idempotent_and_does_not_rebind_after_more_exposure(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    repository.save_tracked_session(_session("idempotent-policy"), session_origin_time=origin)
    first_watermark = origin + timedelta(minutes=10)
    repository.record_session_exposure("idempotent-policy", first_watermark)
    config = OutcomeConfig(4, Decimal("0.0123456789012345678901234567"))

    first = repository.register_outcome_evaluation_policy(
        session_id="idempotent-policy",
        policy_id="policy-idempotent",
        config=config,
    )
    repository.record_session_exposure("idempotent-policy", origin + timedelta(minutes=40))
    second = repository.register_outcome_evaluation_policy(
        session_id="idempotent-policy",
        policy_id="policy-idempotent",
        config=config,
    )

    assert second == first
    assert second.bound_at == first_watermark
    assert second.realized_return_threshold == config.realized_return_threshold


def test_same_policy_id_with_different_config_conflicts(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    repository.save_tracked_session(_session("policy-conflict"), session_origin_time=origin)
    repository.register_outcome_evaluation_policy(
        session_id="policy-conflict",
        policy_id="policy-conflict-id",
        config=OutcomeConfig(3, Decimal("0.01")),
    )

    with pytest.raises(OutcomeEvaluationPolicyConflictError):
        repository.register_outcome_evaluation_policy(
            session_id="policy-conflict",
            policy_id="policy-conflict-id",
            config=OutcomeConfig(4, Decimal("0.01")),
        )


def test_second_policy_for_same_session_conflicts(repositories) -> None:
    _, repository = repositories
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    repository.save_tracked_session(_session("single-policy"), session_origin_time=origin)
    repository.register_outcome_evaluation_policy(
        session_id="single-policy",
        policy_id="policy-a",
        config=OutcomeConfig(3, Decimal("0.01")),
    )

    with pytest.raises(OutcomeEvaluationPolicyConflictError):
        repository.register_outcome_evaluation_policy(
            session_id="single-policy",
            policy_id="policy-b",
            config=OutcomeConfig(3, Decimal("0.01")),
        )
