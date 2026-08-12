from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.interfaces.ground_truth_provider import GroundTruthWindow
from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.candle import Candle
from app.domain.models.outcome import (
    ExposureTrackingState,
    Outcome,
    OutcomeEvaluationPolicy,
    RealizedState,
)
from app.domain.models.outcome_evaluation import OutcomeAvailability
from app.domain.models.session_exposure import SessionExposureState
from app.domain.services.outcome_evaluation_service import OutcomeEvaluationService

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def _analysis(*, timestamp: datetime = T0 + timedelta(minutes=1)) -> Analysis:
    return Analysis(
        analysis_id="analysis-1",
        session_id="session-1",
        timestamp=timestamp,
        market_state=MarketState.UP,
        confidence=0.9,
        data_quality=0.9,
        evidence=("STATE_RULE=RISING_STRUCTURE",),
    )


def _policy(*, bound_at: datetime = T0, horizon: int = 2) -> OutcomeEvaluationPolicy:
    return OutcomeEvaluationPolicy(
        policy_id="policy-1",
        session_id="session-1",
        horizon_closed_candles=horizon,
        realized_return_threshold=Decimal("0.01"),
        bound_at=bound_at,
    )


def _candle(index: int, close: str) -> Candle:
    open_time = T0 + timedelta(minutes=index)
    price = Decimal(close)
    return Candle(
        source_id="replay",
        session_id="session-1",
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


class FakeStorage:
    def __init__(self) -> None:
        self.analysis = _analysis()
        self.exposure = SessionExposureState(
            session_id="session-1",
            tracking_state=ExposureTrackingState.TRACKED,
            session_origin_time=T0,
            session_exposure_watermark=T0,
        )
        self.policy: OutcomeEvaluationPolicy | None = _policy()
        self.outcome: Outcome | None = None
        self.saved_outcomes = 0

    def get_analysis(self, analysis_id: str):
        return self.analysis if analysis_id == self.analysis.analysis_id else None

    def get_session_exposure_state(self, session_id: str):
        return self.exposure if session_id == "session-1" else None

    def get_outcome_evaluation_policy_for_session(self, session_id: str):
        return self.policy if session_id == "session-1" else None

    def get_outcome(self, analysis_id: str):
        return self.outcome if analysis_id == self.analysis.analysis_id else None

    def save_outcome(self, outcome: Outcome) -> None:
        self.saved_outcomes += 1
        self.outcome = outcome


class FakeGroundTruthProvider:
    def __init__(self, window: GroundTruthWindow) -> None:
        self.window = window
        self.calls = 0

    def get_evaluation_window(self, *args, **kwargs) -> GroundTruthWindow:
        self.calls += 1
        return self.window


def _service(storage: FakeStorage, window: GroundTruthWindow):
    provider = FakeGroundTruthProvider(window)
    return OutcomeEvaluationService(storage=storage, ground_truth_provider=provider), provider


def test_legacy_unknown_returns_explicit_status_without_ground_truth() -> None:
    storage = FakeStorage()
    storage.exposure = SessionExposureState(
        session_id="session-1",
        tracking_state=ExposureTrackingState.LEGACY_UNKNOWN,
        session_origin_time=None,
        session_exposure_watermark=None,
    )
    service, provider = _service(storage, GroundTruthWindow(None, (), False))

    result = service.evaluate("analysis-1", T0 + timedelta(minutes=5))

    assert result.status is OutcomeAvailability.EXPOSURE_HISTORY_UNKNOWN
    assert provider.calls == 0
    assert storage.saved_outcomes == 0


def test_missing_policy_returns_explicit_status() -> None:
    storage = FakeStorage()
    storage.policy = None
    service, provider = _service(storage, GroundTruthWindow(None, (), False))

    result = service.evaluate("analysis-1", T0 + timedelta(minutes=5))

    assert result.status is OutcomeAvailability.UNAVAILABLE_POLICY
    assert provider.calls == 0


def test_policy_bound_too_late_returns_explicit_status() -> None:
    storage = FakeStorage()
    storage.policy = _policy(bound_at=storage.analysis.timestamp + timedelta(seconds=1))
    service, provider = _service(storage, GroundTruthWindow(None, (), False))

    result = service.evaluate("analysis-1", T0 + timedelta(minutes=5))

    assert result.status is OutcomeAvailability.POLICY_BOUND_TOO_LATE
    assert provider.calls == 0


def test_missing_reference_returns_unavailable_reference() -> None:
    storage = FakeStorage()
    service, _ = _service(storage, GroundTruthWindow(None, (), False))
    result = service.evaluate("analysis-1", T0 + timedelta(minutes=3))
    assert result.status is OutcomeAvailability.UNAVAILABLE_REFERENCE
    assert storage.saved_outcomes == 0


def test_incomplete_horizon_is_pending_when_source_not_exhausted() -> None:
    storage = FakeStorage()
    reference = _candle(0, "100")
    service, _ = _service(storage, GroundTruthWindow(reference, (_candle(1, "101"),), False))
    result = service.evaluate("analysis-1", T0 + timedelta(minutes=2))
    assert result.status is OutcomeAvailability.PENDING_HORIZON
    assert storage.saved_outcomes == 0


def test_incomplete_horizon_at_terminal_dataset_is_unavailable() -> None:
    storage = FakeStorage()
    reference = _candle(0, "100")
    service, _ = _service(storage, GroundTruthWindow(reference, (_candle(1, "101"),), True))
    result = service.evaluate("analysis-1", T0 + timedelta(minutes=2))
    assert result.status is OutcomeAvailability.UNAVAILABLE_END_OF_DATASET
    assert storage.saved_outcomes == 0


def test_available_horizon_persists_exactly_one_outcome() -> None:
    storage = FakeStorage()
    reference = _candle(0, "100")
    future = (_candle(1, "101"), _candle(2, "102"))
    service, provider = _service(storage, GroundTruthWindow(reference, future, False))

    result = service.evaluate("analysis-1", T0 + timedelta(minutes=3))

    assert result.status is OutcomeAvailability.AVAILABLE
    assert result.outcome is not None
    assert result.outcome.realized_state is RealizedState.UP
    assert storage.saved_outcomes == 1
    assert provider.calls == 1


def test_existing_outcome_is_returned_only_when_authorized_by_evaluation_cut() -> None:
    storage = FakeStorage()
    reference = _candle(0, "100")
    future = (_candle(1, "101"), _candle(2, "102"))
    service, provider = _service(storage, GroundTruthWindow(reference, future[:1], False))

    complete = OutcomeEvaluationService(
        storage=storage,
        ground_truth_provider=FakeGroundTruthProvider(GroundTruthWindow(reference, future, False)),
    ).evaluate("analysis-1", T0 + timedelta(minutes=3)).outcome
    assert complete is not None

    result = service.evaluate("analysis-1", T0 + timedelta(minutes=2))

    assert result.status is OutcomeAvailability.PENDING_HORIZON
    assert provider.calls == 1


def test_evaluation_as_of_before_analysis_fails() -> None:
    storage = FakeStorage()
    service, _ = _service(storage, GroundTruthWindow(None, (), False))
    with pytest.raises(ValueError, match="cannot precede"):
        service.evaluate("analysis-1", T0)


def test_available_evaluation_does_not_mutate_analysis_or_policy() -> None:
    storage = FakeStorage()
    analysis_before = storage.analysis
    policy_before = storage.policy
    reference = _candle(0, "100")
    future = (_candle(1, "101"), _candle(2, "102"))
    service, _ = _service(storage, GroundTruthWindow(reference, future, False))

    service.evaluate("analysis-1", T0 + timedelta(minutes=3))

    assert storage.analysis == analysis_before
    assert storage.policy == policy_before
