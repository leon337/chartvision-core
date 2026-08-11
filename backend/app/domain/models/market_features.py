from enum import StrEnum


class MarketCandleDirection(StrEnum):
    CLOSE_ABOVE_OPEN = "CLOSE_ABOVE_OPEN"
    CLOSE_BELOW_OPEN = "CLOSE_BELOW_OPEN"
    CLOSE_EQUAL_OPEN = "CLOSE_EQUAL_OPEN"
