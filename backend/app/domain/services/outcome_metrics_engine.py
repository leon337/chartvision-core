from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from math import isfinite

from app.domain.models.analysis import MarketState
from app.domain.models.outcome import OutcomeEvaluationPolicy, RealizedState
from app.domain.models.outcome_metrics import (
    ConfidenceBinReport,
    ConfidenceCalibrationReport,
    EvaluatedAnalysis,
    OutcomeMetricsReport,
    PerClassMetric,
)


class MixedOutcomePolicyError(ValueError):
    """Raised before aggregation when a metric cohort is not policy-homogeneous."""


class OutcomeMetricsEngine:
    _realized_order = (RealizedState.UP, RealizedState.DOWN, RealizedState.SIDEWAYS)
    _predicted_order = (
        MarketState.UP,
        MarketState.DOWN,
        MarketState.SIDEWAYS,
        MarketState.UNCERTAIN,
    )
    _bins = (
        (Decimal("0.0"), Decimal("0.2"), False, "[0.0,0.2)"),
        (Decimal("0.2"), Decimal("0.4"), False, "[0.2,0.4)"),
        (Decimal("0.4"), Decimal("0.6"), False, "[0.4,0.6)"),
        (Decimal("0.6"), Decimal("0.8"), False, "[0.6,0.8)"),
        (Decimal("0.8"), Decimal("1.0"), True, "[0.8,1.0]"),
    )

    @classmethod
    def calculate(
        cls,
        policy: OutcomeEvaluationPolicy,
        pairs: Sequence[EvaluatedAnalysis],
    ) -> OutcomeMetricsReport:
        cls._validate_cohort(policy, pairs)
        matrix = [[0 for _ in cls._predicted_order] for _ in cls._realized_order]
        for pair in pairs:
            row = cls._realized_order.index(pair.outcome.realized_state)
            column = cls._predicted_order.index(pair.analysis.market_state)
            matrix[row][column] += 1

        total = len(pairs)
        correct = sum(matrix[index][index] for index in range(3))
        accuracy = cls._ratio(correct, total)

        precisions: list[Decimal | None] = []
        recalls: list[Decimal | None] = []
        for index in range(3):
            precision_denominator = sum(matrix[row][index] for row in range(3))
            recall_denominator = sum(matrix[index])
            precisions.append(cls._ratio(matrix[index][index], precision_denominator))
            recalls.append(cls._ratio(matrix[index][index], recall_denominator))

        uncertain_count = sum(matrix[row][3] for row in range(3))
        coverage = cls._ratio(total - uncertain_count, total)
        uncertain_frequency = cls._ratio(uncertain_count, total)
        calibration = cls._calibration(pairs)

        return OutcomeMetricsReport(
            policy_id=policy.policy_id,
            horizon_closed_candles=policy.horizon_closed_candles,
            realized_return_threshold=policy.realized_return_threshold,
            total_evaluated=total,
            confusion_matrix=tuple(tuple(row) for row in matrix),
            accuracy=accuracy,
            precision_by_class=PerClassMetric(*precisions),
            recall_by_class=PerClassMetric(*recalls),
            coverage=coverage,
            uncertain_count=uncertain_count,
            uncertain_frequency=uncertain_frequency,
            confidence_calibration=calibration,
        )

    @classmethod
    def _validate_cohort(
        cls,
        policy: OutcomeEvaluationPolicy,
        pairs: Sequence[EvaluatedAnalysis],
    ) -> None:
        for pair in pairs:
            if pair.outcome.analysis_id != pair.analysis.analysis_id:
                raise ValueError("Outcome must reference its paired Analysis")
            if pair.outcome.policy_id != policy.policy_id:
                raise MixedOutcomePolicyError("metric cohort contains a different policy_id")
            if pair.outcome.horizon_closed_candles != policy.horizon_closed_candles:
                raise MixedOutcomePolicyError("metric cohort contains a different horizon")
            if pair.outcome.realized_return_threshold != policy.realized_return_threshold:
                raise MixedOutcomePolicyError("metric cohort contains a different threshold")

    @classmethod
    def _calibration(
        cls,
        pairs: Sequence[EvaluatedAnalysis],
    ) -> ConfidenceCalibrationReport:
        eligible: list[tuple[Decimal, bool]] = []
        for pair in pairs:
            if pair.analysis.market_state is MarketState.UNCERTAIN:
                continue
            confidence = pair.analysis.confidence
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise ValueError("Analysis.confidence must be a finite number in [0,1]")
            if not isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("Analysis.confidence must be in [0,1]")
            confidence_decimal = Decimal(str(confidence))
            correct = pair.analysis.market_state.value == pair.outcome.realized_state.value
            eligible.append((confidence_decimal, correct))

        bin_reports: list[ConfidenceBinReport] = []
        total_non_uncertain = len(eligible)
        weighted_gap = Decimal("0")
        for lower, upper, include_upper, label in cls._bins:
            members = [
                item
                for item in eligible
                if item[0] >= lower and (item[0] <= upper if include_upper else item[0] < upper)
            ]
            count = len(members)
            if count == 0:
                bin_reports.append(ConfidenceBinReport(label, 0, None, None, None))
                continue
            with localcontext() as context:
                context.prec = 28
                context.rounding = ROUND_HALF_EVEN
                mean_confidence = sum((item[0] for item in members), Decimal("0")) / count
                observed_accuracy = Decimal(sum(1 for _, correct in members if correct)) / count
                absolute_gap = abs(mean_confidence - observed_accuracy)
                if total_non_uncertain:
                    weighted_gap += (Decimal(count) / total_non_uncertain) * absolute_gap
            bin_reports.append(
                ConfidenceBinReport(
                    label=label,
                    count=count,
                    mean_confidence=mean_confidence,
                    observed_accuracy=observed_accuracy,
                    absolute_gap=absolute_gap,
                )
            )

        return ConfidenceCalibrationReport(
            total_non_uncertain=total_non_uncertain,
            bins=tuple(bin_reports),
            weighted_alignment_gap=weighted_gap if total_non_uncertain else None,
        )

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> Decimal | None:
        if denominator == 0:
            return None
        with localcontext() as context:
            context.prec = 28
            context.rounding = ROUND_HALF_EVEN
            return Decimal(numerator) / Decimal(denominator)
