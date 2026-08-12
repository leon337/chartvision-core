from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.candle import Candle
from app.infrastructure.replay.exposure_tracked_replay import ExposureTrackedReplay
from app.infrastructure.replay.replay_source import ReplaySource, ReplayStatus

T0 = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def _candles() -> tuple[Candle, ...]:
    candles = []
    for index in range(8):
        open_time = T0 + timedelta(minutes=index)
        price = Decimal(100 + index)
        candles.append(
            Candle(
                source_id="replay",
                session_id="session-1",
                asset="SAMPLE",
                timeframe="1m",
                open_time=open_time,
                close_time=open_time + timedelta(minutes=1),
                open=price,
                high=price,
                low=price,
                close=price,
                is_closed=True,
            )
        )
    return tuple(candles)


class FakeExposureStorage:
    def __init__(self, watermark: datetime) -> None:
        self.watermark = watermark
        self.recorded: list[datetime] = []

    def record_session_exposure(self, session_id: str, exposed_at: datetime):
        assert session_id == "session-1"
        self.recorded.append(exposed_at)
        if exposed_at > self.watermark:
            self.watermark = exposed_at


def _tracked():
    storage = FakeExposureStorage(T0)
    source = ReplaySource(_candles())
    return ExposureTrackedReplay(
        session_id="session-1",
        replay_source=source,
        storage=storage,
    ), source, storage


def test_reset_rewinds_cursor_but_never_exposure_watermark() -> None:
    tracked, source, storage = _tracked()
    tracked.start()
    tracked.advance(seconds=180)
    assert source.current_time == T0 + timedelta(minutes=3)
    assert storage.watermark == T0 + timedelta(minutes=3)

    tracked.reset()
    assert source.current_time is None
    assert source.status is ReplayStatus.IDLE
    assert storage.watermark == T0 + timedelta(minutes=3)

    tracked.start()
    tracked.advance(seconds=60)
    assert source.current_time == T0 + timedelta(minutes=1)
    assert storage.watermark == T0 + timedelta(minutes=3)

    tracked.advance(seconds=240)
    assert source.current_time == T0 + timedelta(minutes=5)
    assert storage.watermark == T0 + timedelta(minutes=5)


def test_pause_resume_and_stop_do_not_reduce_exposure() -> None:
    tracked, source, storage = _tracked()
    tracked.start()
    tracked.advance(seconds=120)
    watermark = storage.watermark

    tracked.pause()
    assert source.status is ReplayStatus.PAUSED
    assert storage.watermark == watermark
    tracked.resume()
    assert storage.watermark == watermark
    tracked.stop()
    assert source.status is ReplayStatus.STOPPED
    assert storage.watermark == watermark


def test_repeated_reset_cycles_keep_single_monotonic_history() -> None:
    tracked, _, storage = _tracked()
    tracked.start()
    tracked.advance(seconds=240)
    first_max = storage.watermark

    for _ in range(3):
        tracked.reset()
        tracked.start()
        tracked.advance(seconds=60)
        assert storage.watermark == first_max


def test_start_records_deterministic_origin_before_first_advance() -> None:
    tracked, source, storage = _tracked()
    tracked.start()

    assert source.current_time == T0
    assert storage.recorded == [T0]
    assert storage.watermark == T0
