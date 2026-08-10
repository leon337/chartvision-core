from app.domain.models.vision import CandleDirection, VisionStatus
from app.infrastructure.vision.candle_detector import CandleDetector
from app.infrastructure.vision.opencv_detector import ChartDetector
from app.tests.vision_reference import reference_chart_png


def test_candle_detector_finds_geometry_direction_wicks_and_confidence() -> None:
    image = reference_chart_png()
    chart = ChartDetector().detect(image)
    assert chart.candle_region is not None

    result = CandleDetector().detect(image, chart.candle_region)

    assert result.status is VisionStatus.OK
    assert len(result.candles) == 3
    assert tuple(candle.direction for candle in result.candles) == (
        CandleDirection.UP,
        CandleDirection.DOWN,
        CandleDirection.UP,
    )
    assert all(candle.width >= 10 for candle in result.candles)
    assert all(candle.body.height > 0 for candle in result.candles)
    assert all(candle.upper_wick is not None for candle in result.candles)
    assert all(candle.lower_wick is not None for candle in result.candles)
    assert all(candle.confidence > 0.7 for candle in result.candles)
    assert result.confidence > 0.7


def test_candle_detector_fails_explicitly_when_no_candles_are_visible() -> None:
    image = reference_chart_png(include_candles=False)
    chart = ChartDetector().detect(image)
    assert chart.candle_region is not None

    result = CandleDetector().detect(image, chart.candle_region)
    assert result.status is VisionStatus.CANDLE_DETECTION_FAILED
    assert result.candles == ()


def test_candle_detector_reports_low_quality_for_uniform_pixels() -> None:
    import cv2
    import numpy as np

    from app.domain.models.vision import PixelRegion

    image = np.full((240, 320, 3), (42, 23, 15), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    result = CandleDetector().detect(
        encoded.tobytes(),
        PixelRegion(x=0, y=0, width=320, height=240),
    )
    assert result.status is VisionStatus.LOW_IMAGE_QUALITY
    assert result.candles == ()
