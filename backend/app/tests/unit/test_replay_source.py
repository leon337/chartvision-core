from datetime import datetime
from pathlib import Path

from app.infrastructure.replay import ReplaySource, ReplayStatus


DATASET_PATH = Path(__file__).resolve().parents[4] / "dataset" / "sample_replay.json"


def _replay_all(source: ReplaySource):
    source.start()
    released = []
    while source.status is not ReplayStatus.FINISHED:
        released.extend(source.advance(seconds=60))
    return released


def test_same_dataset_produces_same_sequence() -> None:
    first = ReplaySource.from_json(DATASET_PATH, session_id="run-a")
    second = ReplaySource.from_json(DATASET_PATH, session_id="run-a")

    assert _replay_all(first) == _replay_all(second)


def test_future_candle_is_hidden_until_close_time() -> None:
    source = ReplaySource.from_json(DATASET_PATH)

    source.start()
    assert source.current_time == datetime.fromisoformat("2026-01-05T14:30:00+00:00")
    assert source.visible_candles == ()

    assert source.advance(seconds=59) == ()
    assert source.visible_candles == ()

    released = source.advance(seconds=1)
    assert len(released) == 1
    assert released[0].open_time == datetime.fromisoformat("2026-01-05T14:30:00+00:00")
    assert len(source.visible_candles) == 1


def test_pause_freezes_clock_and_resume_continues_same_point() -> None:
    source = ReplaySource.from_json(DATASET_PATH)

    source.start()
    source.advance(seconds=30)
    source.pause()
    paused_time = source.current_time
    paused_position = source.position

    assert source.advance(seconds=120) == ()
    assert source.current_time == paused_time
    assert source.position == paused_position

    source.resume()
    released = source.advance(seconds=30)
    assert len(released) == 1
    assert source.current_time == datetime.fromisoformat("2026-01-05T14:31:00+00:00")


def test_reset_returns_to_initial_state_and_replays_identically() -> None:
    source = ReplaySource.from_json(DATASET_PATH)

    source.start()
    first_pass = source.advance(seconds=120)
    assert len(first_pass) == 2

    source.reset()
    assert source.status is ReplayStatus.IDLE
    assert source.position == 0
    assert source.current_time is None
    assert source.visible_candles == ()

    source.start()
    second_pass = source.advance(seconds=120)
    assert second_pass == first_pass


def test_finished_replay_exposes_only_dataset_sequence() -> None:
    source = ReplaySource.from_json(DATASET_PATH)

    sequence = _replay_all(source)

    assert len(sequence) == source.total == 5
    assert source.visible_candles == tuple(sequence)
    assert source.status is ReplayStatus.FINISHED
    assert source.advance(seconds=60) == ()
