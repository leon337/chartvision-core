from dataclasses import dataclass
from datetime import datetime

from app.domain.models.outcome import ExposureTrackingState


@dataclass(frozen=True, slots=True)
class SessionExposureState:
    session_id: str
    tracking_state: ExposureTrackingState
    session_origin_time: datetime | None
    session_exposure_watermark: datetime | None

    def __post_init__(self) -> None:
        if self.tracking_state is ExposureTrackingState.LEGACY_UNKNOWN:
            if self.session_origin_time is not None or self.session_exposure_watermark is not None:
                raise ValueError("LEGACY_UNKNOWN exposure state cannot claim origin or watermark")
            return

        if self.session_origin_time is None or self.session_exposure_watermark is None:
            raise ValueError("TRACKED exposure state requires origin and watermark")
        for field_name, value in (
            ("session_origin_time", self.session_origin_time),
            ("session_exposure_watermark", self.session_exposure_watermark),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.session_exposure_watermark < self.session_origin_time:
            raise ValueError("session_exposure_watermark cannot precede session_origin_time")
