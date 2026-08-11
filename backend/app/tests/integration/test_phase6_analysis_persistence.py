import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, inspect, select
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.storage_provider import AnalysisConflictError
from app.domain.models.analysis import Analysis, AnalysisConfig, MarketState
from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.observation import Observation
from app.domain.models.session import Session
from app.domain.services.analysis_lab_service import AnalysisLabService
from app.infrastructure.db.models import (
    AnalysisRecord,
    CandleRecord,
    CandleSnapshotRecord,
    FrameRecord,
    ObservationRecord,
    SessionRecord,
)
from app.infrastructure.storage.postgres_repository import PostgresStorageRepository

TEST_DATABASE_URL = os.getenv("CHARTVISION_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="real PostgreSQL analysis persistence tests require CHARTVISION_POSTGRES_TEST_URL",
)

BASE = datetime(2026, 8, 11, 6, 0, tzinfo=timezone.utc)
CONFIG = AnalysisConfig(
    trend_pairs=2,
    lateralization_window_candles=3,
    lateralization_max_range_ratio=Decimal("0.01"),
    minimum_data_quality=0.8,
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
        connection.execute(delete(AnalysisRecord))
        connection.execute(delete(CandleSnapshotRecord))
        connection.execute(delete(CandleRecord))
        connection.execute(delete(ObservationRecord))
        connection.execute(delete(FrameRecord))
        connection.execute(delete(SessionRecord))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return PostgresStorageRepository(session_factory=factory)


def _session(session_id: str) -> Session:
    return Session(
        session_id=session_id,
        source_id="replay-source",
        asset="TEST",
        timeframe="1m",
        started_at=BASE - timedelta(minutes=10),
    )


def _analysis(
    analysis_id: str = "analysis-1",
    session_id: str = "session-1",
    timestamp: datetime = BASE,
    market_state: MarketState = MarketState.UP,
    confidence: float = 0.9,
    data_quality: float | None = 0.9,
    evidence: tuple[str, ...] = (
        "STATE_RULE=RISING_STRUCTURE",
        "BASIC_TREND=RISING_STRUCTURE",
        "BASIC_LATERALIZATION=FALSE",
        "DATA_QUALITY=0.9",
        "TREND_PAIRS=2",
        "LATERALIZATION_WINDOW_CANDLES=3",
        "LATERALIZATION_MAX_RANGE_RATIO=0.01",
        "MINIMUM_DATA_QUALITY=0.8",
    ),
) -> Analysis:
    return Analysis(
        analysis_id=analysis_id,
        session_id=session_id,
        timestamp=timestamp,
        market_state=market_state,
        confidence=confidence,
        data_quality=data_quality,
        evidence=evidence,
    )


def _observation(
    repository: PostgresStorageRepository,
    *,
    session_id: str,
    timestamp: datetime,
    suffix: str,
) -> Observation:
    frame = Frame(
        frame_id=f"frame-{suffix}",
        session_id=session_id,
        captured_at=timestamp,
        image_hash=f"hash-{suffix}",
        width=800,
        height=560,
        changed_since_previous=True,
    )
    observation = Observation(
        observation_id=f"obs-{suffix}",
        session_id=session_id,
        timestamp=timestamp,
        frame_id=frame.frame_id,
        confidence=0.9,
        visual_quality=0.95,
    )
    repository.save_frame(frame)
    repository.save_observation(observation)
    return observation


def _candle(
    session_id: str,
    *,
    open_time: datetime,
    high: str,
    low: str,
    close: str,
    is_closed: bool = True,
    vision_confidence: float | None = 0.9,
) -> Candle:
    return Candle(
        source_id="vision",
        session_id=session_id,
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        is_closed=is_closed,
        vision_confidence=vision_confidence,
        source_confidence=None,
    )


def _persist_rising_history(
    repository: PostgresStorageRepository,
    *,
    session_id: str,
    as_of: datetime,
    suffix: str,
) -> None:
    observation = _observation(
        repository,
        session_id=session_id,
        timestamp=as_of,
        suffix=suffix,
    )
    candles = (
        _candle(
            session_id,
            open_time=BASE - timedelta(minutes=3),
            high="101",
            low="97",
            close="99",
            vision_confidence=0.95,
        ),
        _candle(
            session_id,
            open_time=BASE - timedelta(minutes=2),
            high="102",
            low="98",
            close="100",
            vision_confidence=0.9,
        ),
        _candle(
            session_id,
            open_time=BASE - timedelta(minutes=1),
            high="103",
            low="99",
            close="101",
            vision_confidence=0.92,
        ),
    )
    for candle in candles:
        repository.save_candle(candle, observation_id=observation.observation_id)


def test_migration_creates_analyses_table(engine) -> None:
    db_inspector = inspect(engine)
    assert "analyses" in db_inspector.get_table_names()

    columns = {column["name"]: column for column in db_inspector.get_columns("analyses")}
    assert tuple(columns) == (
        "analysis_id",
        "session_id",
        "timestamp",
        "market_state",
        "confidence",
        "data_quality",
        "evidence",
    )
    assert db_inspector.get_pk_constraint("analyses")["constrained_columns"] == [
        "analysis_id"
    ]
    foreign_keys = db_inspector.get_foreign_keys("analyses")
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["session_id"]
    assert foreign_keys[0]["referred_table"] == "sessions"
    assert foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
    assert columns["data_quality"]["nullable"] is True
    assert columns["evidence"]["nullable"] is False


def test_save_get_analysis_round_trip(repository) -> None:
    repository.save_session(_session("session-1"))
    analysis = _analysis()

    repository.save_analysis(analysis)

    assert repository.get_analysis(analysis.analysis_id) == analysis


def test_uncertain_with_none_data_quality_round_trips(repository) -> None:
    repository.save_session(_session("session-1"))
    analysis = _analysis(
        analysis_id="analysis-uncertain",
        market_state=MarketState.UNCERTAIN,
        confidence=0.0,
        data_quality=None,
        evidence=(
            "STATE_RULE=INSUFFICIENT_HISTORY",
            "BASIC_TREND=NONE",
            "BASIC_LATERALIZATION=NONE",
            "DATA_QUALITY=NONE",
        ),
    )

    repository.save_analysis(analysis)

    assert repository.get_analysis(analysis.analysis_id) == analysis


def test_evidence_order_is_preserved(repository) -> None:
    repository.save_session(_session("session-1"))
    evidence = ("FIRST", "SECOND", "THIRD")
    analysis = _analysis(analysis_id="analysis-order", evidence=evidence)

    repository.save_analysis(analysis)
    persisted = repository.get_analysis(analysis.analysis_id)

    assert persisted is not None
    assert persisted.evidence == evidence


def test_timezone_aware_timestamp_round_trips_and_normalizes_to_utc(repository) -> None:
    repository.save_session(_session("session-1"))
    local_tz = timezone(timedelta(hours=-3))
    timestamp = datetime(2026, 8, 11, 3, 0, tzinfo=local_tz)
    analysis = _analysis(analysis_id="analysis-timezone", timestamp=timestamp)

    repository.save_analysis(analysis)
    persisted = repository.get_analysis(analysis.analysis_id)

    assert persisted is not None
    assert persisted.timestamp == timestamp
    assert persisted.timestamp == BASE
    assert persisted.timestamp.utcoffset() == timedelta(0)


def test_same_analysis_is_idempotent(repository, engine) -> None:
    repository.save_session(_session("session-1"))
    analysis = _analysis(analysis_id="analysis-idempotent")

    repository.save_analysis(analysis)
    repository.save_analysis(analysis)

    with engine.connect() as connection:
        count = connection.scalar(
            select(func.count()).select_from(AnalysisRecord).where(
                AnalysisRecord.analysis_id == analysis.analysis_id
            )
        )
    assert count == 1
    assert repository.get_analysis(analysis.analysis_id) == analysis


def test_different_analysis_ids_do_not_deduplicate_same_analysis_data(repository, engine) -> None:
    repository.save_session(_session("session-1"))
    first = _analysis(analysis_id="analysis-distinct-1")
    second = replace(first, analysis_id="analysis-distinct-2")

    repository.save_analysis(first)
    repository.save_analysis(second)

    with engine.connect() as connection:
        count = connection.scalar(select(func.count()).select_from(AnalysisRecord))

    assert count == 2
    assert repository.get_analysis(first.analysis_id) == first
    assert repository.get_analysis(second.analysis_id) == second


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_id", "session-other"),
        ("timestamp", BASE + timedelta(seconds=1)),
        ("market_state", MarketState.DOWN),
        ("confidence", 0.8),
        ("data_quality", 0.85),
        ("evidence", ("DIFFERENT",)),
    ],
)
def test_same_analysis_id_with_changed_data_conflicts(repository, field, value) -> None:
    repository.save_session(_session("session-1"))
    repository.save_session(_session("session-other"))
    original = _analysis(analysis_id="analysis-conflict")
    repository.save_analysis(original)

    changed = replace(original, **{field: value})

    with pytest.raises(AnalysisConflictError, match="already exists with different data"):
        repository.save_analysis(changed)
    assert repository.get_analysis(original.analysis_id) == original


def test_missing_session_is_rejected(repository) -> None:
    analysis = _analysis(analysis_id="analysis-no-session", session_id="missing-session")

    with pytest.raises(ValueError, match="session_id 'missing-session' does not exist"):
        repository.save_analysis(analysis)


def test_get_missing_analysis_returns_none(repository) -> None:
    assert repository.get_analysis("missing-analysis") is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("analysis_id", "   ", "analysis_id must be a non-empty string"),
        ("session_id", "", "session_id must be a non-empty string"),
        ("timestamp", datetime(2026, 8, 11, 6, 0), "timestamp must be timezone-aware"),
        ("confidence", -0.1, "confidence must be between 0.0 and 1.0"),
        ("confidence", float("inf"), "confidence must be between 0.0 and 1.0"),
        ("data_quality", 1.1, "data_quality must be between 0.0 and 1.0"),
        ("data_quality", float("nan"), "data_quality must be between 0.0 and 1.0"),
        ("market_state", "UP", "market_state must be a MarketState"),
        ("evidence", ("VALID", 1), "evidence must be a tuple of strings"),
    ],
)
def test_invalid_analysis_is_rejected_before_insert(repository, field, value, message) -> None:
    repository.save_session(_session("session-1"))
    invalid = replace(_analysis(analysis_id="analysis-invalid"), **{field: value})

    with pytest.raises(ValueError, match=message):
        repository.save_analysis(invalid)
    assert repository.get_analysis("analysis-invalid") is None


def test_analyze_and_record_round_trip_preserves_as_of(repository) -> None:
    session = _session("session-service")
    repository.save_session(session)
    _persist_rising_history(
        repository,
        session_id=session.session_id,
        as_of=BASE,
        suffix="phase6-record",
    )
    service = AnalysisLabService(repository)

    analysis = service.analyze_and_record(
        analysis_id="analysis-service",
        session_id=session.session_id,
        as_of=BASE,
        config=CONFIG,
    )
    persisted = repository.get_analysis("analysis-service")

    assert analysis.market_state is MarketState.UP
    assert analysis.timestamp == BASE
    assert persisted == analysis
    assert persisted is not None
    assert persisted.timestamp == BASE
    assert persisted.evidence[-4:] == (
        "TREND_PAIRS=2",
        "LATERALIZATION_WINDOW_CANDLES=3",
        "LATERALIZATION_MAX_RANGE_RATIO=0.01",
        "MINIMUM_DATA_QUALITY=0.8",
    )


def test_future_data_cannot_change_or_duplicate_recorded_analysis(repository, engine) -> None:
    session = _session("session-future-immutable")
    repository.save_session(session)
    _persist_rising_history(
        repository,
        session_id=session.session_id,
        as_of=BASE,
        suffix="phase6-immutable-t",
    )
    service = AnalysisLabService(repository)

    first = service.analyze_and_record(
        analysis_id="analysis-T",
        session_id=session.session_id,
        as_of=BASE,
        config=CONFIG,
    )

    future_observation = _observation(
        repository,
        session_id=session.session_id,
        timestamp=BASE + timedelta(minutes=2),
        suffix="phase6-immutable-future",
    )
    future_candle = _candle(
        session.session_id,
        open_time=BASE + timedelta(minutes=1),
        high="130",
        low="70",
        close="80",
        is_closed=True,
        vision_confidence=0.05,
    )
    repository.save_candle(
        future_candle,
        observation_id=future_observation.observation_id,
    )

    second = service.analyze_and_record(
        analysis_id="analysis-T",
        session_id=session.session_id,
        as_of=BASE,
        config=CONFIG,
    )
    persisted = repository.get_analysis("analysis-T")

    with engine.connect() as connection:
        count = connection.scalar(
            select(func.count()).select_from(AnalysisRecord).where(
                AnalysisRecord.analysis_id == "analysis-T"
            )
        )

    assert first == second
    assert persisted == first
    assert first.timestamp == BASE
    assert count == 1
    assert future_candle not in repository.get_candles_as_of(session.session_id, BASE)
