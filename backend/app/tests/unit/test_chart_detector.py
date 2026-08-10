import cv2
import numpy as np

from app.domain.models.vision import VisionStatus
from app.infrastructure.vision.opencv_detector import ChartDetector
from app.tests.vision_reference import checkerboard_png, reference_chart_png


def test_chart_detector_finds_controlled_chart_and_visual_scale_regions() -> None:
    result = ChartDetector().detect(reference_chart_png())

    assert result.status is VisionStatus.OK
    assert result.chart_region is not None
    assert result.candle_region is not None
    assert result.price_scale_region is not None
    assert result.confidence > 0.8
    assert result.visual_quality > 0.08
    assert result.candle_region.width < result.chart_region.width
    assert result.candle_region.height < result.chart_region.height
    assert result.warnings == ()


def test_chart_detector_returns_chart_not_found_for_detailed_non_chart_image() -> None:
    result = ChartDetector().detect(checkerboard_png())
    assert result.status is VisionStatus.CHART_NOT_FOUND
    assert result.chart_region is None


def test_chart_detector_returns_low_quality_instead_of_inventing_chart() -> None:
    image = np.full((240, 320, 3), (42, 23, 15), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    result = ChartDetector().detect(encoded.tobytes())
    assert result.status is VisionStatus.LOW_IMAGE_QUALITY
    assert result.chart_region is None


def test_chart_detector_reports_missing_price_scale_as_warning() -> None:
    result = ChartDetector().detect(reference_chart_png(include_scale=False))

    assert result.status is VisionStatus.OK
    assert result.chart_region is not None
    assert result.candle_region is not None
    assert result.price_scale_region is None
    assert result.warnings == (VisionStatus.PRICE_SCALE_NOT_FOUND,)
