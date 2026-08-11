from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from app.domain.models.candle import Candle
from app.domain.models.market_features import BasicTrend, MarketCandleDirection


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

    @staticmethod
    def simple_volatility(
        candles: tuple[Candle, ...], volatility_window_candles: int
    ) -> Decimal | None:
        if volatility_window_candles < 3:
            raise ValueError("volatility_window_candles must be at least 3")

        closed_candles = tuple(candle for candle in candles if candle.is_closed)
        if len(closed_candles) < volatility_window_candles:
            return None

        window = closed_candles[-volatility_window_candles:]
        returns: list[Decimal] = []
        for previous_candle, candle in zip(window, window[1:]):
            candle_return = FeatureEngine.candle_return(candle, previous_candle)
            if candle_return is None:
                return None
            returns.append(candle_return)

        with localcontext() as context:
            context.prec = 28
            context.rounding = ROUND_HALF_EVEN
            return_count = Decimal(len(returns))
            mean = sum(returns, Decimal("0")) / return_count
            squared_deviations = (
                (candle_return - mean) ** 2 for candle_return in returns
            )
            variance = sum(squared_deviations, Decimal("0")) / return_count
            return context.sqrt(variance)

    @staticmethod
    def higher_high(candle: Candle, previous_candle: Candle) -> bool | None:
        if not candle.is_closed or not previous_candle.is_closed:
            return None
        return candle.high > previous_candle.high

    @staticmethod
    def higher_low(candle: Candle, previous_candle: Candle) -> bool | None:
        if not candle.is_closed or not previous_candle.is_closed:
            return None
        return candle.low > previous_candle.low

    @staticmethod
    def lower_high(candle: Candle, previous_candle: Candle) -> bool | None:
        if not candle.is_closed or not previous_candle.is_closed:
            return None
        return candle.high < previous_candle.high

    @staticmethod
    def lower_low(candle: Candle, previous_candle: Candle) -> bool | None:
        if not candle.is_closed or not previous_candle.is_closed:
            return None
        return candle.low < previous_candle.low

    @staticmethod
    def basic_trend(
        candles: tuple[Candle, ...], trend_pairs: int
    ) -> BasicTrend | None:
        if trend_pairs < 1:
            raise ValueError("trend_pairs must be at least 1")

        closed_candles = tuple(candle for candle in candles if candle.is_closed)
        window_size = trend_pairs + 1
        if len(closed_candles) < window_size:
            return None

        window = closed_candles[-window_size:]
        all_rising = True
        all_falling = True
        for previous_candle, candle in zip(window, window[1:]):
            higher_high = FeatureEngine.higher_high(candle, previous_candle)
            higher_low = FeatureEngine.higher_low(candle, previous_candle)
            lower_high = FeatureEngine.lower_high(candle, previous_candle)
            lower_low = FeatureEngine.lower_low(candle, previous_candle)

            all_rising = all_rising and higher_high is True and higher_low is True
            all_falling = all_falling and lower_high is True and lower_low is True

        if all_rising:
            return BasicTrend.RISING_STRUCTURE
        if all_falling:
            return BasicTrend.FALLING_STRUCTURE
        return BasicTrend.MIXED_STRUCTURE
