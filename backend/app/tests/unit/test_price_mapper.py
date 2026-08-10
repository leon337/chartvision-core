import ast
import inspect
from decimal import Decimal

import pytest

import app.infrastructure.vision.price_mapper as price_mapper_module
from app.infrastructure.vision.price_mapper import (
    PriceAnchor,
    PriceMapper,
    PriceMappingError,
    PriceScaleOrientation,
)
from app.tests.vision_reference import CHART_REGION, reference_chart_png


def test_two_valid_anchors_map_endpoints_and_interpolate() -> None:
    mapper = PriceMapper(
        (
            PriceAnchor(y=100, price=Decimal("105")),
            PriceAnchor(y=200, price=Decimal("100")),
        )
    )

    assert mapper.price_for_y(100) == Decimal("105")
    assert mapper.price_for_y(150) == Decimal("102.5")
    assert mapper.price_for_y(200) == Decimal("100")
    assert mapper.orientation is PriceScaleOrientation.PRICE_INCREASES_UP
    assert mapper.calibrated_y_range == (100, 200)
    assert mapper.calibration_confidence == 1.0


def test_multiple_valid_anchors_are_sorted_and_used_piecewise() -> None:
    mapper = PriceMapper(
        (
            PriceAnchor(y=300, price=Decimal("95"), confidence=0.94),
            PriceAnchor(y=100, price=Decimal("105"), confidence=0.97),
            PriceAnchor(y=200, price=Decimal("100"), confidence=0.96),
        )
    )

    assert tuple(anchor.y for anchor in mapper.anchors) == (100, 200, 300)
    assert mapper.price_for_y(250) == Decimal("97.5")
    assert mapper.calibration_confidence == pytest.approx(0.94)


def test_orientation_can_increase_down_when_visual_scale_does() -> None:
    mapper = PriceMapper(
        (
            PriceAnchor(y=10, price=Decimal("10")),
            PriceAnchor(y=30, price=Decimal("20")),
        )
    )

    assert mapper.orientation is PriceScaleOrientation.PRICE_INCREASES_DOWN
    assert mapper.price_for_y(20) == Decimal("15")


def test_empty_scale_fails_explicitly() -> None:
    with pytest.raises(PriceMappingError, match="PRICE_SCALE_NOT_FOUND"):
        PriceMapper(())


def test_single_anchor_is_insufficient() -> None:
    with pytest.raises(PriceMappingError, match="INSUFFICIENT_PRICE_ANCHORS"):
        PriceMapper((PriceAnchor(y=100, price=Decimal("100")),))


def test_non_monotonic_anchors_are_rejected() -> None:
    with pytest.raises(PriceMappingError, match="NON_MONOTONIC_PRICE_ANCHORS"):
        PriceMapper(
            (
                PriceAnchor(y=100, price=Decimal("105")),
                PriceAnchor(y=200, price=Decimal("95")),
                PriceAnchor(y=300, price=Decimal("100")),
            )
        )


def test_materially_inconsistent_linear_scale_is_rejected() -> None:
    with pytest.raises(PriceMappingError, match="INCONSISTENT_PRICE_ANCHORS"):
        PriceMapper(
            (
                PriceAnchor(y=100, price=Decimal("105")),
                PriceAnchor(y=200, price=Decimal("100")),
                PriceAnchor(y=300, price=Decimal("80")),
            )
        )


def test_duplicate_vertical_anchor_is_rejected() -> None:
    with pytest.raises(PriceMappingError, match="DUPLICATE_PRICE_ANCHOR_Y"):
        PriceMapper(
            (
                PriceAnchor(y=100, price=Decimal("105")),
                PriceAnchor(y=100, price=Decimal("100")),
            )
        )


def test_outside_calibrated_region_fails_instead_of_extrapolating() -> None:
    mapper = PriceMapper(
        (
            PriceAnchor(y=100, price=Decimal("105")),
            PriceAnchor(y=200, price=Decimal("100")),
        )
    )

    with pytest.raises(PriceMappingError, match="Y_OUTSIDE_CALIBRATED_RANGE"):
        mapper.price_for_y(99)
    with pytest.raises(PriceMappingError, match="Y_OUTSIDE_CALIBRATED_RANGE"):
        mapper.price_for_y(201)


def test_reference_fixture_visible_scale_anchors_calibrate_without_ground_truth() -> None:
    image = reference_chart_png()
    assert image.startswith(b"\x89PNG")

    scale_y = CHART_REGION.y
    mapper = PriceMapper(
        (
            PriceAnchor(y=scale_y + 80, price=Decimal("105")),
            PriceAnchor(y=scale_y + 180, price=Decimal("100")),
            PriceAnchor(y=scale_y + 280, price=Decimal("95")),
        )
    )

    assert mapper.price_for_y(scale_y + 130) == Decimal("102.5")
    assert mapper.price_for_y(scale_y + 230) == Decimal("97.5")
    assert mapper.orientation is PriceScaleOrientation.PRICE_INCREASES_UP


def test_price_mapper_imports_do_not_cross_replay_or_ground_truth_boundary() -> None:
    tree = ast.parse(inspect.getsource(price_mapper_module))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any("replay" in module.lower() for module in imported_modules)
    assert not any("ground_truth" in module.lower() for module in imported_modules)
    assert not any("chart_source" in module.lower() for module in imported_modules)
