from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.models.outcome import (
    ExposureTrackingState,
    Outcome,
    OutcomeConfig,
    OutcomeEvaluationPolicy,
    RealizedState,
)


def _policy(**overrides: object) -> OutcomeEvaluationPolicy:
    values: dict[str, object] = {
        "policy_id": "policy-1",
        "session_id": "session-1",
        "horizon_closed_candles": 3,
        "realized_return_threshold": Decimal("0.01"),
        "bound_at": datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return OutcomeEvaluationPolicy(**values)  # type: ignore[arg-type]


def _outcome(**overrides: object) -> Outcome:
    values: dict[str, object] = {
        "analysis_id": "analysis-1",
        "policy_id": "policy-1",
        "evaluation_timestamp": datetime(2026, 8, 12, 10, 4, tzinfo=timezone.utc),
        "reference_candle_open_time": datetime(2026, 8, 12, 9, 59, tzinfo=timezone.utc),
        "reference_candle_close_time": datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
        "reference_close": Decimal("100"),
        "final_candle_open_time": datetime(2026, 8, 12, 10, 3, tzinfo=timezone.utc),
        "final_candle_close_time": datetime(2026, 8, 12, 10, 4, tzinfo=timezone.utc),
        "final_close": Decimal("102"),
        "horizon_closed_candles": 3,
        "realized_return_threshold": Decimal("0.01"),
        "realized_return": Decimal("0.02"),
        "realized_state": RealizedState.UP,
        "evidence": ("OUTCOME_RULE=RETURN_THRESHOLD",),
    }
    values.update(overrides)
    return Outcome(**values)  # type: ignore[arg-type]


def test_realized_state_excludes_uncertain() -> None:
    assert tuple(RealizedState) == (
        RealizedState.UP,
        RealizedState.DOWN,
        RealizedState.SIDEWAYS,
    )


def test_exposure_tracking_state_is_explicit() -> None:
    assert tuple(ExposureTrackingState) == (
        ExposureTrackingState.TRACKED,
        ExposureTrackingState.LEGACY_UNKNOWN,
    )


def test_outcome_config_accepts_valid_target() -> None:
    config = OutcomeConfig(3, Decimal("0.01"))
    assert config.horizon_closed_candles == 3
    assert config.realized_return_threshold == Decimal("0.01")


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5])
def test_outcome_config_rejects_invalid_horizon(horizon: object) -> None:
    with pytest.raises(ValueError):
        OutcomeConfig(horizon, Decimal("0.01"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "threshold",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_outcome_config_rejects_invalid_threshold(threshold: Decimal) -> None:
    with pytest.raises(ValueError):
        OutcomeConfig(3, threshold)


def test_outcome_config_requires_decimal_threshold() -> None:
    with pytest.raises(ValueError):
        OutcomeConfig(3, 0.01)  # type: ignore[arg-type]


def test_policy_exposes_exact_precommitted_config() -> None:
    policy = _policy()
    assert policy.config == OutcomeConfig(3, Decimal("0.01"))


def test_policy_requires_timezone_aware_bound_at() -> None:
    with pytest.raises(ValueError):
        _policy(bound_at=datetime(2026, 8, 12, 10, 0))


def test_policy_is_immutable() -> None:
    policy = _policy()
    with pytest.raises(FrozenInstanceError):
        policy.bound_at = datetime(2026, 8, 12, 11, 0, tzinfo=timezone.utc)  # type: ignore[misc]


def test_outcome_is_immutable() -> None:
    outcome = _outcome()
    with pytest.raises(FrozenInstanceError):
        outcome.final_close = Decimal("103")  # type: ignore[misc]


def test_outcome_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValueError):
        _outcome(final_candle_close_time=datetime(2026, 8, 12, 10, 4))


def test_outcome_rejects_zero_reference_close() -> None:
    with pytest.raises(ValueError):
        _outcome(reference_close=Decimal("0"))


def test_outcome_requires_final_close_time_after_reference() -> None:
    reference_close_time = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        _outcome(
            final_candle_close_time=reference_close_time,
            evaluation_timestamp=reference_close_time,
        )


def test_outcome_evaluation_timestamp_equals_final_close_time() -> None:
    with pytest.raises(ValueError):
        _outcome(evaluation_timestamp=datetime(2026, 8, 12, 10, 5, tzinfo=timezone.utc))


def test_valid_outcome_preserves_policy_identity_and_decimal_values() -> None:
    outcome = _outcome()
    assert outcome.policy_id == "policy-1"
    assert outcome.horizon_closed_candles == 3
    assert outcome.realized_return_threshold == Decimal("0.01")
    assert outcome.realized_return == Decimal("0.02")
    assert outcome.realized_state is RealizedState.UP
