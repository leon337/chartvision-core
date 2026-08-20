from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Event, Thread

import pytest

from app.domain.interfaces.outcome_storage_provider import OutcomeStorageProvider
from app.domain.models.candle import Candle
from app.domain.models.outcome import OutcomeConfig, OutcomeEvaluationPolicy
from app.infrastructure.replay.exposure_tracked_replay import ExposureTrackedReplay
from app.infrastructure.replay.replay_session_factory import ReplaySessionFactory
from app.infrastructure.replay.replay_source import ReplaySource

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def _candles(session_id: str = "session-1") -> tuple[Candle, ...]:
    result = []
    for index in range(6):
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
            )
        )
    return tuple(result)


class FakeLifecycleStorage:
    def __init__(self) -> None:
        self.initialized = []
        self.watermark = None
        self.exposure_entered = Event()
        self.release_exposure = Event()
        self.policy_entered = Event()
        self.block_advanced_exposure = False

    def _initialize_tracked_session(self, session, *, session_origin_time):
        self.initialized.append((session, session_origin_time))
        if self.watermark is None:
            self.watermark = session_origin_time

    def record_session_exposure(self, session_id: str, exposed_at: datetime):
        if self.block_advanced_exposure and exposed_at > T0:
            self.exposure_entered.set()
            assert self.release_exposure.wait(timeout=2)
        if self.watermark is None or exposed_at > self.watermark:
            self.watermark = exposed_at
        return None

    def register_outcome_evaluation_policy(self, *, session_id: str, policy_id: str, config: OutcomeConfig):
        self.policy_entered.set()
        assert self.watermark is not None
        return OutcomeEvaluationPolicy(
            policy_id=policy_id,
            session_id=session_id,
            horizon_closed_candles=config.horizon_closed_candles,
            realized_return_threshold=config.realized_return_threshold,
            bound_at=self.watermark,
        )


def test_public_outcome_storage_contract_does_not_allow_caller_supplied_tracked_origin() -> None:
    assert not hasattr(OutcomeStorageProvider, "save_tracked_session")


def test_factory_derives_tracked_origin_from_replay_metadata() -> None:
    storage = FakeLifecycleStorage()

    tracked = ReplaySessionFactory(storage).from_candles(_candles())

    assert tracked.session_id == "session-1"
    assert tracked.snapshot.current_time is None
    assert len(storage.initialized) == 1
    session, origin = storage.initialized[0]
    assert session.session_id == "session-1"
    assert session.source_id == "replay"
    assert session.asset == "SAMPLE"
    assert session.timeframe == "1m"
    assert session.started_at == T0
    assert origin == T0
    assert storage.watermark == T0


def test_direct_tracked_adapter_construction_is_rejected() -> None:
    storage = FakeLifecycleStorage()

    with pytest.raises(RuntimeError, match="ReplaySessionFactory"):
        ExposureTrackedReplay(
            session_id="session-1",
            replay_source=ReplaySource(_candles()),
            storage=storage,
        )


def test_policy_registration_cannot_observe_pre_exposure_watermark_across_wrappers() -> None:
    storage = FakeLifecycleStorage()
    first = ReplaySessionFactory(storage).from_candles(_candles())
    second = ReplaySessionFactory(storage).from_candles(_candles())
    first.start()
    storage.block_advanced_exposure = True

    advance_thread = Thread(target=lambda: first.advance(seconds=180))
    advance_thread.start()
    assert storage.exposure_entered.wait(timeout=2)

    policies = []
    policy_thread = Thread(
        target=lambda: policies.append(
            second.register_policy(
                policy_id="policy-1",
                config=OutcomeConfig(3, Decimal("0.01")),
            )
        )
    )
    policy_thread.start()

    assert not storage.policy_entered.wait(timeout=0.1)
    storage.release_exposure.set()
    advance_thread.join(timeout=2)
    policy_thread.join(timeout=2)

    assert not advance_thread.is_alive()
    assert not policy_thread.is_alive()
    assert len(policies) == 1
    assert policies[0].bound_at == T0 + timedelta(minutes=3)


def test_reset_never_rewinds_lifecycle_watermark() -> None:
    storage = FakeLifecycleStorage()
    tracked = ReplaySessionFactory(storage).from_candles(_candles())
    tracked.start()
    tracked.advance(seconds=180)

    tracked.reset()
    tracked.start()
    tracked.advance(seconds=60)

    assert storage.watermark == T0 + timedelta(minutes=3)
