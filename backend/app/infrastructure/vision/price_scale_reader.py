from decimal import Decimal, InvalidOperation

import cv2
import numpy as np

from app.domain.models.vision import PixelRegion
from app.infrastructure.vision.price_mapper import PriceAnchor


_TEXT_THRESHOLD = 100
_TEMPLATE_WIDTH = 14
_TEMPLATE_HEIGHT = 20
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.45
_FONT_THICKNESS = 1
_MIN_GLYPH_CONFIDENCE = 0.58
_MIN_ROW_HEIGHT = 5


class PriceScaleReadError(ValueError):
    """Explicit failure when visible scale labels cannot produce price anchors."""


class OpenCVPriceScaleReader:
    """Read integer price labels from the controlled v1 price scale using pixels only."""

    def __init__(self, *, min_glyph_confidence: float = _MIN_GLYPH_CONFIDENCE) -> None:
        if not 0.0 <= min_glyph_confidence <= 1.0:
            raise ValueError("MIN_GLYPH_CONFIDENCE_OUT_OF_RANGE")
        self._min_glyph_confidence = min_glyph_confidence
        self._templates = self._build_digit_templates()

    def read(self, image: bytes, region: PixelRegion) -> tuple[PriceAnchor, ...]:
        decoded = self._decode(image)
        if decoded is None or not self._region_is_valid(decoded, region):
            raise PriceScaleReadError("PRICE_SCALE_NOT_FOUND")

        roi = decoded[region.y : region.bottom, region.x : region.right]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mask = (gray > _TEXT_THRESHOLD).astype(np.uint8) * 255
        rows = self._bands(np.flatnonzero(np.any(mask > 0, axis=1)))

        anchors: list[PriceAnchor] = []
        for top, bottom in rows:
            if bottom - top + 1 < _MIN_ROW_HEIGHT:
                continue
            row = mask[top : bottom + 1]
            columns = self._bands(np.flatnonzero(np.any(row > 0, axis=0)))
            if not columns:
                continue

            text_parts: list[str] = []
            confidences: list[float] = []
            for left, right in columns:
                glyph = row[:, left : right + 1]
                digit, confidence = self._recognize_digit(glyph)
                if confidence < self._min_glyph_confidence:
                    text_parts = []
                    break
                text_parts.append(digit)
                confidences.append(confidence)

            if not text_parts:
                continue
            text = "".join(text_parts)
            try:
                price = Decimal(text)
            except InvalidOperation:
                continue
            anchors.append(
                PriceAnchor(
                    y=region.y + bottom,
                    price=price,
                    confidence=min(confidences),
                )
            )

        if len(anchors) < 2:
            raise PriceScaleReadError("INSUFFICIENT_VISUAL_PRICE_ANCHORS")
        return tuple(sorted(anchors, key=lambda anchor: anchor.y))

    @staticmethod
    def _decode(image: bytes) -> np.ndarray | None:
        if not image:
            return None
        array = np.frombuffer(image, dtype=np.uint8)
        return cv2.imdecode(array, cv2.IMREAD_COLOR)

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

    @staticmethod
    def _bands(indices: np.ndarray) -> list[tuple[int, int]]:
        if indices.size == 0:
            return []
        values = [int(value) for value in indices]
        start = previous = values[0]
        bands: list[tuple[int, int]] = []
        for value in values[1:]:
            if value > previous + 1:
                bands.append((start, previous))
                start = value
            previous = value
        bands.append((start, previous))
        return bands

    def _recognize_digit(self, glyph: np.ndarray) -> tuple[str, float]:
        normalized = self._normalize(glyph)
        scores = {
            digit: self._binary_similarity(normalized, template)
            for digit, template in self._templates.items()
        }
        digit = max(scores, key=scores.__getitem__)
        return digit, scores[digit]

    @staticmethod
    def _binary_similarity(left: np.ndarray, right: np.ndarray) -> float:
        left_on = left > 0
        right_on = right > 0
        union = np.count_nonzero(left_on | right_on)
        if union == 0:
            return 0.0
        intersection = np.count_nonzero(left_on & right_on)
        return float(intersection / union)

    @staticmethod
    def _normalize(glyph: np.ndarray) -> np.ndarray:
        ys, xs = np.where(glyph > 0)
        if xs.size == 0:
            return np.zeros((_TEMPLATE_HEIGHT, _TEMPLATE_WIDTH), dtype=np.uint8)
        cropped = glyph[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
        return cv2.resize(
            cropped,
            (_TEMPLATE_WIDTH, _TEMPLATE_HEIGHT),
            interpolation=cv2.INTER_NEAREST,
        )

    @classmethod
    def _build_digit_templates(cls) -> dict[str, np.ndarray]:
        templates: dict[str, np.ndarray] = {}
        for digit in "0123456789":
            canvas = np.zeros((30, 30), dtype=np.uint8)
            cv2.putText(
                canvas,
                digit,
                (2, 18),
                _FONT,
                _FONT_SCALE,
                255,
                _FONT_THICKNESS,
                cv2.LINE_AA,
            )
            _, mask = cv2.threshold(canvas, _TEXT_THRESHOLD, 255, cv2.THRESH_BINARY)
            templates[digit] = cls._normalize(mask)
        return templates
