from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ReconstructionMetrics:
    open_error: Decimal | None
    high_error: Decimal | None
    low_error: Decimal | None
    close_error: Decimal | None
    candle_detection_rate: float
    direction_accuracy: float
    duplicate_rate: float
    missing_candle_rate: float
    matched_candles: int
    ground_truth_candles: int
    reconstructed_candles: int
