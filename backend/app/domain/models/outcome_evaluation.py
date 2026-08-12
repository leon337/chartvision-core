from dataclasses import dataclass
from enum import StrEnum

from app.domain.models.outcome import Outcome


class OutcomeAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    PENDING_HORIZON = "PENDING_HORIZON"
    EXPOSURE_HISTORY_UNKNOWN = "EXPOSURE_HISTORY_UNKNOWN"
    UNAVAILABLE_POLICY = "UNAVAILABLE_POLICY"
    POLICY_BOUND_TOO_LATE = "POLICY_BOUND_TOO_LATE"
    UNAVAILABLE_REFERENCE = "UNAVAILABLE_REFERENCE"
    UNAVAILABLE_END_OF_DATASET = "UNAVAILABLE_END_OF_DATASET"


@dataclass(frozen=True, slots=True)
class OutcomeEvaluationResult:
    status: OutcomeAvailability
    outcome: Outcome | None = None

    def __post_init__(self) -> None:
        if self.status is OutcomeAvailability.AVAILABLE and self.outcome is None:
            raise ValueError("AVAILABLE result requires an Outcome")
        if self.status is not OutcomeAvailability.AVAILABLE and self.outcome is not None:
            raise ValueError("unavailable result cannot carry an Outcome")
