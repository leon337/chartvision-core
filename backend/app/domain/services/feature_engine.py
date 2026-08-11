from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.models.market_features import MarketCandleDirection


class FeatureEngine:
    @staticmethod
    def candle_direction(candle: Candle) -> MarketCandleDirection:
        if candle.close > candle.open:
            return MarketCandleDirection.CLOSE_ABOVE_OPEN
        if candle.close < candle.open:
            return MarketCandleDirection.CLOSE_BELOW_OPEN
        return MarketCandleDirection.CLOSE_EQUAL_OPEN

    @staticmethod
    def candle_amplitude(candle: Candle) -> Decimal:
        return candle.high - candle.low
