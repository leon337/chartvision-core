from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _reset() -> dict:
    response = client.post("/replay/reset")
    assert response.status_code == 200
    return response.json()


def test_replay_api_controls_and_future_data_gate() -> None:
    state = _reset()
    assert state["status"] == "idle"
    assert state["position"] == 0
    assert state["candles"] == []

    state = client.post("/replay/start").json()
    assert state["status"] == "running"
    assert state["position"] == 0

    state = client.post("/replay/advance", params={"seconds": 59}).json()
    assert state["position"] == 0
    assert state["candles"] == []

    state = client.post("/replay/advance", params={"seconds": 1}).json()
    assert state["position"] == 1
    assert len(state["candles"]) == 1

    state = client.post("/replay/pause").json()
    paused_time = state["current_time"]
    paused_position = state["position"]

    state = client.post("/replay/advance", params={"seconds": 120}).json()
    assert state["current_time"] == paused_time
    assert state["position"] == paused_position

    state = client.post("/replay/resume").json()
    assert state["status"] == "running"

    state = client.post("/replay/advance", params={"seconds": 60}).json()
    assert state["position"] == 2

    state = _reset()
    assert state["status"] == "idle"
    assert state["position"] == 0
    assert state["current_time"] is None
    assert state["candles"] == []


def test_replay_api_is_deterministic_after_reset() -> None:
    def run_once() -> list[dict]:
        _reset()
        client.post("/replay/start")
        sequence = []
        for _ in range(5):
            state = client.post("/replay/advance", params={"seconds": 60}).json()
            sequence.append(state["candles"][-1])
        return sequence

    assert run_once() == run_once()
