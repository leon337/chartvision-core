from datetime import datetime
from decimal import Decimal
from math import isfinite

from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.models.analysis import Analysis, AnalysisConfig, AnalysisDecision, MarketState
from app.domain.models.candle import Candle
from app.domain.services.analysis_engine import AnalysisEngine
from app.domain.services.feature_engine import FeatureEngine


class AnalysisLabService:
    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    def analyze(
        self,
        session_id: str,
        as_of: datetime,
        config: AnalysisConfig,
    ) -> AnalysisDecision:
        self._validate_as_of(as_of)
        candles = self._storage.get_candles_as_of(session_id, as_of)
        closed_candles = tuple(candle for candle in candles if candle.is_closed)
        required_closed_candles = max(
            config.trend_pairs + 1,
            config.lateralization_window_candles,
        )

        if len(closed_candles) < required_closed_candles:
            return AnalysisDecision(
                market_state=MarketState.UNCERTAIN,
                confidence=0.0,
                data_quality=None,
                evidence=(
                    "STATE_RULE=INSUFFICIENT_HISTORY",
                    "BASIC_TREND=NONE",
                    "BASIC_LATERALIZATION=NONE",
                    "DATA_QUALITY=NONE",
                ),
            )

        required_window = closed_candles[-required_closed_candles:]
        data_quality = self._calculate_data_quality(required_window)
        basic_trend = FeatureEngine.basic_trend(
            candles,
            trend_pairs=config.trend_pairs,
        )
        basic_lateralization = FeatureEngine.basic_lateralization(
            candles,
            lateralization_window_candles=config.lateralization_window_candles,
            lateralization_max_range_ratio=config.lateralization_max_range_ratio,
        )
        return AnalysisEngine.classify(
            basic_trend=basic_trend,
            basic_lateralization=basic_lateralization,
            data_quality=data_quality,
            minimum_data_quality=config.minimum_data_quality,
        )

    def analyze_and_record(
        self,
        analysis_id: str,
        session_id: str,
        as_of: datetime,
        config: AnalysisConfig,
    ) -> Analysis:
        decision = self.analyze(session_id, as_of, config)
        analysis = Analysis(
            analysis_id=analysis_id,
            session_id=session_id,
            timestamp=as_of,
            market_state=decision.market_state,
            confidence=decision.confidence,
            data_quality=decision.data_quality,
            evidence=self._persisted_evidence(decision, config),
        )
        self._storage.save_analysis(analysis)
        return analysis

    @staticmethod
    def _persisted_evidence(
        decision: AnalysisDecision,
        config: AnalysisConfig,
    ) -> tuple[str, ...]:
        classifier_evidence = tuple(
            token
            for token in decision.evidence
            if not token.startswith("MINIMUM_DATA_QUALITY=")
        )
        return classifier_evidence + (
            f"TREND_PAIRS={config.trend_pairs}",
            f"LATERALIZATION_WINDOW_CANDLES={config.lateralization_window_candles}",
            "LATERALIZATION_MAX_RANGE_RATIO="
            f"{AnalysisLabService._format_decimal(config.lateralization_max_range_ratio)}",
            "MINIMUM_DATA_QUALITY="
            f"{AnalysisLabService._format_float(config.minimum_data_quality)}",
        )

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        return format(value.normalize(), "f")

    @staticmethod
    def _format_float(value: float) -> str:
        return format(Decimal(str(value)).normalize(), "f")

    @staticmethod
    def _validate_as_of(as_of: datetime) -> None:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

    @staticmethod
    def _calculate_data_quality(candles: tuple[Candle, ...]) -> float | None:
        has_missing_quality = False
        valid_qualities: list[float] = []
        for candle in candles:
            quality = candle.vision_confidence
            if quality is None:
                has_missing_quality = True
                continue
            if not isfinite(quality) or not 0.0 <= quality <= 1.0:
                raise ValueError("vision_confidence must be between 0.0 and 1.0")
            valid_qualities.append(quality)

        if has_missing_quality:
            return None
        return min(valid_qualities)
