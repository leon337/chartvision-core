import ast
from pathlib import Path


PHASE3_RECONSTRUCTION_MODULES = (
    "app/infrastructure/vision/price_mapper.py",
    "app/infrastructure/vision/price_scale_reader.py",
    "app/domain/services/chart_tracker.py",
    "app/domain/services/normalizer.py",
    "app/infrastructure/vision/reconstruction_pipeline.py",
)


def _imports(path: str) -> tuple[str, ...]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return tuple(imported)


def test_reconstruction_modules_do_not_import_replay_ground_truth_or_chart_source() -> None:
    for path in PHASE3_RECONSTRUCTION_MODULES:
        imported = _imports(path)
        assert not any("replay" in module.lower() for module in imported), path
        assert not any("ground_truth" in module.lower() for module in imported), path
        assert not any("chart_source" in module.lower() for module in imported), path


def test_ground_truth_comparison_is_isolated_to_reconstruction_evaluator() -> None:
    evaluator = Path("app/domain/services/reconstruction_evaluator.py").read_text(
        encoding="utf-8"
    )
    for path in PHASE3_RECONSTRUCTION_MODULES:
        source = Path(path).read_text(encoding="utf-8")
        assert "ReconstructionEvaluator" not in source, path
    assert "ground_truth" in evaluator
