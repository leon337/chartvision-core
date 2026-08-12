import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.outcome_storage_provider import OutcomeConflictError
from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.candle import Candle
from app.domain.models.outcome import OutcomeConfig
from app.domain.models.session import Session
from app.domain.services.outcome_evaluator import OutcomeEvaluator
from app.infrastructure.db.models import AnalysisRecord, SessionRecord
from app.infrastructure.db.phase7_models import OutcomeEvaluationPolicyRecord, OutcomeRecord
from app.infrastructure.storage.phase7_outcome_postgres_repository import (
    Phase7OutcomePostgresStorageRepository,
)

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
        connection.execute(delete(OutcomeRecord))
        connection.execute(delete(OutcomeEvaluationPolicyRecord))
        connection.execute(delete(AnalysisRecord))
        connection.execute(delete(SessionRecord))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return Phase7OutcomePostgresStorageRepository(session_factory=factory)


def _setup(repository, *, session_id: str = "session-1"):
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    session = Session(
        session_id=session_id,
        source_id="replay",
        asset="SAMPLE",
        timeframe="1m",
        started_at=origin,
    )
    repository.save_tracked_session(session, session_origin_time=origin)
    policy = repository.register_outcome_evaluation_policy(
        session_id=session_id,
        policy_id=f"policy-{session_id}",
        config=OutcomeConfig(3, Decimal("0.01")),
    )
    analysis = Analysis(
        analysis_id=f"analysis-{session_id}",
        session_id=session_id,
        timestamp=origin + timedelta(minutes=1),
        market_state=MarketState.UP,
        confidence=0.9,
        data_quality=0.9,
        evidence=("STATE_RULE=RISING_STRUCTURE",),
    )
    repository.save_analysis(analysis)
    reference = Candle(
        source_id="replay",
        session_id=session_id,
        asset="SAMPLE",
        timeframe="1m",
        open_time=origin,
        close_time=origin + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("100"),
        close=Decimal("100"),
        is_closed=True,
    )
    final = Candle(
        source_id="replay",
        session_id=session_id,
        asset="SAMPLE",
        timeframe="1m",
        open_time=origin + timedelta(minutes=3),
        close_time=origin + timedelta(minutes=4),
        open=Decimal("102"),
        high=Decimal("102"),
        low=Decimal("102"),
        close=Decimal("102"),
        is_closed=True,
    )
    outcome = OutcomeEvaluator.evaluate(
        analysis=analysis,
        policy=policy,
        reference_candle=reference,
        final_candle=final,
    )
    return policy, analysis, outcome


def test_outcome_round_trip_preserves_exact_values(repository) -> None:
    policy, _, outcome = _setup(repository)

    repository.save_outcome(outcome)
    loaded = repository.get_outcome(outcome.analysis_id)

    assert loaded == outcome
    assert loaded is not None
    assert loaded.policy_id == policy.policy_id
    assert loaded.realized_return == Decimal("0.02")
    assert loaded.evidence == outcome.evidence
    assert loaded.evaluation_timestamp.tzinfo is not None


def test_identical_outcome_is_idempotent(repository, engine) -> None:
    _, _, outcome = _setup(repository, session_id="idempotent")
    repository.save_outcome(outcome)
    repository.save_outcome(outcome)

    with engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(OutcomeRecord)).scalar_one()
    assert count == 1


def test_conflicting_outcome_for_same_analysis_is_rejected(repository) -> None:
    _, _, outcome = _setup(repository, session_id="conflict")
    repository.save_outcome(outcome)
    conflicting = replace(outcome, evidence=outcome.evidence + ("EXTRA=CONFLICT",))

    with pytest.raises(OutcomeConflictError):
        repository.save_outcome(conflicting)

    assert repository.get_outcome(outcome.analysis_id) == outcome


def test_list_outcomes_is_filtered_by_policy(repository) -> None:
    policy_a, _, outcome_a = _setup(repository, session_id="list-a")
    policy_b, _, outcome_b = _setup(repository, session_id="list-b")
    repository.save_outcome(outcome_a)
    repository.save_outcome(outcome_b)

    assert repository.list_outcomes(policy_a.policy_id) == (outcome_a,)
    assert repository.list_outcomes(policy_b.policy_id) == (outcome_b,)
