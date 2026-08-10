from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    source_id: str
    session_id: str
    asset: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    is_closed: bool
    vision_confidence: float | None = None
    source_confidence: float | None = None
