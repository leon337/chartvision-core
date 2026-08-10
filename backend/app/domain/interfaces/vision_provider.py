from typing import Protocol


class VisionProvider(Protocol):
    def observe(self, image: bytes) -> object: ...
