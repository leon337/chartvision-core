from dataclasses import dataclass
from decimal import Decimal

from app.domain.models.analysis import Analysis
from app.domain.models.outcome import Outcome


@dataclass(frozen=True, slots=True)
class EvaluatedAnalysis:
    analysis: Analysis
    outcome: Outcome


@dataclass(frozen=True, slots=True)
class PerClassMetric:
    up: Decimal | None
    down: Decimal | None
    sideways: Decimal | None


@dataclass(frozen=True, slots=True)
class ConfidenceBinReport:
    label: str
    count: int
    mean_confidence: Decimal | None
    observed_accuracy: Decimal | None
    absolute_gap: Decimal | None


@dataclass(frozen=True, slots=True)
class ConfidenceCalibrationReport:
    total_non_uncertain: int
    bins: tuple[ConfidenceBinReport, ...]
    weighted_alignment_gap: Decimal | None


@dataclass(frozen=True, slots=True)
class OutcomeMetricsReport:
    policy_id: str
    horizon_closed_candles: int
    realized_return_threshold: Decimal
    total_evaluated: int
    confusion_matrix: tuple[tuple[int, int, int, int], ...]
    accuracy: Decimal | None
    precision_by_class: PerClassMetric
    recall_by_class: PerClassMetric
    coverage: Decimal | None
    uncertain_count: int
    uncertain_frequency: Decimal | None
    confidence_calibration: ConfidenceCalibrationReport
