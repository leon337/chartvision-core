from typing import Protocol

from app.domain.models.vision import VisionObservation


class VisionProvider(Protocol):
    def observe(self, image: bytes) -> VisionObservation: ...
