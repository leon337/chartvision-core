from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MarketState(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class Analysis:
    analysis_id: str
    session_id: str
    timestamp: datetime
    market_state: MarketState
    confidence: float
    data_quality: float
    evidence: tuple[str, ...] = ()
