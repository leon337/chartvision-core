from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    source_id: str
    asset: str
    timeframe: str
    started_at: datetime
    ended_at: datetime | None = None
