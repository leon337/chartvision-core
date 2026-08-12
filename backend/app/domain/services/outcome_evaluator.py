from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from app.domain.models.analysis import Analysis
from app.domain.models.candle import Candle
from app.domain.models.outcome import Outcome, OutcomeEvaluationPolicy, RealizedState


class OutcomeEvaluationError(ValueError):
    """Raised when OutcomeEvaluator receives an invalid evaluation boundary."""


class OutcomeEvaluator:
    @staticmethod
    def evaluate(
        *,
        analysis: Analysis,
        policy: OutcomeEvaluationPolicy,
        reference_candle: Candle,
        final_candle: Candle,
    ) -> Outcome:
        OutcomeEvaluator._validate_inputs(
            analysis=analysis,
            policy=policy,
            reference_candle=reference_candle,
            final_candle=final_candle,
        )

        with localcontext() as context:
            context.prec = 28
            context.rounding = ROUND_HALF_EVEN
            realized_return = (final_candle.close - reference_candle.close) / reference_candle.close

        threshold = policy.realized_return_threshold
        if realized_return > threshold:
            realized_state = RealizedState.UP
        elif realized_return < -threshold:
            realized_state = RealizedState.DOWN
        else:
            realized_state = RealizedState.SIDEWAYS

        evidence = (
            "OUTCOME_RULE=REALIZED_RETURN_THRESHOLD",
            f"ANALYSIS_ID={analysis.analysis_id}",
            f"POLICY_ID={policy.policy_id}",
            f"REFERENCE_CANDLE_OPEN_TIME={reference_candle.open_time.isoformat()}",
            f"REFERENCE_CANDLE_CLOSE_TIME={reference_candle.close_time.isoformat()}",
            f"REFERENCE_CLOSE={reference_candle.close}",
            f"FINAL_CANDLE_OPEN_TIME={final_candle.open_time.isoformat()}",
            f"FINAL_CANDLE_CLOSE_TIME={final_candle.close_time.isoformat()}",
            f"FINAL_CLOSE={final_candle.close}",
            f"HORIZON_CLOSED_CANDLES={policy.horizon_closed_candles}",
            f"REALIZED_RETURN_THRESHOLD={policy.realized_return_threshold}",
            f"REALIZED_RETURN={realized_return}",
            f"REALIZED_STATE={realized_state.value}",
        )

        return Outcome(
            analysis_id=analysis.analysis_id,
            policy_id=policy.policy_id,
            evaluation_timestamp=final_candle.close_time,
            reference_candle_open_time=reference_candle.open_time,
            reference_candle_close_time=reference_candle.close_time,
            reference_close=reference_candle.close,
            final_candle_open_time=final_candle.open_time,
            final_candle_close_time=final_candle.close_time,
            final_close=final_candle.close,
            horizon_closed_candles=policy.horizon_closed_candles,
            realized_return_threshold=policy.realized_return_threshold,
            realized_return=realized_return,
            realized_state=realized_state,
            evidence=evidence,
        )

    @staticmethod
    def _validate_inputs(
        *,
        analysis: Analysis,
        policy: OutcomeEvaluationPolicy,
        reference_candle: Candle,
        final_candle: Candle,
    ) -> None:
        OutcomeEvaluator._require_aware(analysis.timestamp, "analysis.timestamp")
        for candle_name, candle in (("reference_candle", reference_candle), ("final_candle", final_candle)):
            OutcomeEvaluator._require_aware(candle.open_time, f"{candle_name}.open_time")
            OutcomeEvaluator._require_aware(candle.close_time, f"{candle_name}.close_time")
            if not candle.is_closed:
                raise OutcomeEvaluationError(f"{candle_name} must be closed")

        if policy.session_id != analysis.session_id:
            raise OutcomeEvaluationError("policy and analysis must belong to the same session")
        if policy.bound_at > analysis.timestamp:
            raise OutcomeEvaluationError("policy bound_at is later than analysis timestamp")
        if reference_candle.session_id != analysis.session_id or final_candle.session_id != analysis.session_id:
            raise OutcomeEvaluationError("ground truth candles must belong to the analysis session")
        if (
            reference_candle.source_id,
            reference_candle.asset,
            reference_candle.timeframe,
        ) != (final_candle.source_id, final_candle.asset, final_candle.timeframe):
            raise OutcomeEvaluationError("ground truth candles must share the same market context")
        if reference_candle.close_time > analysis.timestamp:
            raise OutcomeEvaluationError("reference candle must close at or before analysis timestamp")
        if final_candle.close_time <= analysis.timestamp:
            raise OutcomeEvaluationError("final candle must close after analysis timestamp")
        if reference_candle.close == Decimal("0"):
            raise OutcomeEvaluationError("reference close must be non-zero")

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise OutcomeEvaluationError(f"{field_name} must be timezone-aware")
