from decimal import ROUND_HALF_EVEN, Decimal, localcontext

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

    @staticmethod
    def candle_return(candle: Candle, previous_candle: Candle) -> Decimal | None:
        if not previous_candle.is_closed or previous_candle.close == Decimal("0"):
            return None

        with localcontext() as context:
            context.prec = 28
            context.rounding = ROUND_HALF_EVEN
            return (candle.close - previous_candle.close) / previous_candle.close
