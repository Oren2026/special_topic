"""
lib/vision/
獨立視覺相關資料類（無硬體依賴）

params.py   — 視覺物理常數
objects.py  — BilliardBall, SimulationScene（cv2 繪圖）
"""

from .params import (
    TABLE_WIDTH,
    TABLE_HEIGHT,
    BALL_DIAMETER,
    BALL_RADIUS,
    POCKET_DIAMETER,
    POCKET_RADIUS,
    BALL_COLORS,
    DEFAULT_BALL_COLOR,
    TOP_CANVAS_W,
    TOP_CANVAS_H,
)
from .objects import BilliardBall, SimulationScene

__all__ = [
    "TABLE_WIDTH",
    "TABLE_HEIGHT",
    "BALL_DIAMETER",
    "BALL_RADIUS",
    "POCKET_DIAMETER",
    "POCKET_RADIUS",
    "BALL_COLORS",
    "DEFAULT_BALL_COLOR",
    "TOP_CANVAS_W",
    "TOP_CANVAS_H",
    "BilliardBall",
    "SimulationScene",
]