import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.models.candle import Candle
from app.domain.models.market_features import MarketCandleDirection
from app.domain.models.vision import CandleDirection
from app.domain.services.feature_engine import FeatureEngine

BASE = datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)


def _candle(*, close: Decimal, is_closed: bool) -> Candle:
    open_price = Decimal("100")
    return Candle(
        source_id="source-1",
        session_id="session-1",
        asset="TEST",
        timeframe="1m",
        open_time=BASE,
        close_time=BASE + timedelta(minutes=1),
        open=open_price,
        high=max(open_price, close) + Decimal("1"),
        low=min(open_price, close) - Decimal("1"),
        close=close,
        is_closed=is_closed,
    )


@pytest.mark.parametrize(
    ("close", "expected"),
    (
        (Decimal("101.25"), MarketCandleDirection.CLOSE_ABOVE_OPEN),
        (Decimal("98.75"), MarketCandleDirection.CLOSE_BELOW_OPEN),
        (Decimal("100"), MarketCandleDirection.CLOSE_EQUAL_OPEN),
    ),
)
def test_candle_direction_compares_decimal_close_to_open(
    close: Decimal, expected: MarketCandleDirection
) -> None:
    candle = _candle(close=close, is_closed=True)

    assert FeatureEngine.candle_direction(candle) is expected


def test_candle_direction_does_not_depend_on_is_closed() -> None:
    open_candle = _candle(close=Decimal("101.25"), is_closed=False)
    closed_candle = _candle(close=Decimal("101.25"), is_closed=True)

    assert FeatureEngine.candle_direction(open_candle) is MarketCandleDirection.CLOSE_ABOVE_OPEN
    assert FeatureEngine.candle_direction(closed_candle) is MarketCandleDirection.CLOSE_ABOVE_OPEN


def test_market_direction_enum_is_independent_from_visual_direction() -> None:
    assert tuple(member.value for member in CandleDirection) == ("UP", "DOWN")
    assert tuple(member.value for member in MarketCandleDirection) == (
        "CLOSE_ABOVE_OPEN",
        "CLOSE_BELOW_OPEN",
        "CLOSE_EQUAL_OPEN",
    )
    assert MarketCandleDirection is not CandleDirection


def test_phase5_direction_stays_domain_pure() -> None:
    feature_engine_path = (
        Path(__file__).resolve().parents[2] / "domain" / "services" / "feature_engine.py"
    )
    source = feature_engine_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    forbidden = {
        module
        for module in imported
        if module.startswith(
            (
                "sqlalchemy",
                "psycopg",
                "app.infrastructure",
                "app.domain.interfaces.storage_provider",
            )
        )
        or "replay" in module.lower()
        or "ground_truth" in module.lower()
    }

    assert forbidden == set()
    assert "StorageProvider" not in source
    assert "CandleRecord" not in source
    assert "CandleSnapshotRecord" not in source
    assert "ReplaySource" not in source
    assert "ground_truth" not in source.lower()
    assert "float" not in source
