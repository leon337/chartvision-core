from datetime import datetime, timedelta, timezone

import cv2
import numpy as np

from app.domain.models.vision import PixelRegion
from app.infrastructure.vision.capture_service import (
    DEFAULT_CAPTURE_INTERVAL_SECONDS,
    CaptureService,
)


def _png(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_capture_service_crops_hashes_and_detects_frame_changes() -> None:
    service = CaptureService()
    captured_at = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
    image = np.zeros((100, 160, 3), dtype=np.uint8)
    image[20:60, 30:90] = (42, 23, 15)
    region = PixelRegion(x=30, y=20, width=60, height=40)

    first = service.capture(
        session_id="session-a",
        image=_png(image),
        captured_at=captured_at,
        region=region,
    )
    second = service.capture(
        session_id="session-a",
        image=_png(image),
        captured_at=captured_at + timedelta(seconds=5),
        region=region,
    )

    changed_image = image.copy()
    changed_image[25, 35] = (94, 197, 34)
    third = service.capture(
        session_id="session-a",
        image=_png(changed_image),
        captured_at=captured_at + timedelta(seconds=10),
        region=region,
    )

    assert first.frame.width == 60
    assert first.frame.height == 40
    assert first.frame.changed_since_previous is False
    assert second.frame.image_hash == first.frame.image_hash
    assert second.frame.changed_since_previous is False
    assert third.frame.image_hash != second.frame.image_hash
    assert third.frame.changed_since_previous is True
    assert len(first.frame.image_hash) == 64


def test_capture_service_exposes_five_second_default_interval() -> None:
    service = CaptureService()
    started_at = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
    image = np.zeros((80, 80, 3), dtype=np.uint8)

    assert service.capture_interval_seconds == DEFAULT_CAPTURE_INTERVAL_SECONDS == 5.0
    assert service.is_due("session-a", started_at) is True
    service.capture(session_id="session-a", image=_png(image), captured_at=started_at)
    assert service.is_due("session-a", started_at + timedelta(seconds=4, milliseconds=999)) is False
    assert service.is_due("session-a", started_at + timedelta(seconds=5)) is True
