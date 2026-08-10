from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from app.domain.models.reconstruction import PriceCandleObservation
from app.domain.models.vision import CandleDirection, VisualCandle


_MIN_ANCHORS = 2
_DEFAULT_MAX_SLOPE_DEVIATION_RATIO = Decimal("0.05")


class PriceScaleOrientation(StrEnum):
    PRICE_INCREASES_UP = "PRICE_INCREASES_UP"
    PRICE_INCREASES_DOWN = "PRICE_INCREASES_DOWN"


class PriceMappingError(ValueError):
    """Explicit failure raised when visual scale evidence cannot support a price."""


@dataclass(frozen=True, slots=True)
class PriceAnchor:
    """A price label read from the visible chart scale at a vertical pixel coordinate."""

    y: int
    price: Decimal
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise PriceMappingError("ANCHOR_CONFIDENCE_OUT_OF_RANGE")


class PriceMapper:
    """Calibrate and map vertical pixels to prices using visual scale anchors only."""

    def __init__(
        self,
        anchors: Iterable[PriceAnchor],
        *,
        max_slope_deviation_ratio: Decimal = _DEFAULT_MAX_SLOPE_DEVIATION_RATIO,
    ) -> None:
        if max_slope_deviation_ratio < 0:
            raise PriceMappingError("INVALID_SLOPE_DEVIATION_RATIO")

        ordered = tuple(sorted(anchors, key=lambda anchor: anchor.y))
        if not ordered:
            raise PriceMappingError("PRICE_SCALE_NOT_FOUND")
        if len(ordered) < _MIN_ANCHORS:
            raise PriceMappingError("INSUFFICIENT_PRICE_ANCHORS")

        self._validate_unique_y(ordered)
        orientation = self._detect_orientation(ordered)
        slopes = self._slopes(ordered)
        slope_deviation = self._max_relative_slope_deviation(slopes)
        if slope_deviation > max_slope_deviation_ratio:
            raise PriceMappingError("INCONSISTENT_PRICE_ANCHORS")

        self._anchors = ordered
        self._orientation = orientation
        self._min_y = ordered[0].y
        self._max_y = ordered[-1].y
        anchor_confidence = min(anchor.confidence for anchor in ordered)
        consistency = max(Decimal("0"), Decimal("1") - slope_deviation)
        self._calibration_confidence = float(Decimal(str(anchor_confidence)) * consistency)

    @property
    def anchors(self) -> tuple[PriceAnchor, ...]:
        return self._anchors

    @property
    def orientation(self) -> PriceScaleOrientation:
        return self._orientation

    @property
    def calibrated_y_range(self) -> tuple[int, int]:
        return self._min_y, self._max_y

    @property
    def calibration_confidence(self) -> float:
        return self._calibration_confidence

    def map_candle(
        self,
        candle: VisualCandle,
        *,
        visual_quality: float,
    ) -> PriceCandleObservation:
        high_y = candle.upper_wick.top_y if candle.upper_wick is not None else candle.body.y
        low_y = (
            candle.lower_wick.bottom_y
            if candle.lower_wick is not None
            else candle.body.bottom - 1
        )
        body_top_y = candle.body.y
        body_bottom_y = candle.body.bottom - 1

        if candle.direction is CandleDirection.UP:
            open_y, close_y = body_bottom_y, body_top_y
        else:
            open_y, close_y = body_top_y, body_bottom_y

        confidence = min(candle.confidence, self._calibration_confidence)
        return PriceCandleObservation(
            x=candle.x,
            open=self.price_for_y(open_y),
            high=self.price_for_y(high_y),
            low=self.price_for_y(low_y),
            close=self.price_for_y(close_y),
            direction=candle.direction,
            confidence=confidence,
            visual_quality=visual_quality,
        )

    def price_for_y(self, y: int) -> Decimal:
        if y < self._min_y or y > self._max_y:
            raise PriceMappingError("Y_OUTSIDE_CALIBRATED_RANGE")

        for anchor in self._anchors:
            if y == anchor.y:
                return anchor.price

        for left, right in zip(self._anchors, self._anchors[1:]):
            if left.y < y < right.y:
                offset = Decimal(y - left.y)
                span = Decimal(right.y - left.y)
                return left.price + (right.price - left.price) * offset / span

        raise PriceMappingError("Y_NOT_MAPPABLE")

    @staticmethod
    def _validate_unique_y(anchors: tuple[PriceAnchor, ...]) -> None:
        if len({anchor.y for anchor in anchors}) != len(anchors):
            raise PriceMappingError("DUPLICATE_PRICE_ANCHOR_Y")

    @staticmethod
    def _detect_orientation(anchors: tuple[PriceAnchor, ...]) -> PriceScaleOrientation:
        price_deltas = tuple(
            right.price - left.price
            for left, right in zip(anchors, anchors[1:])
        )
        if all(delta < 0 for delta in price_deltas):
            return PriceScaleOrientation.PRICE_INCREASES_UP
        if all(delta > 0 for delta in price_deltas):
            return PriceScaleOrientation.PRICE_INCREASES_DOWN
        raise PriceMappingError("NON_MONOTONIC_PRICE_ANCHORS")

    @staticmethod
    def _slopes(anchors: tuple[PriceAnchor, ...]) -> tuple[Decimal, ...]:
        return tuple(
            (right.price - left.price) / Decimal(right.y - left.y)
            for left, right in zip(anchors, anchors[1:])
        )

    @staticmethod
    def _max_relative_slope_deviation(slopes: tuple[Decimal, ...]) -> Decimal:
        if len(slopes) == 1:
            return Decimal("0")

        magnitudes = tuple(abs(slope) for slope in slopes)
        mean = sum(magnitudes, start=Decimal("0")) / Decimal(len(magnitudes))
        if mean == 0:
            raise PriceMappingError("INCONSISTENT_PRICE_ANCHORS")
        return max(abs(magnitude - mean) / mean for magnitude in magnitudes)
