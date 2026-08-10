import cv2
import numpy as np

from app.tests.vision_reference import CHART_REGION, PRICE_SCALE_X, TIME_SCALE_Y, _bgr


CandleSpec = tuple[int, int, int, int, int, str]

FRAME1_CANDLES: tuple[CandleSpec, ...] = (
    (230, 180, 265, 205, 240, "#22c55e"),
    (365, 165, 295, 200, 255, "#ef4444"),
    (500, 225, 360, 270, 310, "#22c55e"),
)
FRAME2_CANDLES: tuple[CandleSpec, ...] = (
    (230, 180, 265, 205, 240, "#22c55e"),
    (365, 165, 295, 200, 255, "#ef4444"),
    (500, 205, 360, 250, 310, "#22c55e"),
)
FRAME3_CANDLES: tuple[CandleSpec, ...] = (
    (160, 180, 265, 205, 240, "#22c55e"),
    (295, 165, 295, 200, 255, "#ef4444"),
    (430, 205, 360, 250, 310, "#22c55e"),
    (565, 195, 330, 240, 300, "#ef4444"),
)


def phase3_chart_png(candles: tuple[CandleSpec, ...]) -> bytes:
    image = np.full((560, 800, 3), _bgr("#0b1020"), dtype=np.uint8)
    x, y, width, height = (
        CHART_REGION.x,
        CHART_REGION.y,
        CHART_REGION.width,
        CHART_REGION.height,
    )
    cv2.rectangle(image, (x, y), (x + width - 1, y + height - 1), _bgr("#0f172a"), -1)
    for grid_x in range(x + 70, PRICE_SCALE_X, 90):
        cv2.line(image, (grid_x, y), (grid_x, TIME_SCALE_Y), _bgr("#1e293b"), 1)
    for grid_y in range(y + 55, TIME_SCALE_Y, 55):
        cv2.line(image, (x, grid_y), (PRICE_SCALE_X, grid_y), _bgr("#1e293b"), 1)
    cv2.line(image, (PRICE_SCALE_X, y), (PRICE_SCALE_X, y + height - 1), _bgr("#334155"), 1)
    cv2.line(image, (x, TIME_SCALE_Y), (PRICE_SCALE_X, TIME_SCALE_Y), _bgr("#334155"), 1)
    cv2.rectangle(image, (x, y), (x + width - 1, y + height - 1), _bgr("#334155"), 1)

    for label_y, text in (
        (y + 80, "105"),
        (y + 180, "100"),
        (y + 280, "95"),
        (y + 380, "90"),
    ):
        cv2.putText(
            image,
            text,
            (PRICE_SCALE_X + 12, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            _bgr("#cbd5e1"),
            1,
            cv2.LINE_AA,
        )

    for center_x, high_y, low_y, body_top, body_bottom, color in candles:
        bgr = _bgr(color)
        cv2.line(image, (center_x, high_y), (center_x, low_y), bgr, 1)
        cv2.rectangle(
            image,
            (center_x - 5, body_top),
            (center_x + 5, body_bottom),
            bgr,
            -1,
        )

    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()
