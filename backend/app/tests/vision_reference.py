import cv2
import numpy as np

from app.domain.models.vision import PixelRegion


CHART_REGION = PixelRegion(x=80, y=60, width=640, height=420)
PRICE_SCALE_X = CHART_REGION.x + CHART_REGION.width - 80
TIME_SCALE_Y = CHART_REGION.y + CHART_REGION.height - 40
EXPECTED_DIRECTIONS = ("UP", "DOWN", "UP")


def _bgr(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return blue, green, red


def reference_chart_png(*, include_candles: bool = True, include_scale: bool = True) -> bytes:
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

    if include_scale:
        cv2.line(image, (PRICE_SCALE_X, y), (PRICE_SCALE_X, y + height - 1), _bgr("#334155"), 1)
        cv2.line(image, (x, TIME_SCALE_Y), (PRICE_SCALE_X, TIME_SCALE_Y), _bgr("#334155"), 1)
    cv2.rectangle(image, (x, y), (x + width - 1, y + height - 1), _bgr("#334155"), 1)

    if include_scale:
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

    if include_candles:
        candles = (
            (x + 150, y + 120, y + 205, y + 145, y + 180, "#22c55e"),
            (x + 285, y + 105, y + 235, y + 140, y + 195, "#ef4444"),
            (x + 420, y + 165, y + 300, y + 210, y + 250, "#22c55e"),
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


def checkerboard_png() -> bytes:
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    tile = 16
    for y in range(0, image.shape[0], tile):
        for x in range(0, image.shape[1], tile):
            if (x // tile + y // tile) % 2:
                image[y : y + tile, x : x + tile] = (255, 255, 255)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()
