from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.models.candle import Candle


@dataclass(frozen=True, slots=True)
class GroundTruthWindow:
    reference_candle: Candle | None
    future_closed_candles: tuple[Candle, ...]
    source_exhausted: bool


class GroundTruthProvider(Protocol):
    def get_evaluation_window(
        self,
        session_id: str,
        analysis_timestamp: datetime,
        evaluation_as_of: datetime,
        horizon_closed_candles: int,
    ) -> GroundTruthWindow: ...
