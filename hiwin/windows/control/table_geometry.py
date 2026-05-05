"""
windows/control/table_geometry.py
球檯幾何計算層 — Phase 1

職責：
- 根據校正矩陣，計算檯面上任意物件的真實尺寸
- 提供：球徑pixel估算、HoughCircles半徑範圍、比例尺
- 與 camera 解析度完全解耦

邏輯：
- 校正後：4角點確立了 pixel↔mm 映射
- 球檯 1200×630mm 為真實基準
- 任何 pixel 測量都可以轉換為 mm
"""

import numpy as np
from typing import Tuple, Optional


class TableGeometry:
    """
    球檯幾何計算
    
    使用方式：
    1. set_calibration(calibration_control) — 注入校正
    2. 呼叫各項計算方法
    """

    # 球檯真實尺寸（mm）
    TABLE_WIDTH_MM = 1200
    TABLE_HEIGHT_MM = 630
    BALL_DIAMETER_MM = 38
    BALL_RADIUS_MM = BALL_DIAMETER_MM / 2  # 19mm

    def __init__(self):
        self._calibration = None

    def set_calibration(self, calib) -> None:
        """
        注入校正控制（CalibrationControl 實例）
        
        所需方法：
        - is_valid() → bool
        - pixel_to_mm(u, v) → (x_mm, y_mm)
        - mm_to_pixel(x_mm, y_mm) → (u, v)
        - get_points() → [[u1,v1], ...]
        """
        self._calibration = calib

    # ── 比例尺（pixel ↔ mm）────────────────────────────────────────────────

    def scale_x(self) -> float:
        """
        計算 X 方向（寬）比例尺：pixel → mm
        即：1 pixel = ? mm
        """
        if self._calibration is None or not self._calibration.is_valid():
            return 1.0  # fallback：未校正
        
        # 取球檯寬度方向（左右兩角）來算比例尺
        pts = self._calibration.get_points()
        if len(pts) < 4:
            return 1.0
        
        # 左上→右上：球檯寬度方向
        pixel_width = np.linalg.norm(
            np.array(pts[1], dtype=float) - np.array(pts[0], dtype=float)
        )
        if pixel_width < 1:
            return 1.0
        
        return self.TABLE_WIDTH_MM / pixel_width

    def scale_y(self) -> float:
        """
        計算 Y 方向（高）比例尺：pixel → mm
        """
        if self._calibration is None or not self._calibration.is_valid():
            return 1.0
        
        pts = self._calibration.get_points()
        if len(pts) < 4:
            return 1.0
        
        # 右上→右下：球檯高度方向
        pixel_height = np.linalg.norm(
            np.array(pts[2], dtype=float) - np.array(pts[1], dtype=float)
        )
        if pixel_height < 1:
            return 1.0
        
        return self.TABLE_HEIGHT_MM / pixel_height

    def pixel_to_mm_2d(self, u: float, v: float) -> Tuple[float, float]:
        """pixel → mm（使用校正矩陣）"""
        if self._calibration and self._calibration.is_valid():
            return self._calibration.pixel_to_mm(u, v)
        # fallback：使用比例尺估算
        return (u * self.scale_x(), v * self.scale_y())

    # ── 球徑估算（HoughCircles 參數用）─────────────────────────────────────

    def expected_ball_radius_pixel(self) -> Tuple[float, float]:
        """
        根據校正估算球徑半徑（pixel）
        
        回傳：(min_radius, max_radius)
          - min_radius：最保守（小球在視角邊緣變形）
          - max_radius：最大（正上方觀看）
        
        計算：用 scale_x() 和 scale_y() 平均，再乘以球的 mm 半徑
        """
        scale = (self.scale_x() + self.scale_y()) / 2.0
        radius_mm = self.BALL_RADIUS_MM  # 19mm

        radius_pixel = radius_mm / scale if scale > 0 else 10.0

        # 浮動範圍：±30%（視角造成的大小變化）
        min_r = max(5.0, radius_pixel * 0.7)
        max_r = radius_pixel * 1.5

        return (min_r, max_r)

    def hough_radius_range(self) -> Tuple[int, int]:
        """
        回傳 HoughCircles 的 minRadius 和 maxRadius
        
        用於 BallIdentifier.detect_circles() 的參數注入
        """
        min_r, max_r = self.expected_ball_radius_pixel()
        return (int(min_r), int(max_r))

    # ── 幾何驗證 ─────────────────────────────────────────────────────────────

    def validate_calibration(self) -> Tuple[bool, str]:
        """
        驗證校正結果是否合理
        
        檢查：
        - 比例尺 X 和 Y 差異 < 30%（否則可能是透視變形過度）
        - 球徑預估在合理範圍（5-100 pixel）
        """
        if self._calibration is None or not self._calibration.is_valid():
            return False, "尚未校正"

        sx = self.scale_x()
        sy = self.scale_y()

        # 比例尺差異檢查（寬高比應該與 1200/630 接近）
        expected_ratio = self.TABLE_WIDTH_MM / self.TABLE_HEIGHT_MM  # ~1.905
        pixel_ratio = sx / sy if sy > 0 else 0
        ratio_diff = abs(pixel_ratio / expected_ratio - 1)

        if ratio_diff > 0.3:
            return False, f"校正變形過大（比例尺比 {pixel_ratio:.3f} vs 期望 {expected_ratio:.3f}）"

        min_r, max_r = self.expected_ball_radius_pixel()
        if max_r < 5 or min_r > 150:
            return False, f"球徑預估範圍異常 [{min_r:.0f}, {max_r:.0f}] px"

        return True, f"OK（1px = {sx:.2f}×{sy:.2f} mm）"

    # ── 常用計算 ─────────────────────────────────────────────────────────────

    def distance_pixel(self, u1: float, v1: float, u2: float, v2: float) -> float:
        """兩 pixel 點之間的距離（mm）"""
        du = u2 - u1
        dv = v2 - v1
        pixel_dist = (du**2 + dv**2) ** 0.5
        return pixel_dist * self.scale_x()  # 用 X 方向比例尺（差異小）

    def distance_mm(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """兩 mm 點之間的歐氏距離"""
        return ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5

    def ball_to_pocket_mm(self, ball_x: float, ball_y: float,
                           pocket_x: float, pocket_y: float) -> float:
        """球到口袋的 mm 距離（幾何規劃用）"""
        return self.distance_mm(ball_x, ball_y, pocket_x, pocket_y)
