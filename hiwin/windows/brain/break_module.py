"""
windows/brain/break_module.py
開球（Break）模組

從 wsl/break_module.py 移入，config 改為相對引用

開球與正常擊球不同：
  - 無需 Ghost Ball 計算
  - 無需目標球
  - 角度固定（朝球堆中央）
  - 力道固定（MAX_STROKE）

使用：robot_brain.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


class BreakStrategy:
    """
    開球策略
    計算：手臂 TCP 位置、擊球角度、擊球行程
    """

    def __init__(self):
        self.fixed_length  = config.FIXED_LENGTH
        self.safe_gap      = config.SAFE_GAP
        self.max_stroke    = config.MAX_STROKE
        self.table_width   = config.TABLE_WIDTH
        self.table_height  = config.TABLE_HEIGHT

    def compute_break(self, cue_ball_mm: dict) -> dict:
        """
        計算開球參數

        cue_ball_mm: {"x": float, "y": float}（手臂毫米座標）

        回傳：
            robot_tcp:    (rx, ry)       — 手臂 TCP 停駐位置（mm）
            angle:        float          — 擊球角度（度）
            stroke_dist:  float          — 擊球行程（mm）
            is_reachable: bool
        """
        cx = cue_ball_mm["x"]
        cy = cue_ball_mm["y"]

        # 開球角度：固定朝長邊 Y=table_height（球檯遠端 / 球堆方向）
        angle = 90.0

        # 單位方向向量（朝 Y+ 方向）
        ux, uy = 0.0, 1.0

        # TCP 位置：從白球沿擊球方向退後 fixed_length + safe_gap
        total_offset = self.fixed_length + self.safe_gap
        rx = cx - ux * total_offset
        ry = cy - uy * total_offset

        return {
            "robot_tcp":    (round(rx, 2), round(ry, 2)),
            "angle":        angle,
            "stroke_dist":  self.max_stroke,
            "is_reachable": self._is_reachable(rx, ry),
        }

    def _is_reachable(self, x: float, y: float) -> bool:
        """檢查點位是否在手臂工作範圍內"""
        import math
        return math.sqrt(x**2 + y**2) <= config.ROBOT_MAX_REACH