from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.interfaces.outcome_storage_provider import ExposureHistoryUnknownError
from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.outcome import (
    ExposureTrackingState,
    Outcome,
    OutcomeEvaluationPolicy,
    RealizedState,
)
from app.domain.models.session_exposure import SessionExposureState
from app.domain.services.outcome_metrics_service import OutcomeMetricsService

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self) -> None:
        self.policy = OutcomeEvaluationPolicy(
            policy_id="policy-1",
            session_id="session-1",
            horizon_closed_candles=2,
            realized_return_threshold=Decimal("0.01"),
            bound_at=T0,
        )
        self.exposure = SessionExposureState(
            session_id="session-1",
            tracking_state=ExposureTrackingState.TRACKED,
            session_origin_time=T0,
            session_exposure_watermark=T0,
        )
        self.analysis = Analysis(
            analysis_id="analysis-1",
            session_id="session-1",
            timestamp=T0 + timedelta(minutes=1),
            market_state=MarketState.UP,
            confidence=0.8,
            data_quality=0.8,
            evidence=("STATE_RULE=TEST",),
        )
        self.outcome = Outcome(
            analysis_id="analysis-1",
            policy_id="policy-1",
            evaluation_timestamp=T0 + timedelta(minutes=3),
            reference_candle_open_time=T0,
            reference_candle_close_time=T0 + timedelta(minutes=1),
            reference_close=Decimal("100"),
            final_candle_open_time=T0 + timedelta(minutes=2),
            final_candle_close_time=T0 + timedelta(minutes=3),
            final_close=Decimal("102"),
            horizon_closed_candles=2,
            realized_return_threshold=Decimal("0.01"),
            realized_return=Decimal("0.02"),
            realized_state=RealizedState.UP,
            evidence=("OUTCOME_RULE=TEST",),
        )

    def get_outcome_evaluation_policy(self, policy_id: str):
        return self.policy if policy_id == self.policy.policy_id else None

    def get_session_exposure_state(self, session_id: str):
        return self.exposure if session_id == "session-1" else None

    def list_outcomes(self, policy_id: str):
        return (self.outcome,) if policy_id == self.policy.policy_id else ()

    def get_analysis(self, analysis_id: str):
        return self.analysis if analysis_id == self.analysis.analysis_id else None


def test_metrics_service_builds_report_from_persisted_pairs() -> None:
    storage = FakeStorage()
    report = OutcomeMetricsService(storage).report("policy-1")

    assert report.policy_id == "policy-1"
    assert report.total_evaluated == 1
    assert report.accuracy == Decimal("1")
    assert report.coverage == Decimal("1")


def test_metrics_service_rejects_legacy_provenance() -> None:
    storage = FakeStorage()
    storage.exposure = SessionExposureState(
        session_id="session-1",
        tracking_state=ExposureTrackingState.LEGACY_UNKNOWN,
        session_origin_time=None,
        session_exposure_watermark=None,
    )

    with pytest.raises(ExposureHistoryUnknownError):
        OutcomeMetricsService(storage).report("policy-1")
