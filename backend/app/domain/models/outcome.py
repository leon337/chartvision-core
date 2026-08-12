from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum


class RealizedState(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"


class ExposureTrackingState(StrEnum):
    TRACKED = "TRACKED"
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN"


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_target(horizon_closed_candles: int, realized_return_threshold: Decimal) -> None:
    if isinstance(horizon_closed_candles, bool) or not isinstance(horizon_closed_candles, int):
        raise ValueError("horizon_closed_candles must be an integer")
    if horizon_closed_candles < 1:
        raise ValueError("horizon_closed_candles must be at least 1")
    if not isinstance(realized_return_threshold, Decimal):
        raise ValueError("realized_return_threshold must be a Decimal")
    if not realized_return_threshold.is_finite() or realized_return_threshold < Decimal("0"):
        raise ValueError("realized_return_threshold must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class OutcomeConfig:
    horizon_closed_candles: int
    realized_return_threshold: Decimal

    def __post_init__(self) -> None:
        _validate_target(self.horizon_closed_candles, self.realized_return_threshold)


@dataclass(frozen=True, slots=True)
class OutcomeEvaluationPolicy:
    policy_id: str
    session_id: str
    horizon_closed_candles: int
    realized_return_threshold: Decimal
    bound_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.policy_id, "policy_id")
        _require_non_empty(self.session_id, "session_id")
        _validate_target(self.horizon_closed_candles, self.realized_return_threshold)
        _require_aware(self.bound_at, "bound_at")

    @property
    def config(self) -> OutcomeConfig:
        return OutcomeConfig(
            horizon_closed_candles=self.horizon_closed_candles,
            realized_return_threshold=self.realized_return_threshold,
        )


@dataclass(frozen=True, slots=True)
class Outcome:
    analysis_id: str
    policy_id: str
    evaluation_timestamp: datetime
    reference_candle_open_time: datetime
    reference_candle_close_time: datetime
    reference_close: Decimal
    final_candle_open_time: datetime
    final_candle_close_time: datetime
    final_close: Decimal
    horizon_closed_candles: int
    realized_return_threshold: Decimal
    realized_return: Decimal
    realized_state: RealizedState
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_empty(self.analysis_id, "analysis_id")
        _require_non_empty(self.policy_id, "policy_id")
        _validate_target(self.horizon_closed_candles, self.realized_return_threshold)
        for field_name in (
            "evaluation_timestamp",
            "reference_candle_open_time",
            "reference_candle_close_time",
            "final_candle_open_time",
            "final_candle_close_time",
        ):
            _require_aware(getattr(self, field_name), field_name)
        if self.reference_candle_close_time <= self.reference_candle_open_time:
            raise ValueError("reference candle close_time must be after open_time")
        if self.final_candle_close_time <= self.final_candle_open_time:
            raise ValueError("final candle close_time must be after open_time")
        if not all(
            isinstance(value, Decimal)
            for value in (self.reference_close, self.final_close, self.realized_return)
        ):
            raise ValueError("outcome prices and realized_return must be Decimal values")
        if not all(
            value.is_finite()
            for value in (self.reference_close, self.final_close, self.realized_return)
        ):
            raise ValueError("outcome prices and realized_return must be finite")
        if self.reference_close == Decimal("0"):
            raise ValueError("reference_close must be non-zero")
        if self.final_candle_close_time <= self.reference_candle_close_time:
            raise ValueError("final_candle_close_time must be after reference_candle_close_time")
        if self.evaluation_timestamp != self.final_candle_close_time:
            raise ValueError("evaluation_timestamp must equal final_candle_close_time")
        if not isinstance(self.realized_state, RealizedState):
            raise ValueError("realized_state must be a RealizedState")
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(token, str) for token in self.evidence
        ):
            raise ValueError("evidence must be a tuple of strings")

        with localcontext() as context:
            context.prec = 28
            context.rounding = ROUND_HALF_EVEN
            expected_return = (self.final_close - self.reference_close) / self.reference_close
        if self.realized_return != expected_return:
            raise ValueError("realized_return is inconsistent with reference/final close")
        threshold = self.realized_return_threshold
        expected_state = (
            RealizedState.UP
            if expected_return > threshold
            else RealizedState.DOWN
            if expected_return < -threshold
            else RealizedState.SIDEWAYS
        )
        if self.realized_state is not expected_state:
            raise ValueError("realized_state is inconsistent with realized_return threshold rule")
