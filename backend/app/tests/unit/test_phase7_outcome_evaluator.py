from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models.analysis import Analysis, MarketState
from app.domain.models.candle import Candle
from app.domain.models.outcome import OutcomeEvaluationPolicy, RealizedState
from app.domain.services.outcome_evaluator import OutcomeEvaluationError, OutcomeEvaluator

T = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def _analysis(*, timestamp: datetime = T) -> Analysis:
    return Analysis(
        analysis_id="analysis-1",
        session_id="session-1",
        timestamp=timestamp,
        market_state=MarketState.UP,
        confidence=0.9,
        data_quality=0.9,
        evidence=("STATE_RULE=RISING_STRUCTURE",),
    )


def _policy(
    *,
    threshold: Decimal = Decimal("0.01"),
    bound_at: datetime = T,
    session_id: str = "session-1",
) -> OutcomeEvaluationPolicy:
    return OutcomeEvaluationPolicy(
        policy_id="policy-1",
        session_id=session_id,
        horizon_closed_candles=3,
        realized_return_threshold=threshold,
        bound_at=bound_at,
    )


def _candle(
    *,
    close: Decimal,
    close_time: datetime,
    session_id: str = "session-1",
    is_closed: bool = True,
    source_id: str = "replay",
    asset: str = "SAMPLE",
    timeframe: str = "1m",
) -> Candle:
    return Candle(
        source_id=source_id,
        session_id=session_id,
        asset=asset,
        timeframe=timeframe,
        open_time=close_time - timedelta(minutes=1),
        close_time=close_time,
        open=close,
        high=close,
        low=close,
        close=close,
        is_closed=is_closed,
    )


def _evaluate(*, final_close: Decimal, threshold: Decimal = Decimal("0.01")):
    return OutcomeEvaluator.evaluate(
        analysis=_analysis(),
        policy=_policy(threshold=threshold),
        reference_candle=_candle(close=Decimal("100"), close_time=T),
        final_candle=_candle(close=final_close, close_time=T + timedelta(minutes=3)),
    )


def test_return_above_threshold_is_up() -> None:
    outcome = _evaluate(final_close=Decimal("102"))
    assert outcome.realized_return == Decimal("0.02")
    assert outcome.realized_state is RealizedState.UP


def test_return_below_negative_threshold_is_down() -> None:
    outcome = _evaluate(final_close=Decimal("98"))
    assert outcome.realized_return == Decimal("-0.02")
    assert outcome.realized_state is RealizedState.DOWN


def test_return_inside_threshold_is_sideways() -> None:
    outcome = _evaluate(final_close=Decimal("100.5"))
    assert outcome.realized_return == Decimal("0.005")
    assert outcome.realized_state is RealizedState.SIDEWAYS


def test_positive_threshold_equality_is_sideways() -> None:
    outcome = _evaluate(final_close=Decimal("101"))
    assert outcome.realized_return == Decimal("0.01")
    assert outcome.realized_state is RealizedState.SIDEWAYS


def test_negative_threshold_equality_is_sideways() -> None:
    outcome = _evaluate(final_close=Decimal("99"))
    assert outcome.realized_return == Decimal("-0.01")
    assert outcome.realized_state is RealizedState.SIDEWAYS


def test_zero_threshold_only_zero_return_is_sideways() -> None:
    assert _evaluate(final_close=Decimal("100"), threshold=Decimal("0")).realized_state is RealizedState.SIDEWAYS
    assert _evaluate(final_close=Decimal("100.01"), threshold=Decimal("0")).realized_state is RealizedState.UP
    assert _evaluate(final_close=Decimal("99.99"), threshold=Decimal("0")).realized_state is RealizedState.DOWN


def test_policy_bound_equal_analysis_timestamp_is_allowed() -> None:
    outcome = _evaluate(final_close=Decimal("102"))
    assert outcome.policy_id == "policy-1"


def test_policy_bound_after_analysis_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(bound_at=T + timedelta(seconds=1)),
            reference_candle=_candle(close=Decimal("100"), close_time=T),
            final_candle=_candle(close=Decimal("102"), close_time=T + timedelta(minutes=3)),
        )


def test_policy_from_other_session_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(session_id="session-2"),
            reference_candle=_candle(close=Decimal("100"), close_time=T),
            final_candle=_candle(close=Decimal("102"), close_time=T + timedelta(minutes=3)),
        )


def test_ground_truth_from_other_session_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(),
            reference_candle=_candle(close=Decimal("100"), close_time=T),
            final_candle=_candle(
                close=Decimal("102"),
                close_time=T + timedelta(minutes=3),
                session_id="session-2",
            ),
        )


def test_open_ground_truth_candle_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(),
            reference_candle=_candle(close=Decimal("100"), close_time=T),
            final_candle=_candle(
                close=Decimal("102"),
                close_time=T + timedelta(minutes=3),
                is_closed=False,
            ),
        )


def test_reference_after_analysis_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(),
            reference_candle=_candle(close=Decimal("100"), close_time=T + timedelta(seconds=1)),
            final_candle=_candle(close=Decimal("102"), close_time=T + timedelta(minutes=3)),
        )


def test_final_at_or_before_analysis_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(),
            reference_candle=_candle(close=Decimal("100"), close_time=T - timedelta(minutes=1)),
            final_candle=_candle(close=Decimal("102"), close_time=T),
        )


def test_zero_reference_close_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(),
            policy=_policy(),
            reference_candle=_candle(close=Decimal("0"), close_time=T),
            final_candle=_candle(close=Decimal("102"), close_time=T + timedelta(minutes=3)),
        )


def test_naive_analysis_timestamp_is_rejected() -> None:
    with pytest.raises(OutcomeEvaluationError):
        OutcomeEvaluator.evaluate(
            analysis=_analysis(timestamp=datetime(2026, 8, 12, 10, 0)),
            policy=_policy(),
            reference_candle=_candle(close=Decimal("100"), close_time=T),
            final_candle=_candle(close=Decimal("102"), close_time=T + timedelta(minutes=3)),
        )


def test_same_input_produces_same_outcome() -> None:
    first = _evaluate(final_close=Decimal("102"))
    second = _evaluate(final_close=Decimal("102"))
    assert first == second


def test_evidence_order_is_deterministic() -> None:
    outcome = _evaluate(final_close=Decimal("102"))
    assert tuple(token.split("=", 1)[0] for token in outcome.evidence) == (
        "OUTCOME_RULE",
        "ANALYSIS_ID",
        "POLICY_ID",
        "REFERENCE_CANDLE_OPEN_TIME",
        "REFERENCE_CANDLE_CLOSE_TIME",
        "REFERENCE_CLOSE",
        "FINAL_CANDLE_OPEN_TIME",
        "FINAL_CANDLE_CLOSE_TIME",
        "FINAL_CLOSE",
        "HORIZON_CLOSED_CANDLES",
        "REALIZED_RETURN_THRESHOLD",
        "REALIZED_RETURN",
        "REALIZED_STATE",
    )


def test_evaluation_does_not_mutate_analysis() -> None:
    analysis = _analysis()
    before = analysis
    OutcomeEvaluator.evaluate(
        analysis=analysis,
        policy=_policy(),
        reference_candle=_candle(close=Decimal("100"), close_time=T),
        final_candle=_candle(close=Decimal("102"), close_time=T + timedelta(minutes=3)),
    )
    assert analysis == before
    with pytest.raises(FrozenInstanceError):
        analysis.confidence = 0.1  # type: ignore[misc]
