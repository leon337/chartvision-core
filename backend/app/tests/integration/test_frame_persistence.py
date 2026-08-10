import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.domain.interfaces.storage_provider import FrameConflictError
from app.domain.models.frame import Frame
from app.domain.models.session import Session
from app.infrastructure.db.models import FrameRecord, SessionRecord
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
        connection.execute(delete(FrameRecord))
        connection.execute(delete(SessionRecord))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return PostgresStorageRepository(session_factory=factory)


def _session(session_id: str = "session-frame") -> Session:
    return Session(
        session_id=session_id,
        source_id="replay-source",
        asset="BTCUSD",
        timeframe="1m",
        started_at=datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc),
    )


def _frame(
    frame_id: str = "frame-001",
    session_id: str = "session-frame",
    *,
    image_hash: str = "abc123",
    storage_reference: str | None = "frames/frame-001.png",
) -> Frame:
    return Frame(
        frame_id=frame_id,
        session_id=session_id,
        captured_at=datetime(2026, 8, 10, 15, 0, 5, tzinfo=timezone(timedelta(hours=-3))),
        image_hash=image_hash,
        width=1280,
        height=720,
        changed_since_previous=True,
        storage_reference=storage_reference,
    )


def test_migration_created_frames_table_with_session_foreign_key(engine) -> None:
    inspector = inspect(engine)

    assert "frames" in inspector.get_table_names()
    foreign_keys = inspector.get_foreign_keys("frames")
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["session_id"]
    assert foreign_keys[0]["referred_table"] == "sessions"
    assert foreign_keys[0]["referred_columns"] == ["session_id"]


def test_round_trip_frame_preserves_all_fields_and_timezone(repository) -> None:
    parent = _session()
    original = _frame()
    repository.save_session(parent)

    repository.save_frame(original)
    loaded = repository.get_frame(original.frame_id)

    assert loaded is not None
    assert loaded == original
    assert loaded.captured_at.tzinfo is not None
    assert loaded.captured_at.utcoffset() == timedelta(0)
    assert loaded.storage_reference == "frames/frame-001.png"


def test_round_trip_frame_allows_missing_storage_reference(repository) -> None:
    parent = _session("session-no-storage")
    original = _frame(
        frame_id="frame-no-storage",
        session_id=parent.session_id,
        storage_reference=None,
    )
    repository.save_session(parent)

    repository.save_frame(original)

    assert repository.get_frame(original.frame_id) == original
    assert repository.get_frame(original.frame_id).storage_reference is None


def test_saving_identical_frame_is_idempotent(repository, engine) -> None:
    parent = _session("session-idempotent-frame")
    original = _frame(
        frame_id="frame-idempotent",
        session_id=parent.session_id,
    )
    repository.save_session(parent)

    repository.save_frame(original)
    repository.save_frame(original)

    with engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(FrameRecord)).scalar_one()
    assert count == 1


def test_conflicting_payload_for_same_frame_id_fails_and_preserves_history(repository) -> None:
    parent = _session("session-frame-conflict")
    original = _frame(
        frame_id="frame-conflict",
        session_id=parent.session_id,
    )
    repository.save_session(parent)
    repository.save_frame(original)
    conflicting = Frame(
        frame_id=original.frame_id,
        session_id=original.session_id,
        captured_at=original.captured_at,
        image_hash="different-hash",
        width=original.width,
        height=original.height,
        changed_since_previous=original.changed_since_previous,
        storage_reference=original.storage_reference,
    )

    with pytest.raises(FrameConflictError):
        repository.save_frame(conflicting)

    assert repository.get_frame(original.frame_id) == original


def test_same_image_hash_is_valid_for_distinct_frame_identities(repository, engine) -> None:
    parent = _session("session-repeated-pixels")
    repository.save_session(parent)
    first = _frame(
        frame_id="frame-repeat-1",
        session_id=parent.session_id,
        image_hash="same-pixels",
    )
    second = Frame(
        frame_id="frame-repeat-2",
        session_id=parent.session_id,
        captured_at=first.captured_at + timedelta(seconds=5),
        image_hash=first.image_hash,
        width=first.width,
        height=first.height,
        changed_since_previous=False,
        storage_reference="frames/frame-repeat-2.png",
    )

    repository.save_frame(first)
    repository.save_frame(second)

    with engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(FrameRecord)).scalar_one()
    assert count == 2
    assert repository.get_frame(first.frame_id) == first
    assert repository.get_frame(second.frame_id) == second


def test_missing_parent_session_rolls_back_and_foreign_key_is_enforced(repository) -> None:
    original = _frame(
        frame_id="frame-orphan",
        session_id="missing-session",
    )

    with pytest.raises(IntegrityError):
        repository.save_frame(original)

    assert repository.get_frame(original.frame_id) is None
    repository.save_session(_session(original.session_id))
    repository.save_frame(original)
    assert repository.get_frame(original.frame_id) == original


def test_invalid_dimensions_roll_back_transaction(repository) -> None:
    parent = _session("session-invalid-frame")
    repository.save_session(parent)
    invalid = Frame(
        frame_id="frame-invalid-size",
        session_id=parent.session_id,
        captured_at=datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc),
        image_hash="abc123",
        width=0,
        height=720,
        changed_since_previous=False,
    )

    with pytest.raises(IntegrityError):
        repository.save_frame(invalid)

    assert repository.get_frame(invalid.frame_id) is None
    valid = Frame(
        frame_id=invalid.frame_id,
        session_id=invalid.session_id,
        captured_at=invalid.captured_at,
        image_hash=invalid.image_hash,
        width=1280,
        height=invalid.height,
        changed_since_previous=invalid.changed_since_previous,
    )
    repository.save_frame(valid)
    assert repository.get_frame(valid.frame_id) == valid


def test_naive_captured_at_is_rejected_explicitly(repository) -> None:
    parent = _session("session-naive-frame")
    repository.save_session(parent)
    naive = Frame(
        frame_id="frame-naive",
        session_id=parent.session_id,
        captured_at=datetime(2026, 8, 10, 18, 0),
        image_hash="abc123",
        width=1280,
        height=720,
        changed_since_previous=False,
    )

    with pytest.raises(ValueError, match="captured_at must be timezone-aware"):
        repository.save_frame(naive)

    assert repository.get_frame(naive.frame_id) is None
