import ast
import inspect

from app.domain.models.vision import VisionStatus
from app.infrastructure.vision import candle_detector, capture_service, opencv_detector
from app.infrastructure.vision.opencv_detector import OpenCVVisionProvider
from app.tests.vision_reference import reference_chart_png


def test_visual_observer_identifies_visible_candles_from_pixels_only() -> None:
    observation = OpenCVVisionProvider().observe(reference_chart_png())

    assert observation.status is VisionStatus.OK
    assert observation.candles is not None
    assert len(observation.candles.candles) == 3
    assert observation.confidence > 0.7
    assert observation.chart.candle_region is not None


def test_visual_modules_have_no_replay_or_ground_truth_import_dependency() -> None:
    forbidden_prefixes = ("app.infrastructure.replay", "app.domain.interfaces.chart_source")
    for module in (capture_service, opencv_detector, candle_detector):
        tree = ast.parse(inspect.getsource(module))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(
            imported.startswith(prefix)
            for imported in imports
            for prefix in forbidden_prefixes
        )

    parameters = tuple(inspect.signature(OpenCVVisionProvider.observe).parameters)
    assert parameters == ("self", "image")
