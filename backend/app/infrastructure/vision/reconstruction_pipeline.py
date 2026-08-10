from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.reconstruction import ReconstructionResult
from app.domain.models.vision import VisionStatus
from app.domain.services.chart_tracker import ChartTracker
from app.domain.services.normalizer import NormalizationError, Normalizer
from app.infrastructure.vision.opencv_detector import OpenCVVisionProvider
from app.infrastructure.vision.price_mapper import PriceMapper, PriceMappingError
from app.infrastructure.vision.price_scale_reader import OpenCVPriceScaleReader, PriceScaleReadError


class CandleReconstructionPipeline:
    """Stateful Phase 3 reconstruction pipeline. Ground Truth is intentionally absent."""

    def __init__(self, *, source_id: str, asset: str, timeframe: str) -> None:
        self._vision = OpenCVVisionProvider()
        self._scale_reader = OpenCVPriceScaleReader()
        self._tracker = ChartTracker(timeframe)
        self._normalizer = Normalizer(source_id=source_id, asset=asset, timeframe=timeframe)
        self._last_calibration_confidence = 0.0

    def process(self, image: bytes, frame: Frame) -> ReconstructionResult:
        observation = self._vision.observe(image)
        if observation.status is not VisionStatus.OK or observation.candles is None:
            return self._failure(observation.status, observation.status.value)
        if observation.chart.price_scale_region is None:
            return self._failure(VisionStatus.PRICE_SCALE_NOT_FOUND, "PRICE_SCALE_NOT_FOUND")

        try:
            anchors = self._scale_reader.read(image, observation.chart.price_scale_region)
            mapper = PriceMapper(anchors)
            mapped = tuple(
                mapper.map_candle(
                    candle,
                    visual_quality=observation.visual_quality,
                )
                for candle in observation.candles.candles
            )
        except (PriceScaleReadError, PriceMappingError) as exc:
            return self._failure(VisionStatus.PRICE_SCALE_NOT_FOUND, str(exc))

        tracking = self._tracker.update(frame, mapped)
        if tracking.status is not VisionStatus.OK:
            return ReconstructionResult(
                status=tracking.status,
                candles=(),
                tracking=tracking,
                calibration_confidence=mapper.calibration_confidence,
                failure_reason=tracking.failure_reason,
            )

        try:
            candles = self._normalizer.normalize_many(tracking.candles)
        except NormalizationError as exc:
            return self._failure(VisionStatus.CANDLE_DETECTION_FAILED, str(exc))

        self._last_calibration_confidence = mapper.calibration_confidence
        return ReconstructionResult(
            status=VisionStatus.OK,
            candles=candles,
            tracking=tracking,
            calibration_confidence=mapper.calibration_confidence,
        )

    def snapshot(self) -> tuple[Candle, ...]:
        return self._normalizer.normalize_many(self._tracker.snapshot())

    def _failure(self, status: VisionStatus, reason: str) -> ReconstructionResult:
        return ReconstructionResult(
            status=status,
            candles=(),
            tracking=None,
            calibration_confidence=self._last_calibration_confidence,
            failure_reason=reason,
        )
