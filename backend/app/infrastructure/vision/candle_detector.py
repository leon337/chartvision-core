import cv2
import numpy as np

from app.domain.models.vision import (
    CandleDetection,
    CandleDirection,
    PixelRegion,
    VerticalWick,
    VisualCandle,
    VisionStatus,
)


_UP_BGR = np.array((94, 197, 34), dtype=np.uint8)
_DOWN_BGR = np.array((68, 68, 239), dtype=np.uint8)
_COLOR_TOLERANCE = 12
_MIN_VISUAL_QUALITY = 0.02


def _decode_image(image: bytes) -> np.ndarray | None:
    if not image:
        return None
    array = np.frombuffer(image, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def _color_mask(image: np.ndarray, color: np.ndarray) -> np.ndarray:
    lower = np.clip(color.astype(np.int16) - _COLOR_TOLERANCE, 0, 255).astype(np.uint8)
    upper = np.clip(color.astype(np.int16) + _COLOR_TOLERANCE, 0, 255).astype(np.uint8)
    return cv2.inRange(image, lower, upper)


def _visual_quality(image: np.ndarray) -> float:
    if min(image.shape[:2]) < 32:
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contrast_score = min(1.0, float(gray.std()) / 48.0)
    edges = cv2.Canny(gray, 40, 120)
    edge_score = min(1.0, float(np.count_nonzero(edges)) / edges.size * 8.0)
    return min(1.0, 0.55 * contrast_score + 0.45 * edge_score)


class CandleDetector:
    def detect(self, image: bytes, region: PixelRegion) -> CandleDetection:
        decoded = _decode_image(image)
        if decoded is None or not self._region_is_valid(decoded, region):
            return CandleDetection(
                status=VisionStatus.CANDLE_DETECTION_FAILED,
                candles=(),
                confidence=0.0,
                visual_quality=0.0,
            )

        roi = decoded[region.y : region.bottom, region.x : region.right]
        quality = _visual_quality(roi)
        if quality < _MIN_VISUAL_QUALITY:
            return CandleDetection(
                status=VisionStatus.LOW_IMAGE_QUALITY,
                candles=(),
                confidence=0.0,
                visual_quality=quality,
            )

        candles = [
            *self._detect_color(roi, region, _UP_BGR, CandleDirection.UP),
            *self._detect_color(roi, region, _DOWN_BGR, CandleDirection.DOWN),
        ]
        candles.sort(key=lambda candle: candle.x)
        if not candles:
            return CandleDetection(
                status=VisionStatus.CANDLE_DETECTION_FAILED,
                candles=(),
                confidence=0.0,
                visual_quality=quality,
            )

        confidence = sum(candle.confidence for candle in candles) / len(candles)
        return CandleDetection(
            status=VisionStatus.OK,
            candles=tuple(candles),
            confidence=confidence,
            visual_quality=quality,
        )

    @staticmethod
    def _region_is_valid(image: np.ndarray, region: PixelRegion) -> bool:
        height, width = image.shape[:2]
        return (
            region.x >= 0
            and region.y >= 0
            and region.width > 0
            and region.height > 0
            and region.right <= width
            and region.bottom <= height
        )

    def _detect_color(
        self,
        roi: np.ndarray,
        region: PixelRegion,
        color: np.ndarray,
        direction: CandleDirection,
    ) -> list[VisualCandle]:
        mask = _color_mask(roi, color)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        candles: list[VisualCandle] = []
        for label in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[label])
            if width < 3 or height < 5 or area < 8:
                continue
            component = labels[y : y + height, x : x + width] == label
            row_counts = np.count_nonzero(component, axis=1)
            body_threshold = max(2, int(np.ceil(width * 0.55)))
            body_rows = np.flatnonzero(row_counts >= body_threshold)
            if body_rows.size == 0:
                continue

            body_top = int(body_rows[0])
            body_bottom = int(body_rows[-1])
            body_pixels = component[body_top : body_bottom + 1]
            body_cols = np.flatnonzero(np.any(body_pixels, axis=0))
            if body_cols.size == 0:
                continue

            body_left = int(body_cols[0])
            body_right = int(body_cols[-1])
            body_width = body_right - body_left + 1
            body_height = body_bottom - body_top + 1
            if body_width < 3 or body_height < 1:
                continue

            absolute_body = PixelRegion(
                x=region.x + x + body_left,
                y=region.y + y + body_top,
                width=body_width,
                height=body_height,
            )
            center_x = absolute_body.x + absolute_body.width // 2
            component_top = region.y + y
            component_bottom = region.y + y + height - 1
            upper_wick = None
            if component_top < absolute_body.y:
                upper_wick = VerticalWick(
                    x=center_x,
                    top_y=component_top,
                    bottom_y=absolute_body.y - 1,
                )
            lower_wick = None
            if absolute_body.bottom - 1 < component_bottom:
                lower_wick = VerticalWick(
                    x=center_x,
                    top_y=absolute_body.bottom,
                    bottom_y=component_bottom,
                )

            density = min(1.0, area / max(1, width * height))
            body_score = min(1.0, body_width / 8.0)
            confidence = min(1.0, 0.65 + 0.20 * body_score + 0.15 * density)
            candles.append(
                VisualCandle(
                    x=center_x,
                    body=absolute_body,
                    upper_wick=upper_wick,
                    lower_wick=lower_wick,
                    direction=direction,
                    width=body_width,
                    confidence=confidence,
                )
            )
        return candles
