from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from app.domain.models.candle import Candle
from app.domain.models.reconstruction_metrics import ReconstructionMetrics


class ReconstructionEvaluator:
    """Compare already-reconstructed candles with Ground Truth after reconstruction."""

    def evaluate(
        self,
        reconstructed: Iterable[Candle],
        ground_truth: Iterable[Candle],
    ) -> ReconstructionMetrics:
        reconstructed_tuple = tuple(reconstructed)
        truth_tuple = tuple(ground_truth)
        truth_by_key = {self._key(candle): candle for candle in truth_tuple}
        if len(truth_by_key) != len(truth_tuple):
            raise ValueError("DUPLICATE_GROUND_TRUTH_CANDLE")

        reconstructed_groups: dict[tuple[object, ...], list[Candle]] = defaultdict(list)
        for candle in reconstructed_tuple:
            reconstructed_groups[self._key(candle)].append(candle)

        duplicate_count = sum(max(0, len(group) - 1) for group in reconstructed_groups.values())
        matched_pairs: list[tuple[Candle, Candle]] = []
        for key, truth in truth_by_key.items():
            candidates = reconstructed_groups.get(key)
            if candidates:
                matched_pairs.append((candidates[-1], truth))

        matched_count = len(matched_pairs)
        truth_count = len(truth_tuple)
        reconstructed_count = len(reconstructed_tuple)
        missing_count = max(0, truth_count - matched_count)

        return ReconstructionMetrics(
            open_error=self._mean_error(matched_pairs, "open"),
            high_error=self._mean_error(matched_pairs, "high"),
            low_error=self._mean_error(matched_pairs, "low"),
            close_error=self._mean_error(matched_pairs, "close"),
            candle_detection_rate=self._rate(matched_count, truth_count),
            direction_accuracy=self._direction_accuracy(matched_pairs),
            duplicate_rate=self._rate(duplicate_count, reconstructed_count),
            missing_candle_rate=self._rate(missing_count, truth_count),
            matched_candles=matched_count,
            ground_truth_candles=truth_count,
            reconstructed_candles=reconstructed_count,
        )

    @staticmethod
    def _key(candle: Candle) -> tuple[object, ...]:
        return (
            candle.session_id,
            candle.asset,
            candle.timeframe,
            candle.open_time,
        )

    @staticmethod
    def _mean_error(
        pairs: list[tuple[Candle, Candle]],
        field: str,
    ) -> Decimal | None:
        if not pairs:
            return None
        errors = tuple(
            abs(getattr(reconstructed, field) - getattr(truth, field))
            for reconstructed, truth in pairs
        )
        return sum(errors, start=Decimal("0")) / Decimal(len(errors))

    @classmethod
    def _direction_accuracy(cls, pairs: list[tuple[Candle, Candle]]) -> float:
        if not pairs:
            return 0.0
        correct = sum(
            cls._direction(reconstructed) == cls._direction(truth)
            for reconstructed, truth in pairs
        )
        return correct / len(pairs)

    @staticmethod
    def _direction(candle: Candle) -> int:
        if candle.close > candle.open:
            return 1
        if candle.close < candle.open:
            return -1
        return 0

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return numerator / denominator
