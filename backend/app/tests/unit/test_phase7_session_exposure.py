from datetime import datetime, timezone

import pytest

from app.domain.models.outcome import ExposureTrackingState
from app.domain.models.session_exposure import SessionExposureState


def test_tracked_state_requires_origin_and_watermark() -> None:
    with pytest.raises(ValueError):
        SessionExposureState(
            session_id="session-1",
            tracking_state=ExposureTrackingState.TRACKED,
            session_origin_time=None,
            session_exposure_watermark=None,
        )


def test_tracked_state_rejects_regressed_watermark() -> None:
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        SessionExposureState(
            session_id="session-1",
            tracking_state=ExposureTrackingState.TRACKED,
            session_origin_time=origin,
            session_exposure_watermark=datetime(2026, 8, 12, 9, 59, tzinfo=timezone.utc),
        )


def test_legacy_unknown_cannot_claim_provenance() -> None:
    with pytest.raises(ValueError):
        SessionExposureState(
            session_id="session-1",
            tracking_state=ExposureTrackingState.LEGACY_UNKNOWN,
            session_origin_time=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
            session_exposure_watermark=None,
        )


def test_valid_tracked_state_is_immutable_value_object() -> None:
    origin = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    state = SessionExposureState(
        session_id="session-1",
        tracking_state=ExposureTrackingState.TRACKED,
        session_origin_time=origin,
        session_exposure_watermark=origin,
    )
    assert state.session_exposure_watermark == origin
