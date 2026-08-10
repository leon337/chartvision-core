from typing import Protocol

from app.domain.models.frame import Frame
from app.domain.models.session import Session


class SessionConflictError(ValueError):
    """Raised when an existing session identity has conflicting persisted data."""


class FrameConflictError(ValueError):
    """Raised when an existing frame identity has conflicting persisted data."""


class StorageProvider(Protocol):
    def healthcheck(self) -> bool: ...

    def save_session(self, session: Session) -> None: ...

    def get_session(self, session_id: str) -> Session | None: ...

    def save_frame(self, frame: Frame) -> None: ...

    def get_frame(self, frame_id: str) -> Frame | None: ...
