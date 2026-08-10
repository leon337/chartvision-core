import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.storage_provider import (
    CandleConflictError,
    ObservationConflictError,
)
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

BASE = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)


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


def _session(session_id: str = "session-temporal") -> Session:
    return Session(
        session_id=session_id,
        source_id="replay-source",
        asset="TEST",
        timeframe="1m",
        started_at=BASE - timedelta(minutes=5),
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


def _observation(
    observation_id: str,
    frame: Frame,
    *,
    timestamp: datetime | None = None,
    confidence: float = 0.9,
    visual_quality: float = 0.95,
) -> Observation:
    return Observation(
        observation_id=observation_id,
        session_id=frame.session_id,
        timestamp=timestamp or frame.captured_at,
        frame_id=frame.frame_id,
        confidence=confidence,
        visual_quality=visual_quality,
    )


def _candle(
    session_id: str,
    *,
    high: str,
    low: str,
    close: str,
    is_closed: bool,
    open_time: datetime = BASE,
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


def _persist_observation(repository, frame: Frame, observation: Observation) -> None:
    repository.save_frame(frame)
    repository.save_observation(observation)


def test_migrations_create_temporal_tables_and_traceability_constraints(engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"sessions", "frames", "observations", "candles", "candle_snapshots"} <= tables

    observation_fks = inspector.get_foreign_keys("observations")
    assert any(
        fk["referred_table"] == "frames"
        and fk["constrained_columns"] == ["frame_id", "session_id"]
        and fk["referred_columns"] == ["frame_id", "session_id"]
        for fk in observation_fks
    )

    candle_pk = inspector.get_pk_constraint("candles")
    assert candle_pk["constrained_columns"] == ["session_id", "open_time"]

    snapshot_fks = inspector.get_foreign_keys("candle_snapshots")
    assert any(fk["referred_table"] == "observations" for fk in snapshot_fks)
    assert any(fk["referred_table"] == "candles" for fk in snapshot_fks)


def test_observation_round_trip_is_utc_and_idempotent(repository, engine) -> None:
    session = _session("session-observation")
    repository.save_session(session)
    frame = _frame(
        "frame-observation",
        session.session_id,
        datetime(2026, 8, 10, 15, 0, 5, tzinfo=timezone(timedelta(hours=-3))),
    )
    repository.save_frame(frame)
    original = _observation("observation-1", frame)

    repository.save_observation(original)
    repository.save_observation(original)
    loaded = repository.get_observation(original.observation_id)

    assert loaded == original
    assert loaded is not None
    assert loaded.timestamp.utcoffset() == timedelta(0)
    with engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(ObservationRecord)).scalar_one()
    assert count == 1


def test_observation_conflict_preserves_original(repository) -> None:
    session = _session("session-observation-conflict")
    repository.save_session(session)
    frame = _frame("frame-observation-conflict", session.session_id, BASE)
    repository.save_frame(frame)
    original = _observation("observation-conflict", frame)
    repository.save_observation(original)
    conflicting = Observation(
        observation_id=original.observation_id,
        session_id=original.session_id,
        timestamp=original.timestamp,
        frame_id=original.frame_id,
        confidence=0.1,
        visual_quality=original.visual_quality,
    )

    with pytest.raises(ObservationConflictError):
        repository.save_observation(conflicting)

    assert repository.get_observation(original.observation_id) == original


def test_observation_cannot_cross_frame_session_boundary(repository) -> None:
    first_session = _session("session-observation-a")
    second_session = _session("session-observation-b")
    repository.save_session(first_session)
    repository.save_session(second_session)
    frame = _frame("frame-session-a", first_session.session_id, BASE)
    repository.save_frame(frame)
    invalid = Observation(
        observation_id="observation-wrong-session",
        session_id=second_session.session_id,
        timestamp=BASE,
        frame_id=frame.frame_id,
        confidence=0.9,
        visual_quality=0.9,
    )

    with pytest.raises(IntegrityError):
        repository.save_observation(invalid)

    assert repository.get_observation(invalid.observation_id) is None


def test_observation_quality_constraints_and_rollback(repository) -> None:
    session = _session("session-observation-quality")
    repository.save_session(session)
    frame = _frame("frame-observation-quality", session.session_id, BASE)
    repository.save_frame(frame)
    invalid = _observation("observation-invalid-quality", frame, confidence=1.1)

    with pytest.raises(IntegrityError):
        repository.save_observation(invalid)

    assert repository.get_observation(invalid.observation_id) is None
    valid = _observation("observation-invalid-quality", frame, confidence=1.0)
    repository.save_observation(valid)
    assert repository.get_observation(valid.observation_id) == valid


def test_naive_observation_timestamp_is_rejected(repository) -> None:
    session = _session("session-observation-naive")
    repository.save_session(session)
    frame = _frame("frame-observation-naive", session.session_id, BASE)
    repository.save_frame(frame)
    naive = _observation(
        "observation-naive",
        frame,
        timestamp=datetime(2026, 8, 10, 18, 0),
    )

    with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
        repository.save_observation(naive)

    assert repository.get_observation(naive.observation_id) is None


def test_open_candle_evolves_closes_once_and_preserves_frame_history(repository, engine) -> None:
    session = _session("session-candle-lifecycle")
    repository.save_session(session)
    frame1 = _frame("frame-candle-1", session.session_id, BASE + timedelta(seconds=20))
    frame2 = _frame("frame-candle-2", session.session_id, BASE + timedelta(seconds=45))
    frame3 = _frame("frame-candle-3", session.session_id, BASE + timedelta(minutes=1, seconds=5))
    obs1 = _observation("obs-candle-1", frame1)
    obs2 = _observation("obs-candle-2", frame2)
    obs3 = _observation("obs-candle-3", frame3)
    for frame, observation in ((frame1, obs1), (frame2, obs2), (frame3, obs3)):
        _persist_observation(repository, frame, observation)

    first = _candle(session.session_id, high="103", low="99", close="101", is_closed=False)
    second = _candle(session.session_id, high="104", low="98", close="99", is_closed=False)
    closed = _candle(session.session_id, high="104", low="98", close="100", is_closed=True)

    repository.save_candle(first, observation_id=obs1.observation_id)
    repository.save_candle(second, observation_id=obs2.observation_id)
    repository.save_candle(closed, observation_id=obs3.observation_id)

    assert repository.get_candle(session.session_id, BASE) == closed
    assert repository.get_candles_for_frame(frame1.frame_id) == (first,)
    assert repository.get_candles_for_frame(frame2.frame_id) == (second,)
    assert repository.get_candles_for_frame(frame3.frame_id) == (closed,)

    with engine.connect() as connection:
        candle_count = connection.execute(select(func.count()).select_from(CandleRecord)).scalar_one()
        snapshot_count = connection.execute(
            select(func.count()).select_from(CandleSnapshotRecord)
        ).scalar_one()
    assert candle_count == 1
    assert snapshot_count == 3


def test_repeated_replay_is_idempotent_for_candle_identity_and_does_not_regress(repository, engine) -> None:
    session = _session("session-repeated-replay")
    repository.save_session(session)
    states = (
        _candle(session.session_id, high="103", low="99", close="101", is_closed=False),
        _candle(session.session_id, high="104", low="98", close="99", is_closed=False),
        _candle(session.session_id, high="104", low="98", close="100", is_closed=True),
    )
    timestamps = (
        BASE + timedelta(seconds=20),
        BASE + timedelta(seconds=45),
        BASE + timedelta(minutes=1, seconds=5),
    )

    for replay in (1, 2):
        for index, (state, timestamp) in enumerate(zip(states, timestamps, strict=True), start=1):
            frame = _frame(
                f"frame-replay-{replay}-{index}",
                session.session_id,
                timestamp,
            )
            observation = _observation(
                f"obs-replay-{replay}-{index}",
                frame,
                timestamp=timestamp,
            )
            _persist_observation(repository, frame, observation)
            repository.save_candle(state, observation_id=observation.observation_id)

    assert repository.get_candle(session.session_id, BASE) == states[-1]
    assert repository.get_candles_for_frame("frame-replay-2-1") == (states[0],)
    assert repository.get_candles_for_frame("frame-replay-2-2") == (states[1],)
    with engine.connect() as connection:
        candle_count = connection.execute(select(func.count()).select_from(CandleRecord)).scalar_one()
        snapshot_count = connection.execute(
            select(func.count()).select_from(CandleSnapshotRecord)
        ).scalar_one()
    assert candle_count == 1
    assert snapshot_count == 6


def test_same_logical_timestamp_with_different_candle_data_is_rejected(repository) -> None:
    session = _session("session-deterministic-history")
    repository.save_session(session)
    first_frame = _frame("frame-deterministic-1", session.session_id, BASE + timedelta(seconds=20))
    first_observation = _observation("obs-deterministic-1", first_frame)
    _persist_observation(repository, first_frame, first_observation)
    original = _candle(session.session_id, high="103", low="99", close="101", is_closed=False)
    repository.save_candle(original, observation_id=first_observation.observation_id)

    replay_frame = _frame("frame-deterministic-2", session.session_id, first_frame.captured_at)
    replay_observation = _observation("obs-deterministic-2", replay_frame)
    _persist_observation(repository, replay_frame, replay_observation)
    divergent = _candle(session.session_id, high="103", low="99", close="102", is_closed=False)

    with pytest.raises(CandleConflictError, match="same candle timestamp"):
        repository.save_candle(divergent, observation_id=replay_observation.observation_id)

    assert repository.get_candle(session.session_id, BASE) == original
    assert repository.get_candles_for_frame(replay_frame.frame_id) == ()


def test_closed_candle_cannot_be_rewritten_by_later_observation(repository) -> None:
    session = _session("session-closed-immutable")
    repository.save_session(session)
    close_frame = _frame("frame-close", session.session_id, BASE + timedelta(minutes=1, seconds=5))
    close_observation = _observation("obs-close", close_frame)
    _persist_observation(repository, close_frame, close_observation)
    closed = _candle(session.session_id, high="104", low="98", close="100", is_closed=True)
    repository.save_candle(closed, observation_id=close_observation.observation_id)

    later_frame = _frame("frame-later", session.session_id, BASE + timedelta(minutes=1, seconds=30))
    later_observation = _observation("obs-later", later_frame)
    _persist_observation(repository, later_frame, later_observation)
    conflicting = _candle(session.session_id, high="104", low="98", close="99", is_closed=True)

    with pytest.raises(CandleConflictError, match="closed candle history is immutable"):
        repository.save_candle(conflicting, observation_id=later_observation.observation_id)

    assert repository.get_candle(session.session_id, BASE) == closed
    assert repository.get_candles_for_frame(later_frame.frame_id) == ()


def test_open_candle_range_cannot_regress_on_later_observation(repository) -> None:
    session = _session("session-open-monotonic")
    repository.save_session(session)
    first_frame = _frame("frame-open-first", session.session_id, BASE + timedelta(seconds=20))
    first_observation = _observation("obs-open-first", first_frame)
    _persist_observation(repository, first_frame, first_observation)
    first = _candle(session.session_id, high="104", low="98", close="100", is_closed=False)
    repository.save_candle(first, observation_id=first_observation.observation_id)

    later_frame = _frame("frame-open-later", session.session_id, BASE + timedelta(seconds=40))
    later_observation = _observation("obs-open-later", later_frame)
    _persist_observation(repository, later_frame, later_observation)
    regressed = _candle(session.session_id, high="103", low="99", close="100", is_closed=False)

    with pytest.raises(CandleConflictError, match="high cannot decrease"):
        repository.save_candle(regressed, observation_id=later_observation.observation_id)

    assert repository.get_candle(session.session_id, BASE) == first


def test_candle_requires_existing_observation_and_same_session(repository) -> None:
    first_session = _session("session-candle-parent-a")
    second_session = _session("session-candle-parent-b")
    repository.save_session(first_session)
    repository.save_session(second_session)
    candle = _candle(first_session.session_id, high="103", low="99", close="101", is_closed=False)

    with pytest.raises(ValueError, match="does not exist"):
        repository.save_candle(candle, observation_id="missing-observation")

    frame = _frame("frame-other-session", second_session.session_id, BASE)
    observation = _observation("obs-other-session", frame)
    _persist_observation(repository, frame, observation)
    with pytest.raises(CandleConflictError, match="same session"):
        repository.save_candle(candle, observation_id=observation.observation_id)

    assert repository.get_candle(first_session.session_id, BASE) is None


def test_invalid_candle_constraints_roll_back(repository) -> None:
    session = _session("session-invalid-candle")
    repository.save_session(session)
    frame = _frame("frame-invalid-candle", session.session_id, BASE + timedelta(seconds=10))
    observation = _observation("obs-invalid-candle", frame)
    _persist_observation(repository, frame, observation)
    invalid = _candle(session.session_id, high="99", low="98", close="100", is_closed=False)

    with pytest.raises(IntegrityError):
        repository.save_candle(invalid, observation_id=observation.observation_id)

    assert repository.get_candle(session.session_id, BASE) is None
    assert repository.get_candles_for_frame(frame.frame_id) == ()


def test_naive_candle_timestamp_is_rejected(repository) -> None:
    session = _session("session-naive-candle")
    repository.save_session(session)
    frame = _frame("frame-naive-candle", session.session_id, BASE)
    observation = _observation("obs-naive-candle", frame)
    _persist_observation(repository, frame, observation)
    naive_open_time = datetime(2026, 8, 10, 18, 0)
    naive = Candle(
        source_id="vision",
        session_id=session.session_id,
        asset="TEST",
        timeframe="1m",
        open_time=naive_open_time,
        close_time=naive_open_time + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("103"),
        low=Decimal("99"),
        close=Decimal("101"),
        is_closed=False,
        vision_confidence=0.9,
    )

    with pytest.raises(ValueError, match="open_time must be timezone-aware"):
        repository.save_candle(naive, observation_id=observation.observation_id)

    assert repository.get_candle(session.session_id, BASE) is None
