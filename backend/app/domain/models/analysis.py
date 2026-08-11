from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from math import isfinite


class MarketState(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    trend_pairs: int
    lateralization_window_candles: int
    lateralization_max_range_ratio: Decimal
    minimum_data_quality: float

    def __post_init__(self) -> None:
        if self.trend_pairs < 1:
            raise ValueError("trend_pairs must be at least 1")
        if self.lateralization_window_candles < 3:
            raise ValueError("lateralization_window_candles must be at least 3")
        if (
            not self.lateralization_max_range_ratio.is_finite()
            or self.lateralization_max_range_ratio < Decimal("0")
        ):
            raise ValueError("lateralization_max_range_ratio must be finite and non-negative")
        if not isfinite(self.minimum_data_quality) or not (
            0.0 <= self.minimum_data_quality <= 1.0
        ):
            raise ValueError("minimum_data_quality must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class AnalysisDecision:
    market_state: MarketState
    confidence: float
    data_quality: float | None
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Analysis:
    analysis_id: str
    session_id: str
    timestamp: datetime
    market_state: MarketState
    confidence: float
    data_quality: float | None
    evidence: tuple[str, ...] = ()
