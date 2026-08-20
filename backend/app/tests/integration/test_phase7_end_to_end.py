import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.storage_provider import SessionConflictError
from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.candle import Candle
from app.domain.models.outcome import ExposureTrackingState, OutcomeConfig
from app.domain.models.outcome_evaluation import OutcomeAvailability
from app.domain.models.session import Session
from app.domain.services.outcome_evaluation_service import OutcomeEvaluationService
from app.domain.services.outcome_metrics_service import OutcomeMetricsService
from app.infrastructure.db.models import AnalysisRecord, SessionRecord
from app.infrastructure.db.phase7_models import OutcomeEvaluationPolicyRecord, OutcomeRecord
from app.infrastructure.replay.ground_truth_provider import ReplayGroundTruthProvider
from app.infrastructure.replay.replay_session_factory import ReplaySessionFactory
from app.infrastructure.storage.phase7_outcome_postgres_repository import (
    Phase7OutcomePostgresStorageRepository,
)

TEST_DATABASE_URL = os.getenv("CHARTVISION_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="real PostgreSQL Phase 7 integration tests require CHARTVISION_POSTGRES_TEST_URL",
)

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


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


def _session(session_id: str) -> Session:
    return Session(
        session_id=session_id,
        source_id="replay",
        asset="SAMPLE",
        timeframe="1m",
        started_at=T0,
    )


def _candles(session_id: str, count: int = 8) -> tuple[Candle, ...]:
    result = []
    for index in range(count):
        open_time = T0 + timedelta(minutes=index)
        price = Decimal(100 + index)
        result.append(
            Candle(
                source_id="replay",
                session_id=session_id,
                asset="SAMPLE",
                timeframe="1m",
                open_time=open_time,
                close_time=open_time + timedelta(minutes=1),
                open=price,
                high=price,
                low=price,
                close=price,
                is_closed=True,
                source_confidence=1.0,
            )
        )
    return tuple(result)


def _analysis(session_id: str, analysis_id: str, timestamp: datetime) -> Analysis:
    return Analysis(
        analysis_id=analysis_id,
        session_id=session_id,
        timestamp=timestamp,
        market_state=MarketState.UP,
        confidence=0.9,
        data_quality=0.9,
        evidence=("STATE_RULE=RISING_STRUCTURE",),
    )


def test_pending_then_available_persists_outcome_and_metrics_without_mutating_analysis(repository) -> None:
    session_id = "phase7-e2e"
    tracked = ReplaySessionFactory(repository).from_candles(_candles(session_id, 6))
    policy = tracked.register_policy(
        policy_id="phase7-e2e-policy",
        config=OutcomeConfig(3, Decimal("0.01")),
    )
    analysis = _analysis(session_id, "phase7-e2e-analysis", T0 + timedelta(minutes=1))
    repository.save_analysis(analysis)
    provider = ReplayGroundTruthProvider(_candles(session_id, 6))
    service = OutcomeEvaluationService(storage=repository, ground_truth_provider=provider)

    pending = service.evaluate(analysis.analysis_id, T0 + timedelta(minutes=2))
    assert pending.status is OutcomeAvailability.PENDING_HORIZON
    assert repository.get_outcome(analysis.analysis_id) is None

    available = service.evaluate(analysis.analysis_id, T0 + timedelta(minutes=4))
    assert available.status is OutcomeAvailability.AVAILABLE
    assert available.outcome is not None
    assert available.outcome.policy_id == policy.policy_id
    assert available.outcome.reference_close == Decimal("100")
    assert available.outcome.final_close == Decimal("103")
    assert available.outcome.final_candle_close_time == T0 + timedelta(minutes=4)
    assert repository.get_analysis(analysis.analysis_id) == analysis
    assert repository.get_outcome_evaluation_policy(policy.policy_id) == policy

    repeated = service.evaluate(analysis.analysis_id, T0 + timedelta(minutes=5))
    assert repeated == available
    report = OutcomeMetricsService(repository).report(policy.policy_id)
    assert report.total_evaluated == 1
    assert report.accuracy == Decimal("1")
    assert report.coverage == Decimal("1")


def test_future_exposed_then_reset_cannot_backdate_policy_for_historical_analysis(repository) -> None:
    session_id = "phase7-reset-proof"
    candles = _candles(session_id)
    tracked = ReplaySessionFactory(repository).from_candles(candles)
    tracked.start()
    tracked.advance(seconds=180)
    assert repository.get_session_exposure_state(session_id).session_exposure_watermark == (
        T0 + timedelta(minutes=3)
    )

    tracked.reset()
    policy = tracked.register_policy(
        policy_id="phase7-reset-policy",
        config=OutcomeConfig(2, Decimal("0.01")),
    )
    assert policy.bound_at == T0 + timedelta(minutes=3)

    analysis = _analysis(session_id, "phase7-before-watermark", T0 + timedelta(minutes=2))
    repository.save_analysis(analysis)
    service = OutcomeEvaluationService(
        storage=repository,
        ground_truth_provider=ReplayGroundTruthProvider(candles),
    )
    result = service.evaluate(analysis.analysis_id, T0 + timedelta(minutes=6))

    assert result.status is OutcomeAvailability.POLICY_BOUND_TOO_LATE
    assert repository.get_outcome(analysis.analysis_id) is None
    assert repository.get_session_exposure_state(session_id).session_exposure_watermark == (
        T0 + timedelta(minutes=3)
    )


def test_restart_with_new_repository_instance_preserves_watermark_for_policy(engine, repository) -> None:
    session_id = "phase7-restart-proof"
    candles = _candles(session_id)
    first = ReplaySessionFactory(repository).from_candles(candles)
    first.start()
    first.advance(seconds=180)

    restarted_repository = Phase7OutcomePostgresStorageRepository(
        session_factory=sessionmaker(bind=engine, expire_on_commit=False)
    )
    restarted = ReplaySessionFactory(restarted_repository).from_candles(candles)
    policy = restarted.register_policy(
        policy_id="phase7-restart-policy",
        config=OutcomeConfig(2, Decimal("0.01")),
    )

    assert policy.bound_at == T0 + timedelta(minutes=3)
    state = restarted_repository.get_session_exposure_state(session_id)
    assert state is not None
    assert state.tracking_state is ExposureTrackingState.TRACKED
    assert state.session_origin_time == T0
    assert state.session_exposure_watermark == T0 + timedelta(minutes=3)


def test_legacy_session_cannot_be_promoted_through_tracked_factory(repository) -> None:
    session_id = "phase7-legacy-no-promotion"
    repository.save_session(_session(session_id))

    with pytest.raises(SessionConflictError, match="incompatible provenance"):
        ReplaySessionFactory(repository).from_candles(_candles(session_id))

    state = repository.get_session_exposure_state(session_id)
    assert state is not None
    assert state.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN
    assert state.session_origin_time is None
    assert state.session_exposure_watermark is None


def test_legacy_session_and_new_tracked_session_remain_independent(repository) -> None:
    repository.save_session(_session("phase7-legacy-independent"))
    tracked = ReplaySessionFactory(repository).from_candles(_candles("phase7-fresh-tracked"))
    policy = tracked.register_policy(
        policy_id="phase7-fresh-policy",
        config=OutcomeConfig(2, Decimal("0.01")),
    )

    legacy_state = repository.get_session_exposure_state("phase7-legacy-independent")
    tracked_state = repository.get_session_exposure_state("phase7-fresh-tracked")
    assert legacy_state is not None
    assert legacy_state.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN
    assert tracked_state is not None
    assert tracked_state.tracking_state is ExposureTrackingState.TRACKED
    assert policy.bound_at == T0


def test_legacy_analysis_is_preserved_but_ineligible_for_outcome(repository) -> None:
    session_id = "phase7-legacy-analysis"
    repository.save_session(_session(session_id))
    analysis = _analysis(session_id, "phase7-legacy-analysis-id", T0 + timedelta(minutes=1))
    repository.save_analysis(analysis)
    service = OutcomeEvaluationService(
        storage=repository,
        ground_truth_provider=ReplayGroundTruthProvider(_candles(session_id)),
    )

    result = service.evaluate(analysis.analysis_id, T0 + timedelta(minutes=6))

    assert result.status is OutcomeAvailability.EXPOSURE_HISTORY_UNKNOWN
    assert repository.get_analysis(analysis.analysis_id) == analysis
    assert repository.get_outcome(analysis.analysis_id) is None
