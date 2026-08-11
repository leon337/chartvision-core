import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.domain.models.analysis import AnalysisConfig, MarketState
from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.observation import Observation
from app.domain.models.session import Session
from app.domain.services.analysis_lab_service import AnalysisLabService
from app.infrastructure.db.models import (
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
    reason="real PostgreSQL analysis tests require CHARTVISION_POSTGRES_TEST_URL",
)

BASE = datetime(2026, 8, 11, 5, 0, tzinfo=timezone.utc)
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
    is_closed: bool,
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


def _rising_history(session_id: str) -> tuple[Candle, ...]:
    return (
        _candle(
            session_id,
            open_time=BASE - timedelta(minutes=3),
            high="101",
            low="97",
            close="99",
            is_closed=True,
            vision_confidence=0.95,
        ),
        _candle(
            session_id,
            open_time=BASE - timedelta(minutes=2),
            high="102",
            low="98",
            close="100",
            is_closed=True,
            vision_confidence=0.9,
        ),
        _candle(
            session_id,
            open_time=BASE - timedelta(minutes=1),
            high="103",
            low="99",
            close="101",
            is_closed=True,
            vision_confidence=0.92,
        ),
    )


def _persist_history(
    repository: PostgresStorageRepository,
    *,
    session_id: str,
    as_of: datetime,
    suffix: str,
) -> tuple[Candle, ...]:
    observation = _observation(
        repository,
        session_id=session_id,
        timestamp=as_of,
        suffix=suffix,
    )
    candles = _rising_history(session_id)
    for candle in candles:
        repository.save_candle(candle, observation_id=observation.observation_id)
    return candles


def test_future_candle_does_not_change_historical_analysis(repository) -> None:
    session = _session("session-phase6-future-candle")
    repository.save_session(session)
    _persist_history(
        repository,
        session_id=session.session_id,
        as_of=BASE,
        suffix="phase6-future-candle-t",
    )
    service = AnalysisLabService(repository)

    before = service.analyze(session.session_id, BASE, CONFIG)

    future_observation = _observation(
        repository,
        session_id=session.session_id,
        timestamp=BASE + timedelta(minutes=2),
        suffix="phase6-future-candle-later",
    )
    future_candle = _candle(
        session.session_id,
        open_time=BASE + timedelta(minutes=1),
        high="120",
        low="80",
        close="85",
        is_closed=True,
        vision_confidence=0.1,
    )
    repository.save_candle(
        future_candle,
        observation_id=future_observation.observation_id,
    )

    after = service.analyze(session.session_id, BASE, CONFIG)

    assert before.market_state is MarketState.UP
    assert before == after
    assert future_candle not in repository.get_candles_as_of(session.session_id, BASE)


def test_future_snapshot_does_not_change_historical_analysis(repository) -> None:
    session = _session("session-phase6-future-snapshot")
    repository.save_session(session)
    _persist_history(
        repository,
        session_id=session.session_id,
        as_of=BASE,
        suffix="phase6-future-snapshot-t",
    )
    service = AnalysisLabService(repository)

    before = service.analyze(session.session_id, BASE, CONFIG)

    future_observation = _observation(
        repository,
        session_id=session.session_id,
        timestamp=BASE + timedelta(seconds=45),
        suffix="phase6-future-snapshot-later",
    )
    late_known_candle = _candle(
        session.session_id,
        open_time=BASE - timedelta(seconds=30),
        high="130",
        low="70",
        close="80",
        is_closed=True,
        vision_confidence=0.05,
    )
    repository.save_candle(
        late_known_candle,
        observation_id=future_observation.observation_id,
    )

    after = service.analyze(session.session_id, BASE, CONFIG)

    assert before.market_state is MarketState.UP
    assert before == after
    assert late_known_candle not in repository.get_candles_as_of(session.session_id, BASE)
    assert late_known_candle in repository.get_candles_as_of(
        session.session_id,
        future_observation.timestamp,
    )


def test_future_canonical_candle_evolution_does_not_change_historical_analysis(
    repository,
) -> None:
    session = _session("session-phase6-canonical-evolution")
    repository.save_session(session)
    observation_at_t = _observation(
        repository,
        session_id=session.session_id,
        timestamp=BASE,
        suffix="phase6-canonical-t",
    )
    for candle in _rising_history(session.session_id):
        repository.save_candle(candle, observation_id=observation_at_t.observation_id)

    evolving_open_time = BASE
    open_state = _candle(
        session.session_id,
        open_time=evolving_open_time,
        high="104",
        low="99",
        close="102",
        is_closed=False,
        vision_confidence=0.01,
    )
    repository.save_candle(open_state, observation_id=observation_at_t.observation_id)
    service = AnalysisLabService(repository)

    before = service.analyze(session.session_id, BASE, CONFIG)

    future_observation = _observation(
        repository,
        session_id=session.session_id,
        timestamp=BASE + timedelta(minutes=1, seconds=5),
        suffix="phase6-canonical-later",
    )
    final_state = _candle(
        session.session_id,
        open_time=evolving_open_time,
        high="110",
        low="80",
        close="85",
        is_closed=True,
        vision_confidence=0.99,
    )
    repository.save_candle(final_state, observation_id=future_observation.observation_id)

    current_canonical = repository.get_candle(session.session_id, evolving_open_time)
    historical_candles = repository.get_candles_as_of(session.session_id, BASE)
    after = service.analyze(session.session_id, BASE, CONFIG)

    assert before.market_state is MarketState.UP
    assert before.data_quality == 0.9
    assert current_canonical == final_state
    assert current_canonical != open_state
    assert open_state in historical_candles
    assert final_state not in historical_candles
    assert before == after


def test_analysis_remains_isolated_by_session(repository) -> None:
    target = _session("session-phase6-isolation-target")
    other = _session("session-phase6-isolation-other")
    repository.save_session(target)
    repository.save_session(other)
    _persist_history(
        repository,
        session_id=target.session_id,
        as_of=BASE,
        suffix="phase6-isolation-target",
    )
    service = AnalysisLabService(repository)

    before = service.analyze(target.session_id, BASE, CONFIG)

    other_observation = _observation(
        repository,
        session_id=other.session_id,
        timestamp=BASE,
        suffix="phase6-isolation-other",
    )
    other_candles = (
        _candle(
            other.session_id,
            open_time=BASE - timedelta(minutes=3),
            high="120",
            low="80",
            close="90",
            is_closed=True,
            vision_confidence=0.1,
        ),
        _candle(
            other.session_id,
            open_time=BASE - timedelta(minutes=2),
            high="110",
            low="70",
            close="80",
            is_closed=True,
            vision_confidence=0.1,
        ),
        _candle(
            other.session_id,
            open_time=BASE - timedelta(minutes=1),
            high="100",
            low="60",
            close="70",
            is_closed=True,
            vision_confidence=0.1,
        ),
    )
    for candle in other_candles:
        repository.save_candle(candle, observation_id=other_observation.observation_id)

    after = service.analyze(target.session_id, BASE, CONFIG)

    assert before.market_state is MarketState.UP
    assert before == after
    assert all(
        candle.session_id == target.session_id
        for candle in repository.get_candles_as_of(target.session_id, BASE)
    )
