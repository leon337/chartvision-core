import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.observation import Observation
from app.domain.models.session import Session
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
    reason="real PostgreSQL persistence tests require CHARTVISION_POSTGRES_TEST_URL",
)

BASE = datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)


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


def _frame(frame_id: str, session_id: str, captured_at: datetime) -> Frame:
    return Frame(
        frame_id=frame_id,
        session_id=session_id,
        captured_at=captured_at,
        image_hash=f"hash-{frame_id}",
        width=800,
        height=560,
        changed_since_previous=True,
    )


def _observation(observation_id: str, frame: Frame) -> Observation:
    return Observation(
        observation_id=observation_id,
        session_id=frame.session_id,
        timestamp=frame.captured_at,
        frame_id=frame.frame_id,
        confidence=0.9,
        visual_quality=0.95,
    )


def _candle(
    session_id: str,
    *,
    open_time: datetime = BASE,
    high: str,
    low: str,
    close: str,
    is_closed: bool,
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
        vision_confidence=0.9,
        source_confidence=None,
    )


def _persist_observation(
    repository: PostgresStorageRepository,
    *,
    frame_id: str,
    session_id: str,
    timestamp: datetime,
    observation_id: str,
) -> Observation:
    frame = _frame(frame_id, session_id, timestamp)
    observation = _observation(observation_id, frame)
    repository.save_frame(frame)
    repository.save_observation(observation)
    return observation


def test_point_in_time_read_does_not_leak_later_candle_evolution(repository) -> None:
    session = _session("session-phase5-point-in-time")
    repository.save_session(session)
    t1 = BASE + timedelta(seconds=20)
    t2 = BASE + timedelta(seconds=40)
    t3 = BASE + timedelta(minutes=1, seconds=5)

    obs1 = _persist_observation(
        repository,
        frame_id="frame-phase5-t1",
        session_id=session.session_id,
        timestamp=t1,
        observation_id="obs-phase5-t1",
    )
    obs2 = _persist_observation(
        repository,
        frame_id="frame-phase5-t2",
        session_id=session.session_id,
        timestamp=t2,
        observation_id="obs-phase5-t2",
    )
    obs2_repeat = _persist_observation(
        repository,
        frame_id="frame-phase5-t2-repeat",
        session_id=session.session_id,
        timestamp=t2,
        observation_id="obs-phase5-t2-repeat",
    )
    obs3 = _persist_observation(
        repository,
        frame_id="frame-phase5-t3",
        session_id=session.session_id,
        timestamp=t3,
        observation_id="obs-phase5-t3",
    )

    state_t1 = _candle(
        session.session_id,
        high="103",
        low="99",
        close="101",
        is_closed=False,
    )
    state_t2 = _candle(
        session.session_id,
        high="104",
        low="98",
        close="99",
        is_closed=False,
    )
    state_t3 = _candle(
        session.session_id,
        high="105",
        low="97",
        close="102",
        is_closed=True,
    )

    repository.save_candle(state_t1, observation_id=obs1.observation_id)
    repository.save_candle(state_t2, observation_id=obs2.observation_id)
    repository.save_candle(state_t2, observation_id=obs2_repeat.observation_id)
    repository.save_candle(state_t3, observation_id=obs3.observation_id)

    assert repository.get_candle(session.session_id, BASE) == state_t3
    assert repository.get_candles_as_of(session.session_id, t1) == (state_t1,)
    assert repository.get_candles_as_of(session.session_id, t2) == (state_t2,)
    assert repository.get_candles_as_of(session.session_id, t3) == (state_t3,)
    assert repository.get_candles_as_of(session.session_id, t1) == (state_t1,)


def test_point_in_time_read_is_ordered_filters_future_and_isolates_sessions(repository) -> None:
    target = _session("session-phase5-target")
    other = _session("session-phase5-other")
    repository.save_session(target)
    repository.save_session(other)
    as_of = BASE + timedelta(seconds=30)
    later = BASE + timedelta(seconds=50)

    target_observation = _persist_observation(
        repository,
        frame_id="frame-phase5-target",
        session_id=target.session_id,
        timestamp=as_of,
        observation_id="obs-phase5-target",
    )
    future_observation = _persist_observation(
        repository,
        frame_id="frame-phase5-future",
        session_id=target.session_id,
        timestamp=later,
        observation_id="obs-phase5-future",
    )
    other_observation = _persist_observation(
        repository,
        frame_id="frame-phase5-other",
        session_id=other.session_id,
        timestamp=as_of,
        observation_id="obs-phase5-other",
    )

    first = _candle(
        target.session_id,
        open_time=BASE - timedelta(minutes=2),
        high="102",
        low="98",
        close="101",
        is_closed=True,
    )
    second = _candle(
        target.session_id,
        open_time=BASE - timedelta(minutes=1),
        high="103",
        low="99",
        close="102",
        is_closed=True,
    )
    third_at_cut = _candle(
        target.session_id,
        high="103",
        low="99",
        close="101",
        is_closed=False,
    )
    third_after_cut = _candle(
        target.session_id,
        high="104",
        low="98",
        close="99",
        is_closed=False,
    )
    other_session_candle = _candle(
        other.session_id,
        high="110",
        low="90",
        close="105",
        is_closed=False,
    )

    for candle in (third_at_cut, first, second):
        repository.save_candle(candle, observation_id=target_observation.observation_id)
    repository.save_candle(third_after_cut, observation_id=future_observation.observation_id)
    repository.save_candle(other_session_candle, observation_id=other_observation.observation_id)

    result = repository.get_candles_as_of(target.session_id, as_of)

    assert result == (first, second, third_at_cut)
    assert tuple(candle.open_time for candle in result) == tuple(
        sorted(candle.open_time for candle in result)
    )
    assert all(candle.session_id == target.session_id for candle in result)
    assert third_after_cut not in result
    assert other_session_candle not in result


def test_point_in_time_read_handles_empty_history_and_rejects_naive_as_of(repository) -> None:
    session = _session("session-phase5-empty")
    repository.save_session(session)
    observation = _persist_observation(
        repository,
        frame_id="frame-phase5-empty",
        session_id=session.session_id,
        timestamp=BASE + timedelta(seconds=20),
        observation_id="obs-phase5-empty",
    )
    candle = _candle(
        session.session_id,
        high="103",
        low="99",
        close="101",
        is_closed=False,
    )
    repository.save_candle(candle, observation_id=observation.observation_id)

    assert repository.get_candles_as_of(session.session_id, BASE) == ()

    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        repository.get_candles_as_of(
            session.session_id,
            datetime(2026, 8, 10, 20, 0),
        )
