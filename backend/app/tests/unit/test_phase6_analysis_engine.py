from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.models.analysis import (
    Analysis,
    AnalysisConfig,
    AnalysisDecision,
    MarketState,
)
from app.domain.models.market_features import BasicTrend
from app.domain.services.analysis_engine import AnalysisEngine

MINIMUM_DATA_QUALITY = 0.8


def _classify(
    *,
    basic_trend: BasicTrend | None = BasicTrend.RISING_STRUCTURE,
    basic_lateralization: bool | None = False,
    data_quality: float | None = 0.9,
    minimum_data_quality: float = MINIMUM_DATA_QUALITY,
) -> AnalysisDecision:
    return AnalysisEngine.classify(
        basic_trend=basic_trend,
        basic_lateralization=basic_lateralization,
        data_quality=data_quality,
        minimum_data_quality=minimum_data_quality,
    )


def test_classifies_up() -> None:
    decision = _classify(basic_trend=BasicTrend.RISING_STRUCTURE)
    assert decision.market_state is MarketState.UP


def test_classifies_down() -> None:
    decision = _classify(basic_trend=BasicTrend.FALLING_STRUCTURE)
    assert decision.market_state is MarketState.DOWN


def test_classifies_sideways() -> None:
    decision = _classify(
        basic_trend=BasicTrend.MIXED_STRUCTURE,
        basic_lateralization=True,
    )
    assert decision.market_state is MarketState.SIDEWAYS


def test_mixed_non_lateral_is_uncertain() -> None:
    decision = _classify(basic_trend=BasicTrend.MIXED_STRUCTURE)
    assert decision.market_state is MarketState.UNCERTAIN


def test_missing_trend_is_uncertain() -> None:
    decision = _classify(basic_trend=None)
    assert decision.market_state is MarketState.UNCERTAIN


def test_missing_lateralization_is_uncertain() -> None:
    decision = _classify(basic_lateralization=None)
    assert decision.market_state is MarketState.UNCERTAIN


def test_unrecognized_lateralization_is_uncertain() -> None:
    decision = AnalysisEngine.classify(
        basic_trend=BasicTrend.RISING_STRUCTURE,
        basic_lateralization="unexpected",  # type: ignore[arg-type]
        data_quality=0.9,
        minimum_data_quality=MINIMUM_DATA_QUALITY,
    )
    assert decision.market_state is MarketState.UNCERTAIN


def test_low_data_quality_is_uncertain() -> None:
    decision = _classify(data_quality=0.79)
    assert decision.market_state is MarketState.UNCERTAIN


def test_missing_data_quality_is_uncertain() -> None:
    decision = _classify(data_quality=None)
    assert decision.market_state is MarketState.UNCERTAIN


def test_quality_equal_threshold_is_allowed() -> None:
    decision = _classify(data_quality=MINIMUM_DATA_QUALITY)
    assert decision.market_state is MarketState.UP


def test_sideways_precedes_directional_state() -> None:
    decision = _classify(
        basic_trend=BasicTrend.RISING_STRUCTURE,
        basic_lateralization=True,
    )
    assert decision.market_state is MarketState.SIDEWAYS


def test_same_input_produces_same_decision() -> None:
    first = _classify()
    second = _classify()
    assert first == second


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trend_pairs", 0),
        ("lateralization_window_candles", 2),
        ("lateralization_max_range_ratio", Decimal("-0.01")),
        ("minimum_data_quality", -0.01),
        ("minimum_data_quality", 1.01),
    ],
)
def test_analysis_config_rejects_invalid_values(field: str, value: object) -> None:
    config_values = {
        "trend_pairs": 3,
        "lateralization_window_candles": 5,
        "lateralization_max_range_ratio": Decimal("0.02"),
        "minimum_data_quality": 0.8,
    }
    config_values[field] = value

    with pytest.raises(ValueError):
        AnalysisConfig(**config_values)  # type: ignore[arg-type]


@pytest.mark.parametrize("data_quality", [-0.01, 1.01, float("nan"), float("inf")])
def test_rejects_data_quality_outside_valid_range(data_quality: float) -> None:
    with pytest.raises(ValueError):
        _classify(data_quality=data_quality)


@pytest.mark.parametrize("minimum_data_quality", [-0.01, 1.01, float("nan")])
def test_rejects_invalid_minimum_data_quality(minimum_data_quality: float) -> None:
    with pytest.raises(ValueError):
        _classify(minimum_data_quality=minimum_data_quality)


def test_determined_state_confidence_equals_data_quality() -> None:
    decision = _classify(data_quality=0.91)
    assert decision.confidence == 0.91


def test_uncertain_confidence_is_zero() -> None:
    decision = _classify(basic_trend=BasicTrend.MIXED_STRUCTURE)
    assert decision.confidence == 0.0


def test_evidence_is_deterministic_and_auditable() -> None:
    decision = _classify(data_quality=0.91)
    assert decision.evidence == (
        "STATE_RULE=RISING_STRUCTURE",
        "BASIC_TREND=RISING_STRUCTURE",
        "BASIC_LATERALIZATION=FALSE",
        "DATA_QUALITY=0.91",
        "MINIMUM_DATA_QUALITY=0.8",
    )


def test_missing_values_use_stable_evidence_tokens() -> None:
    decision = _classify(
        basic_trend=None,
        basic_lateralization=None,
        data_quality=None,
    )
    assert decision.evidence == (
        "STATE_RULE=MISSING_DATA_QUALITY",
        "BASIC_TREND=NONE",
        "BASIC_LATERALIZATION=NONE",
        "DATA_QUALITY=NONE",
        "MINIMUM_DATA_QUALITY=0.8",
    )


def test_analysis_decision_is_immutable() -> None:
    decision = _classify()
    with pytest.raises(FrozenInstanceError):
        decision.confidence = 0.1  # type: ignore[misc]


def test_analysis_allows_missing_data_quality() -> None:
    analysis = Analysis(
        analysis_id="analysis-1",
        session_id="session-1",
        timestamp=datetime(2026, 8, 11, tzinfo=timezone.utc),
        market_state=MarketState.UNCERTAIN,
        confidence=0.0,
        data_quality=None,
    )
    assert analysis.data_quality is None
