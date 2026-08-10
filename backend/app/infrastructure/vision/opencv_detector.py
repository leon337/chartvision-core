import cv2
import numpy as np

from app.domain.models.vision import (
    ChartDetection,
    PixelRegion,
    VisionObservation,
    VisionStatus,
)
from app.infrastructure.vision.candle_detector import CandleDetector


_CHART_BACKGROUND_BGR = np.array((42, 23, 15), dtype=np.uint8)
_BORDER_BGR = np.array((85, 65, 51), dtype=np.uint8)
_COLOR_TOLERANCE = 8
_MIN_CHART_AREA_RATIO = 0.15
_MIN_IMAGE_SIDE = 64
_MIN_VISUAL_QUALITY = 0.08


def _decode_image(image: bytes) -> np.ndarray | None:
    if not image:
        return None
    array = np.frombuffer(image, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def _color_mask(image: np.ndarray, color: np.ndarray, tolerance: int = _COLOR_TOLERANCE) -> np.ndarray:
    lower = np.clip(color.astype(np.int16) - tolerance, 0, 255).astype(np.uint8)
    upper = np.clip(color.astype(np.int16) + tolerance, 0, 255).astype(np.uint8)
    return cv2.inRange(image, lower, upper)


def _visual_quality(image: np.ndarray) -> float:
    height, width = image.shape[:2]
    if min(height, width) < _MIN_IMAGE_SIDE:
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contrast_score = min(1.0, float(gray.std()) / 48.0)
    edges = cv2.Canny(gray, 40, 120)
    edge_score = min(1.0, float(np.count_nonzero(edges)) / edges.size * 8.0)
    return min(1.0, 0.55 * contrast_score + 0.45 * edge_score)


class ChartDetector:
    def detect(self, image: bytes) -> ChartDetection:
        decoded = _decode_image(image)
        if decoded is None:
            return self._failure(VisionStatus.LOW_IMAGE_QUALITY, 0.0)

        quality = _visual_quality(decoded)
        if quality < _MIN_VISUAL_QUALITY:
            return self._failure(VisionStatus.LOW_IMAGE_QUALITY, quality)

        background_mask = _color_mask(decoded, _CHART_BACKGROUND_BGR)
        kernel = np.ones((3, 3), dtype=np.uint8)
        connected = cv2.morphologyEx(background_mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._failure(VisionStatus.CHART_NOT_FOUND, quality)

        image_height, image_width = decoded.shape[:2]
        image_area = image_width * image_height
        candidates: list[tuple[int, PixelRegion]] = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            if width < 120 or height < 80 or area / image_area < _MIN_CHART_AREA_RATIO:
                continue
            candidates.append((area, PixelRegion(x=x, y=y, width=width, height=height)))
        if not candidates:
            return self._failure(VisionStatus.CHART_NOT_FOUND, quality)

        _, chart_region = max(candidates, key=lambda item: item[0])
        chart_roi = decoded[
            chart_region.y : chart_region.bottom,
            chart_region.x : chart_region.right,
        ]
        chart_background = _color_mask(chart_roi, _CHART_BACKGROUND_BGR)
        background_ratio = float(np.count_nonzero(chart_background)) / chart_background.size
        confidence = min(1.0, 0.55 + 0.45 * background_ratio)

        price_scale_x = self._find_price_scale_x(chart_roi)
        warnings: tuple[VisionStatus, ...] = ()
        if price_scale_x is None:
            warnings = (VisionStatus.PRICE_SCALE_NOT_FOUND,)
            candle_width = chart_region.width
            price_scale_region = None
        else:
            candle_width = max(1, price_scale_x)
            price_scale_region = PixelRegion(
                x=chart_region.x + price_scale_x + 1,
                y=chart_region.y,
                width=max(1, chart_region.width - price_scale_x - 1),
                height=chart_region.height,
            )

        time_scale_y = self._find_time_scale_y(chart_roi, candle_width)
        candle_height = time_scale_y if time_scale_y is not None else chart_region.height
        candle_region = PixelRegion(
            x=chart_region.x,
            y=chart_region.y,
            width=candle_width,
            height=max(1, candle_height),
        )

        return ChartDetection(
            status=VisionStatus.OK,
            chart_region=chart_region,
            candle_region=candle_region,
            price_scale_region=price_scale_region,
            confidence=confidence,
            visual_quality=quality,
            warnings=warnings,
        )

    @staticmethod
    def _find_price_scale_x(chart_roi: np.ndarray) -> int | None:
        height, width = chart_roi.shape[:2]
        border_mask = _color_mask(chart_roi, _BORDER_BGR)
        counts = np.count_nonzero(border_mask, axis=0)
        start = max(0, int(width * 0.50))
        stop = max(start + 1, int(width * 0.97))
        search = counts[start:stop]
        if search.size == 0:
            return None
        relative_x = int(np.argmax(search))
        x = start + relative_x
        if int(counts[x]) < max(12, int(height * 0.20)):
            return None
        return x

    @staticmethod
    def _find_time_scale_y(chart_roi: np.ndarray, candle_width: int) -> int | None:
        height = chart_roi.shape[0]
        border_mask = _color_mask(chart_roi[:, :candle_width], _BORDER_BGR)
        counts = np.count_nonzero(border_mask, axis=1)
        start = max(0, int(height * 0.55))
        stop = max(start + 1, int(height * 0.97))
        search = counts[start:stop]
        if search.size == 0:
            return None
        relative_y = int(np.argmax(search))
        y = start + relative_y
        if int(counts[y]) < max(12, int(candle_width * 0.20)):
            return None
        return y

    @staticmethod
    def _failure(status: VisionStatus, quality: float) -> ChartDetection:
        return ChartDetection(
            status=status,
            chart_region=None,
            candle_region=None,
            price_scale_region=None,
            confidence=0.0,
            visual_quality=quality,
        )


class OpenCVVisionProvider:
    def __init__(
        self,
        chart_detector: ChartDetector | None = None,
        candle_detector: CandleDetector | None = None,
    ) -> None:
        self._chart_detector = chart_detector or ChartDetector()
        self._candle_detector = candle_detector or CandleDetector()

    def observe(self, image: bytes) -> VisionObservation:
        chart = self._chart_detector.detect(image)
        if chart.status is not VisionStatus.OK or chart.candle_region is None:
            return VisionObservation(
                status=chart.status,
                chart=chart,
                candles=None,
                confidence=chart.confidence,
                visual_quality=chart.visual_quality,
            )

        candles = self._candle_detector.detect(image, chart.candle_region)
        if candles.status is not VisionStatus.OK:
            return VisionObservation(
                status=candles.status,
                chart=chart,
                candles=candles,
                confidence=min(chart.confidence, candles.confidence),
                visual_quality=min(chart.visual_quality, candles.visual_quality),
            )

        return VisionObservation(
            status=VisionStatus.OK,
            chart=chart,
            candles=candles,
            confidence=min(chart.confidence, candles.confidence),
            visual_quality=min(chart.visual_quality, candles.visual_quality),
        )
