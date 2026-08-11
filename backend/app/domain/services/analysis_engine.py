from math import isfinite

from app.domain.models.analysis import AnalysisDecision, MarketState
from app.domain.models.market_features import BasicTrend


class AnalysisEngine:
    @staticmethod
    def classify(
        basic_trend: BasicTrend | None,
        basic_lateralization: bool | None,
        data_quality: float | None,
        minimum_data_quality: float,
    ) -> AnalysisDecision:
        if not isfinite(minimum_data_quality) or not 0.0 <= minimum_data_quality <= 1.0:
            raise ValueError("minimum_data_quality must be between 0.0 and 1.0")
        if data_quality is not None and (
            not isfinite(data_quality) or not 0.0 <= data_quality <= 1.0
        ):
            raise ValueError("data_quality must be between 0.0 and 1.0")

        if data_quality is None:
            return AnalysisEngine._decision(
                MarketState.UNCERTAIN,
                "MISSING_DATA_QUALITY",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        if data_quality < minimum_data_quality:
            return AnalysisEngine._decision(
                MarketState.UNCERTAIN,
                "LOW_DATA_QUALITY",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        if basic_lateralization is None:
            return AnalysisEngine._decision(
                MarketState.UNCERTAIN,
                "MISSING_LATERALIZATION",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        if basic_lateralization is True:
            return AnalysisEngine._decision(
                MarketState.SIDEWAYS,
                "SIDEWAYS",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        if basic_lateralization is not False:
            return AnalysisEngine._decision(
                MarketState.UNCERTAIN,
                "UNRECOGNIZED_LATERALIZATION",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        if basic_trend is BasicTrend.RISING_STRUCTURE:
            return AnalysisEngine._decision(
                MarketState.UP,
                "RISING_STRUCTURE",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        if basic_trend is BasicTrend.FALLING_STRUCTURE:
            return AnalysisEngine._decision(
                MarketState.DOWN,
                "FALLING_STRUCTURE",
                basic_trend,
                basic_lateralization,
                data_quality,
                minimum_data_quality,
            )
        return AnalysisEngine._decision(
            MarketState.UNCERTAIN,
            "UNCERTAIN_FALLBACK",
            basic_trend,
            basic_lateralization,
            data_quality,
            minimum_data_quality,
        )

    @staticmethod
    def _decision(
        market_state: MarketState,
        state_rule: str,
        basic_trend: BasicTrend | None,
        basic_lateralization: bool | None,
        data_quality: float | None,
        minimum_data_quality: float,
    ) -> AnalysisDecision:
        confidence = 0.0 if market_state is MarketState.UNCERTAIN else data_quality
        evidence = (
            f"STATE_RULE={state_rule}",
            f"BASIC_TREND={AnalysisEngine._format_trend(basic_trend)}",
            f"BASIC_LATERALIZATION={AnalysisEngine._format_optional_bool(basic_lateralization)}",
            f"DATA_QUALITY={AnalysisEngine._format_optional_float(data_quality)}",
            f"MINIMUM_DATA_QUALITY={minimum_data_quality}",
        )
        return AnalysisDecision(
            market_state=market_state,
            confidence=confidence,
            data_quality=data_quality,
            evidence=evidence,
        )

    @staticmethod
    def _format_trend(basic_trend: BasicTrend | None) -> str:
        return "NONE" if basic_trend is None else basic_trend.value

    @staticmethod
    def _format_optional_bool(value: bool | None) -> str:
        if value is None:
            return "NONE"
        return "TRUE" if value else "FALSE"

    @staticmethod
    def _format_optional_float(value: float | None) -> str:
        return "NONE" if value is None else str(value)
