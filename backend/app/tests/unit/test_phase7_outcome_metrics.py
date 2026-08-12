from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.outcome import Outcome, OutcomeEvaluationPolicy, RealizedState
from app.domain.models.outcome_metrics import EvaluatedAnalysis
from app.domain.services.outcome_metrics_engine import MixedOutcomePolicyError, OutcomeMetricsEngine

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def _policy(policy_id: str = "policy-1") -> OutcomeEvaluationPolicy:
    return OutcomeEvaluationPolicy(
        policy_id=policy_id,
        session_id="session-1",
        horizon_closed_candles=3,
        realized_return_threshold=Decimal("0.01"),
        bound_at=T0,
    )


def _pair(
    identity: str,
    predicted: MarketState,
    realized: RealizedState,
    confidence: float,
    *,
    policy_id: str = "policy-1",
) -> EvaluatedAnalysis:
    analysis = Analysis(
        analysis_id=identity,
        session_id="session-1",
        timestamp=T0 + timedelta(minutes=1),
        market_state=predicted,
        confidence=confidence,
        data_quality=confidence,
        evidence=("STATE_RULE=TEST",),
    )
    outcome = Outcome(
        analysis_id=identity,
        policy_id=policy_id,
        evaluation_timestamp=T0 + timedelta(minutes=4),
        reference_candle_open_time=T0,
        reference_candle_close_time=T0 + timedelta(minutes=1),
        reference_close=Decimal("100"),
        final_candle_open_time=T0 + timedelta(minutes=3),
        final_candle_close_time=T0 + timedelta(minutes=4),
        final_close=Decimal("102"),
        horizon_closed_candles=3,
        realized_return_threshold=Decimal("0.01"),
        realized_return=Decimal("0.02"),
        realized_state=realized,
        evidence=("OUTCOME_RULE=TEST",),
    )
    return EvaluatedAnalysis(analysis, outcome)


def test_confusion_matrix_metrics_and_uncertain_semantics() -> None:
    pairs = (
        _pair("a1", MarketState.UP, RealizedState.UP, 0.9),
        _pair("a2", MarketState.UNCERTAIN, RealizedState.UP, 0.0),
        _pair("a3", MarketState.UP, RealizedState.DOWN, 0.6),
        _pair("a4", MarketState.DOWN, RealizedState.DOWN, 0.7),
        _pair("a5", MarketState.SIDEWAYS, RealizedState.SIDEWAYS, 0.5),
        _pair("a6", MarketState.UNCERTAIN, RealizedState.SIDEWAYS, 0.0),
    )

    report = OutcomeMetricsEngine.calculate(_policy(), pairs)

    assert report.confusion_matrix == (
        (1, 0, 0, 1),
        (1, 1, 0, 0),
        (0, 0, 1, 1),
    )
    assert sum(sum(row) for row in report.confusion_matrix) == 6
    assert report.accuracy == Decimal("0.5")
    assert report.precision_by_class.up == Decimal("0.5")
    assert report.precision_by_class.down == Decimal("1")
    assert report.precision_by_class.sideways == Decimal("1")
    assert report.recall_by_class.up == Decimal("0.5")
    assert report.recall_by_class.down == Decimal("0.5")
    assert report.recall_by_class.sideways == Decimal("0.5")
    assert report.uncertain_count == 2
    assert report.coverage == Decimal(2) / Decimal(3)
    assert report.uncertain_frequency == Decimal(1) / Decimal(3)


def test_confidence_calibration_excludes_uncertain_and_is_deterministic() -> None:
    pairs = (
        _pair("a1", MarketState.UP, RealizedState.UP, 0.9),
        _pair("a2", MarketState.UNCERTAIN, RealizedState.UP, 0.0),
        _pair("a3", MarketState.UP, RealizedState.DOWN, 0.6),
        _pair("a4", MarketState.DOWN, RealizedState.DOWN, 0.7),
        _pair("a5", MarketState.SIDEWAYS, RealizedState.SIDEWAYS, 0.5),
    )

    calibration = OutcomeMetricsEngine.calculate(_policy(), pairs).confidence_calibration

    assert calibration.total_non_uncertain == 4
    assert tuple(bin_report.count for bin_report in calibration.bins) == (0, 0, 1, 2, 1)
    assert calibration.bins[2].mean_confidence == Decimal("0.5")
    assert calibration.bins[2].observed_accuracy == Decimal("1")
    assert calibration.bins[3].mean_confidence == Decimal("0.65")
    assert calibration.bins[3].observed_accuracy == Decimal("0.5")
    assert calibration.bins[4].mean_confidence == Decimal("0.9")
    assert calibration.weighted_alignment_gap == Decimal("0.225")


def test_canonical_bin_boundaries_use_decimal_string_normalization() -> None:
    confidences = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    pairs = tuple(
        _pair(f"b{index}", MarketState.UP, RealizedState.UP, confidence)
        for index, confidence in enumerate(confidences)
    )

    calibration = OutcomeMetricsEngine.calculate(_policy(), pairs).confidence_calibration

    assert tuple(bin_report.count for bin_report in calibration.bins) == (1, 1, 1, 1, 2)
    assert calibration.bins[-1].mean_confidence == Decimal("0.9")


def test_empty_cohort_uses_none_for_undefined_ratios() -> None:
    report = OutcomeMetricsEngine.calculate(_policy(), ())

    assert report.total_evaluated == 0
    assert report.confusion_matrix == ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    assert report.accuracy is None
    assert report.coverage is None
    assert report.uncertain_frequency is None
    assert report.uncertain_count == 0
    assert report.precision_by_class.up is None
    assert report.recall_by_class.up is None
    assert report.confidence_calibration.weighted_alignment_gap is None
    assert all(bin_report.count == 0 for bin_report in report.confidence_calibration.bins)


def test_all_uncertain_has_no_confidence_calibration_aggregate() -> None:
    pairs = (
        _pair("u1", MarketState.UNCERTAIN, RealizedState.UP, 0.0),
        _pair("u2", MarketState.UNCERTAIN, RealizedState.DOWN, 0.0),
    )
    report = OutcomeMetricsEngine.calculate(_policy(), pairs)

    assert report.coverage == Decimal("0")
    assert report.uncertain_frequency == Decimal("1")
    assert report.confidence_calibration.total_non_uncertain == 0
    assert report.confidence_calibration.weighted_alignment_gap is None


def test_mixed_policy_fails_before_aggregation() -> None:
    pairs = (
        _pair("a1", MarketState.UP, RealizedState.UP, 0.9),
        _pair("a2", MarketState.DOWN, RealizedState.DOWN, 0.8, policy_id="policy-2"),
    )
    with pytest.raises(MixedOutcomePolicyError):
        OutcomeMetricsEngine.calculate(_policy(), pairs)
