from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Frame:
    frame_id: str
    session_id: str
    captured_at: datetime
    image_hash: str
    width: int
    height: int
    changed_since_previous: bool
    storage_reference: str | None = None
