from decimal import Decimal

import pytest

from app.domain.models.vision import PixelRegion
from app.infrastructure.vision.price_scale_reader import (
    OpenCVPriceScaleReader,
    PriceScaleReadError,
)
from app.tests.vision_reference import CHART_REGION, PRICE_SCALE_X, reference_chart_png


def _scale_region() -> PixelRegion:
    return PixelRegion(
        x=PRICE_SCALE_X + 1,
        y=CHART_REGION.y,
        width=CHART_REGION.right - PRICE_SCALE_X - 1,
        height=CHART_REGION.height,
    )


def test_reads_visible_price_labels_as_anchors() -> None:
    anchors = OpenCVPriceScaleReader().read(reference_chart_png(), _scale_region())

    assert [(anchor.y, anchor.price) for anchor in anchors] == [
        (CHART_REGION.y + 80, Decimal("105")),
        (CHART_REGION.y + 180, Decimal("100")),
        (CHART_REGION.y + 280, Decimal("95")),
        (CHART_REGION.y + 380, Decimal("90")),
    ]
    assert all(0.58 <= anchor.confidence <= 1.0 for anchor in anchors)


def test_fails_when_scale_pixels_are_absent() -> None:
    with pytest.raises(PriceScaleReadError, match="INSUFFICIENT_VISUAL_PRICE_ANCHORS"):
        OpenCVPriceScaleReader().read(
            reference_chart_png(include_scale=False),
            _scale_region(),
        )


def test_fails_for_invalid_region() -> None:
    with pytest.raises(PriceScaleReadError, match="PRICE_SCALE_NOT_FOUND"):
        OpenCVPriceScaleReader().read(
            reference_chart_png(),
            PixelRegion(x=9999, y=0, width=10, height=10),
        )
