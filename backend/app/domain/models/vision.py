from dataclasses import dataclass
from enum import StrEnum


class VisionStatus(StrEnum):
    OK = "OK"
    CHART_NOT_FOUND = "CHART_NOT_FOUND"
    LOW_IMAGE_QUALITY = "LOW_IMAGE_QUALITY"
    PRICE_SCALE_NOT_FOUND = "PRICE_SCALE_NOT_FOUND"
    CANDLE_DETECTION_FAILED = "CANDLE_DETECTION_FAILED"
    TRACKING_LOST = "TRACKING_LOST"


class CandleDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"


@dataclass(frozen=True, slots=True)
class PixelRegion:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class VerticalWick:
    x: int
    top_y: int
    bottom_y: int


@dataclass(frozen=True, slots=True)
class VisualCandle:
    x: int
    body: PixelRegion
    upper_wick: VerticalWick | None
    lower_wick: VerticalWick | None
    direction: CandleDirection
    width: int
    confidence: float


@dataclass(frozen=True, slots=True)
class ChartDetection:
    status: VisionStatus
    chart_region: PixelRegion | None
    candle_region: PixelRegion | None
    price_scale_region: PixelRegion | None
    confidence: float
    visual_quality: float
    warnings: tuple[VisionStatus, ...] = ()


@dataclass(frozen=True, slots=True)
class CandleDetection:
    status: VisionStatus
    candles: tuple[VisualCandle, ...]
    confidence: float
    visual_quality: float


@dataclass(frozen=True, slots=True)
class VisionObservation:
    status: VisionStatus
    chart: ChartDetection
    candles: CandleDetection | None
    confidence: float
    visual_quality: float
