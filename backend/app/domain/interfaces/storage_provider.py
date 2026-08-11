from datetime import datetime
from typing import Protocol

from app.domain.models.analysis import Analysis
from app.domain.models.candle import Candle
from app.domain.models.frame import Frame
from app.domain.models.observation import Observation
from app.domain.models.session import Session


class SessionConflictError(ValueError):
    """Raised when an existing session identity has conflicting persisted data."""


class FrameConflictError(ValueError):
    """Raised when an existing frame identity has conflicting persisted data."""


class ObservationConflictError(ValueError):
    """Raised when an existing observation identity has conflicting persisted data."""


class CandleConflictError(ValueError):
    """Raised when persisted candle history would be mutated inconsistently."""


class AnalysisConflictError(ValueError):
    """Raised when an existing analysis identity has conflicting persisted data."""


class StorageProvider(Protocol):
    def healthcheck(self) -> bool: ...

    def save_session(self, session: Session) -> None: ...

    def get_session(self, session_id: str) -> Session | None: ...

    def save_frame(self, frame: Frame) -> None: ...

    def get_frame(self, frame_id: str) -> Frame | None: ...

    def save_observation(self, observation: Observation) -> None: ...

    def get_observation(self, observation_id: str) -> Observation | None: ...

    def save_candle(self, candle: Candle, *, observation_id: str) -> None: ...

    def get_candle(self, session_id: str, open_time: datetime) -> Candle | None: ...

    def get_candles_for_frame(self, frame_id: str) -> tuple[Candle, ...]: ...

    def get_candles_as_of(self, session_id: str, as_of: datetime) -> tuple[Candle, ...]: ...

    def save_analysis(self, analysis: Analysis) -> None: ...

    def get_analysis(self, analysis_id: str) -> Analysis | None: ...
