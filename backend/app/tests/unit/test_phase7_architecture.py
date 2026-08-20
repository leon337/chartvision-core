from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (APP_ROOT / relative_path).read_text(encoding="utf-8")


def test_analysis_layer_remains_isolated_from_ground_truth_and_outcomes() -> None:
    banned = (
        "GroundTruthProvider",
        "ground_truth_provider",
        "OutcomeEvaluator",
        "OutcomeEvaluationService",
        "ReplaySource",
    )
    for relative_path in (
        "domain/services/analysis_engine.py",
        "domain/services/analysis_lab_service.py",
    ):
        source = _source(relative_path)
        for token in banned:
            assert token not in source, f"{relative_path} must not depend on {token}"


def test_phase7_pure_engines_do_not_depend_on_infrastructure_or_io() -> None:
    banned = (
        "sqlalchemy",
        "app.infrastructure",
        "FastAPI",
        "StorageProvider",
        "ReplaySource",
        "GroundTruthProvider",
    )
    for relative_path in (
        "domain/services/outcome_evaluator.py",
        "domain/services/outcome_metrics_engine.py",
    ):
        source = _source(relative_path)
        for token in banned:
            assert token not in source, f"{relative_path} must remain pure and not depend on {token}"


def test_ground_truth_is_not_used_to_reconstruct_exposure_provenance() -> None:
    for relative_path in (
        "infrastructure/storage/outcome_postgres_repository.py",
        "infrastructure/storage/phase7_postgres_repository.py",
        "infrastructure/replay/exposure_tracked_replay.py",
        "infrastructure/replay/replay_session_factory.py",
    ):
        source = _source(relative_path)
        assert "GroundTruthProvider" not in source
        assert "ground_truth_provider" not in source


def test_replay_api_cannot_bypass_tracked_lifecycle_with_raw_replay_source() -> None:
    source = _source("api/routes/replay.py")

    assert "ReplaySessionFactory" in source
    assert "ReplaySource" not in source
    assert "_get_replay_session().advance" in source
    assert "_get_replay_session().reset" in source


def test_visual_pipeline_remains_isolated_from_ground_truth() -> None:
    paths = list((APP_ROOT / "infrastructure" / "vision").rglob("*.py"))
    paths.extend(
        APP_ROOT / relative_path
        for relative_path in (
            "domain/services/chart_tracker.py",
            "domain/services/normalizer.py",
        )
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "GroundTruthProvider" not in source
        assert "ground_truth_provider" not in source
