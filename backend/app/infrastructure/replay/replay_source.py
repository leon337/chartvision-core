from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Sequence

from app.domain.models.candle import Candle


class ReplayStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    status: ReplayStatus
    position: int
    total: int
    current_time: datetime | None
    visible_candles: tuple[Candle, ...]


class ReplaySource:
    """Deterministic OHLC replay driven only by an explicit virtual clock."""

    def __init__(self, candles: Sequence[Candle]) -> None:
        self._candles = tuple(candles)
        self._validate_candles()
        self._position = 0
        self._current_time: datetime | None = None
        self._status = ReplayStatus.IDLE

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        *,
        source_id: str = "replay",
        session_id: str = "reference-replay",
    ) -> ReplaySource:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        asset = str(payload["asset"])
        timeframe = str(payload["timeframe"])

        if timeframe != "1m":
            raise ValueError("Replay MVP supports only the 1m timeframe")

        raw_candles = payload.get("candles")
        if not isinstance(raw_candles, list) or not raw_candles:
            raise ValueError("Replay dataset must contain at least one candle")

        candles: list[Candle] = []
        for raw in raw_candles:
            open_time = datetime.fromisoformat(str(raw["timestamp"]))
            if open_time.tzinfo is None:
                raise ValueError("Replay candle timestamps must include a timezone")

            open_price = Decimal(str(raw["open"]))
            high_price = Decimal(str(raw["high"]))
            low_price = Decimal(str(raw["low"]))
            close_price = Decimal(str(raw["close"]))

            if high_price < max(open_price, close_price):
                raise ValueError("Candle high cannot be below open or close")
            if low_price > min(open_price, close_price):
                raise ValueError("Candle low cannot be above open or close")

            candles.append(
                Candle(
                    source_id=source_id,
                    session_id=session_id,
                    asset=asset,
                    timeframe=timeframe,
                    open_time=open_time,
                    close_time=open_time + timedelta(minutes=1),
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    is_closed=True,
                    source_confidence=1.0,
                )
            )

        return cls(candles)

    @property
    def asset(self) -> str:
        return self._candles[0].asset

    @property
    def timeframe(self) -> str:
        return self._candles[0].timeframe

    @property
    def status(self) -> ReplayStatus:
        return self._status

    @property
    def position(self) -> int:
        return self._position

    @property
    def total(self) -> int:
        return len(self._candles)

    @property
    def current_time(self) -> datetime | None:
        return self._current_time

    @property
    def visible_candles(self) -> tuple[Candle, ...]:
        return self._candles[: self._position]

    @property
    def snapshot(self) -> ReplaySnapshot:
        return ReplaySnapshot(
            status=self._status,
            position=self._position,
            total=self.total,
            current_time=self._current_time,
            visible_candles=self.visible_candles,
        )

    def start(self) -> None:
        if self._status is ReplayStatus.FINISHED:
            return
        if self._current_time is None:
            self._current_time = self._candles[0].open_time
        self._status = ReplayStatus.RUNNING

    def pause(self) -> None:
        if self._status is ReplayStatus.RUNNING:
            self._status = ReplayStatus.PAUSED

    def resume(self) -> None:
        if self._status is ReplayStatus.PAUSED:
            self._status = ReplayStatus.RUNNING

    def stop(self) -> None:
        if self._status is not ReplayStatus.FINISHED:
            self._status = ReplayStatus.STOPPED

    def reset(self) -> None:
        self._position = 0
        self._current_time = None
        self._status = ReplayStatus.IDLE

    def advance(self, *, seconds: int = 60) -> tuple[Candle, ...]:
        if seconds <= 0:
            raise ValueError("Replay advance must be greater than zero seconds")
        if self._status is not ReplayStatus.RUNNING:
            return ()

        assert self._current_time is not None
        self._current_time += timedelta(seconds=seconds)

        start_position = self._position
        while (
            self._position < self.total
            and self._candles[self._position].close_time <= self._current_time
        ):
            self._position += 1

        released = self._candles[start_position : self._position]
        if self._position == self.total:
            self._status = ReplayStatus.FINISHED
        return released

    def _validate_candles(self) -> None:
        if not self._candles:
            raise ValueError("ReplaySource requires at least one candle")

        first = self._candles[0]
        previous_open_time: datetime | None = None
        for candle in self._candles:
            if candle.asset != first.asset or candle.timeframe != first.timeframe:
                raise ValueError("Replay candles must share asset and timeframe")
            if candle.timeframe != "1m":
                raise ValueError("Replay MVP supports only the 1m timeframe")
            if candle.open_time.tzinfo is None or candle.close_time.tzinfo is None:
                raise ValueError("Replay candle timestamps must include a timezone")
            if previous_open_time is not None and candle.open_time <= previous_open_time:
                raise ValueError("Replay candle timestamps must be strictly increasing")
            previous_open_time = candle.open_time
