from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.infrastructure.replay import ReplaySource, ReplayStatus


DATASET_PATH = Path(__file__).resolve().parents[4] / "dataset" / "sample_replay.json"
replay_source = ReplaySource.from_json(DATASET_PATH)

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


def _state_response() -> ReplayStateResponse:
    snapshot = replay_source.snapshot
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
        asset=replay_source.asset,
        timeframe=replay_source.timeframe,
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
    replay_source.start()
    return _state_response()


@router.post("/pause", response_model=ReplayStateResponse)
def pause_replay() -> ReplayStateResponse:
    replay_source.pause()
    return _state_response()


@router.post("/resume", response_model=ReplayStateResponse)
def resume_replay() -> ReplayStateResponse:
    replay_source.resume()
    return _state_response()


@router.post("/reset", response_model=ReplayStateResponse)
def reset_replay() -> ReplayStateResponse:
    replay_source.reset()
    return _state_response()


@router.post("/advance", response_model=ReplayStateResponse)
def advance_replay(
    seconds: int = Query(default=60, gt=0, le=3600),
) -> ReplayStateResponse:
    replay_source.advance(seconds=seconds)
    return _state_response()
