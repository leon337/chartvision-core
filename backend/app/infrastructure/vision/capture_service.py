from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import cv2
import numpy as np

from app.domain.models.frame import Frame
from app.domain.models.vision import PixelRegion


DEFAULT_CAPTURE_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    frame: Frame
    image: bytes


class CaptureService:
    def __init__(self, capture_interval_seconds: float = DEFAULT_CAPTURE_INTERVAL_SECONDS) -> None:
        if capture_interval_seconds <= 0:
            raise ValueError("capture_interval_seconds must be positive")
        self.capture_interval_seconds = capture_interval_seconds
        self._previous_hash_by_session: dict[str, str] = {}
        self._last_capture_at_by_session: dict[str, datetime] = {}

    def is_due(self, session_id: str, at: datetime) -> bool:
        previous = self._last_capture_at_by_session.get(session_id)
        if previous is None:
            return True
        return (at - previous).total_seconds() >= self.capture_interval_seconds

    def capture(
        self,
        *,
        session_id: str,
        image: bytes,
        captured_at: datetime | None = None,
        region: PixelRegion | None = None,
        storage_reference: str | None = None,
    ) -> CapturedFrame:
        captured_at = captured_at or datetime.now(timezone.utc)
        decoded = self._decode(image)
        cropped = self._crop(decoded, region)
        image_hash = self._pixel_hash(cropped)
        previous_hash = self._previous_hash_by_session.get(session_id)
        changed = previous_hash is not None and previous_hash != image_hash
        encoded = self._encode_png(cropped)
        height, width = cropped.shape[:2]

        frame = Frame(
            frame_id=uuid4().hex,
            session_id=session_id,
            captured_at=captured_at,
            image_hash=image_hash,
            width=width,
            height=height,
            changed_since_previous=changed,
            storage_reference=storage_reference,
        )
        self._previous_hash_by_session[session_id] = image_hash
        self._last_capture_at_by_session[session_id] = captured_at
        return CapturedFrame(frame=frame, image=encoded)

    @staticmethod
    def _decode(image: bytes) -> np.ndarray:
        if not image:
            raise ValueError("image must not be empty")
        array = np.frombuffer(image, dtype=np.uint8)
        decoded = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("image bytes could not be decoded")
        return decoded

    @staticmethod
    def _crop(image: np.ndarray, region: PixelRegion | None) -> np.ndarray:
        if region is None:
            return image.copy()
        height, width = image.shape[:2]
        if (
            region.x < 0
            or region.y < 0
            or region.width <= 0
            or region.height <= 0
            or region.right > width
            or region.bottom > height
        ):
            raise ValueError("capture region must be inside the decoded image")
        return image[region.y : region.bottom, region.x : region.right].copy()

    @staticmethod
    def _pixel_hash(image: np.ndarray) -> str:
        height, width = image.shape[:2]
        digest = sha256()
        digest.update(width.to_bytes(4, "big", signed=False))
        digest.update(height.to_bytes(4, "big", signed=False))
        digest.update(image.tobytes(order="C"))
        return digest.hexdigest()

    @staticmethod
    def _encode_png(image: np.ndarray) -> bytes:
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise ValueError("captured image could not be encoded")
        return encoded.tobytes()
