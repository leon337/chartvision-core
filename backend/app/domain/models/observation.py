from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    session_id: str
    timestamp: datetime
    frame_id: str
    confidence: float
    visual_quality: float
