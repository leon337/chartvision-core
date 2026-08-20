from datetime import datetime
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.replay import ExposureTrackedReplay, ReplaySessionFactory, ReplayStatus
from app.infrastructure.storage.phase7_outcome_postgres_repository import (
    Phase7OutcomePostgresStorageRepository,
)


DATASET_PATH = Path(__file__).resolve().parents[4] / "dataset" / "sample_replay.json"
_replay_session: ExposureTrackedReplay | None = None
_replay_init_lock = Lock()

router = APIRouter(prefix="/replay", tags=["replay"])


class ReplayCandleResponse(BaseModel):
    open_time: datetime
    close_time: datetime
    open: str
    high: str
    low: str
    close: str


class ReplayStateResponse(BaseModel):
    status: ReplayStatus
    asset: str
    timeframe: str
    position: int
    total: int
    current_time: datetime | None
    candles: list[ReplayCandleResponse]


def _get_replay_session() -> ExposureTrackedReplay:
    global _replay_session
    if _replay_session is None:
        with _replay_init_lock:
            if _replay_session is None:
                repository = Phase7OutcomePostgresStorageRepository(session_factory=SessionLocal)
                _replay_session = ReplaySessionFactory(repository).from_json(DATASET_PATH)
    return _replay_session


def _state_response() -> ReplayStateResponse:
    replay = _get_replay_session()
    snapshot = replay.snapshot
    candles = [
        ReplayCandleResponse(
            open_time=candle.open_time,
            close_time=candle.close_time,
            open=str(candle.open),
            high=str(candle.high),
            low=str(candle.low),
            close=str(candle.close),
        )
        for candle in snapshot.visible_candles
    ]
    return ReplayStateResponse(
        status=snapshot.status,
        asset=replay.asset,
        timeframe=replay.timeframe,
        position=snapshot.position,
        total=snapshot.total,
        current_time=snapshot.current_time,
        candles=candles,
    )


@router.get("", response_model=ReplayStateResponse)
def get_replay_state() -> ReplayStateResponse:
    return _state_response()


@router.post("/start", response_model=ReplayStateResponse)
def start_replay() -> ReplayStateResponse:
    _get_replay_session().start()
    return _state_response()


@router.post("/pause", response_model=ReplayStateResponse)
def pause_replay() -> ReplayStateResponse:
    _get_replay_session().pause()
    return _state_response()


@router.post("/resume", response_model=ReplayStateResponse)
def resume_replay() -> ReplayStateResponse:
    _get_replay_session().resume()
    return _state_response()


@router.post("/reset", response_model=ReplayStateResponse)
def reset_replay() -> ReplayStateResponse:
    _get_replay_session().reset()
    return _state_response()


@router.post("/advance", response_model=ReplayStateResponse)
def advance_replay(
    seconds: int = Query(default=60, gt=0, le=3600),
) -> ReplayStateResponse:
    _get_replay_session().advance(seconds=seconds)
    return _state_response()
