from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.interfaces.storage_provider import AnalysisConflictError, StorageProvider
from app.domain.models.analysis import Analysis, AnalysisConfig, AnalysisDecision, MarketState
from app.domain.models.candle import Candle
from app.domain.services.analysis_lab_service import AnalysisLabService

BASE = datetime(2026, 8, 11, 6, 0, tzinfo=timezone.utc)
CONFIG = AnalysisConfig(
    trend_pairs=2,
    lateralization_window_candles=3,
    lateralization_max_range_ratio=Decimal("0.0100"),
    minimum_data_quality=0.80,
)


class RecordingStorage:
    def __init__(self, candles: tuple[Candle, ...]) -> None:
        self.candles = candles
        self.saved: dict[str, Analysis] = {}

    def get_candles_as_of(self, session_id: str, as_of: datetime) -> tuple[Candle, ...]:
        return self.candles

    def save_analysis(self, analysis: Analysis) -> None:
        existing = self.saved.get(analysis.analysis_id)
        if existing is None:
            self.saved[analysis.analysis_id] = analysis
            return
        if existing != analysis:
            raise AnalysisConflictError("conflicting analysis")

    def get_analysis(self, analysis_id: str) -> Analysis | None:
        return self.saved.get(analysis_id)


def _candle(minute: int, high: str, low: str, close: str) -> Candle:
    open_time = BASE + timedelta(minutes=minute)
    return Candle(
        source_id="vision",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        is_closed=True,
        vision_confidence=0.9,
        source_confidence=None,
    )


def _rising_history() -> tuple[Candle, ...]:
    return (
        _candle(-3, "101", "97", "99"),
        _candle(-2, "102", "98", "100"),
        _candle(-1, "103", "99", "101"),
    )


def test_storage_provider_exposes_analysis_persistence_contract() -> None:
    assert hasattr(StorageProvider, "save_analysis")
    assert hasattr(StorageProvider, "get_analysis")
    assert issubclass(AnalysisConflictError, ValueError)


def test_analyze_contract_remains_analysis_decision() -> None:
    service = AnalysisLabService(RecordingStorage(_rising_history()))

    result = service.analyze("session-1", BASE, CONFIG)

    assert isinstance(result, AnalysisDecision)
    assert result.market_state is MarketState.UP


def test_analyze_and_record_creates_analysis_with_explicit_identity_and_as_of() -> None:
    storage = RecordingStorage(_rising_history())
    service = AnalysisLabService(storage)

    result = service.analyze_and_record(
        analysis_id="analysis-1",
        session_id="session-1",
        as_of=BASE,
        config=CONFIG,
    )

    assert isinstance(result, Analysis)
    assert result.analysis_id == "analysis-1"
    assert result.session_id == "session-1"
    assert result.timestamp == BASE
    assert storage.get_analysis("analysis-1") == result


def test_persisted_evidence_has_complete_configuration_in_stable_order() -> None:
    storage = RecordingStorage(_rising_history())
    service = AnalysisLabService(storage)

    result = service.analyze_and_record(
        analysis_id="analysis-evidence",
        session_id="session-1",
        as_of=BASE,
        config=CONFIG,
    )

    assert result.evidence == (
        "STATE_RULE=RISING_STRUCTURE",
        "BASIC_TREND=RISING_STRUCTURE",
        "BASIC_LATERALIZATION=FALSE",
        "DATA_QUALITY=0.9",
        "TREND_PAIRS=2",
        "LATERALIZATION_WINDOW_CANDLES=3",
        "LATERALIZATION_MAX_RANGE_RATIO=0.01",
        "MINIMUM_DATA_QUALITY=0.8",
    )


def test_analyze_and_record_is_deterministic_for_same_inputs() -> None:
    storage = RecordingStorage(_rising_history())
    service = AnalysisLabService(storage)

    first = service.analyze_and_record("analysis-stable", "session-1", BASE, CONFIG)
    second = service.analyze_and_record("analysis-stable", "session-1", BASE, CONFIG)

    assert first == second
    assert storage.get_analysis("analysis-stable") == first
    assert len(storage.saved) == 1


def test_insufficient_history_persists_canonical_evidence_plus_config() -> None:
    storage = RecordingStorage(_rising_history()[:2])
    service = AnalysisLabService(storage)

    result = service.analyze_and_record(
        "analysis-insufficient",
        "session-1",
        BASE,
        CONFIG,
    )

    assert result.market_state is MarketState.UNCERTAIN
    assert result.evidence == (
        "STATE_RULE=INSUFFICIENT_HISTORY",
        "BASIC_TREND=NONE",
        "BASIC_LATERALIZATION=NONE",
        "DATA_QUALITY=NONE",
        "TREND_PAIRS=2",
        "LATERALIZATION_WINDOW_CANDLES=3",
        "LATERALIZATION_MAX_RANGE_RATIO=0.01",
        "MINIMUM_DATA_QUALITY=0.8",
    )
