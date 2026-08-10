from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.models.vision import CandleDirection, VisionStatus


@dataclass(frozen=True, slots=True)
class PriceCandleObservation:
    x: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    direction: CandleDirection
    confidence: float
    visual_quality: float


@dataclass(frozen=True, slots=True)
class TrackedCandle:
    track_id: str
    session_id: str
    open_time: datetime
    close_time: datetime
    observation: PriceCandleObservation
    is_closed: bool
    first_seen_at: datetime
    last_seen_at: datetime
    confidence: float


@dataclass(frozen=True, slots=True)
class TrackingResult:
    status: VisionStatus
    candles: tuple[TrackedCandle, ...]
    horizontal_shift_px: int
    new_track_ids: tuple[str, ...] = ()
    updated_track_ids: tuple[str, ...] = ()
    closed_track_ids: tuple[str, ...] = ()
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReconstructionResult:
    status: VisionStatus
    candles: tuple[Candle, ...]
    tracking: TrackingResult | None
    calibration_confidence: float
    failure_reason: str | None = None
