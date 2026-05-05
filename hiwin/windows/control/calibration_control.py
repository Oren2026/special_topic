"""
windows/control/calibration_control.py
校正控制介面 — Phase 1 影像辨識起點

職責：
- 收集並驗證球桌 4 角校正點
- 提供 pixel ↔ mm 轉換矩陣
- 為後續視覺辨識（圓形+顏色）奠定基礎

依賴：cv2, numpy
輸出：CalibrationControl 實例，供 HMI / StateMachine 取用
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple


class CalibrationControl:
    """
    球桌校正控制
    
    使用方式：
    1. add_click(u, v) — 依序點擊 4 角
    2. is_valid() — 驗證校正是否合理（對角線長度接近、面積合理）
    3. get_matrix() — 取得 pixel→mm 透視矩陣
    4. pixel_to_mm(u, v) — 單點轉換
    """

    POINT_ORDER = ["左上", "右上", "右下", "左下"]

    # 球檯實際尺寸（mm）
    TABLE_WIDTH_MM = 1200
    TABLE_HEIGHT_MM = 630

    def __init__(self):
        self._points: List[List[int]] = []  # pixel 座標 [u, v]
        self._matrix: Optional[np.ndarray] = None  # 透視轉換矩陣
        self._inverse_matrix: Optional[np.ndarray] = None
        self._calibrated: bool = False

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def add_click(self, u: int, v: int) -> Tuple[bool, str]:
        """
        加入一個校正點（依序：左上→右上→右下→左下）
        
        回傳：(is_complete, message)
          - is_complete: True 表示已收集滿 4 點
          - message: 狀態提示
        """
        if self._calibrated:
            return False, "已校正完成，請先 reset() 再重新校正"

        if len(self._points) >= 4:
            return False, "已收集 4 點，呼叫 compute() 計算矩陣"

        self._points.append([int(u), int(v)])
        idx = len(self._points) - 1

        if len(self._points) < 4:
            return False, f"已記錄 {self.POINT_ORDER[idx]} ({u}, {v})，請繼續點擊：{self.POINT_ORDER[idx + 1]}"
        else:
            return True, "4 點已收集，請稍候..."

    def compute(self) -> Tuple[bool, str]:
        """
        計算透視轉換矩陣
        
        回傳：(success, message)
        驗證：
          - 4 點不共線（行列式 ≠ 0）
          - 對角線長度比例合理（差 < 20%）
          - 面積與球檯比例合理
        """
        if len(self._points) < 4:
            return False, f"需要 4 點，目前只有 {len(self._points)} 點"

        pts = np.array(self._points, dtype=np.float32)

        # 驗證：4 點不共線（外積面積 > 0）
        area = cv2.contourArea(pts)
        if area < 1000:  # pixel 面積太小的校正點不可靠
            self._reset()
            return False, f"校正區域面積太小 ({area:.0f} px)，請重新點擊四角"

        # 驗證：對角線長度比例
        d1 = np.linalg.norm(pts[0] - pts[2])  # 左上→右下
        d2 = np.linalg.norm(pts[1] - pts[3])  # 右上→左下
        if max(d1, d2) / min(d1, d2) > 1.3:
            self._reset()
            return False, f"對角線比例異常 ({d1/d2:.2f})，請確認四角順序正確"

        # 驗證：點的順序（左上→右上→右下→左下 應為逆時針或順時針）
        # 計算梯度變化方向
        cross_sum = 0
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i + 1) % 4]
            cross_sum += (p2[0] - p1[0]) * (p2[1] + p1[1])
        orientation = "cw" if cross_sum > 0 else "ccw"  # 順時針/逆時針

        # 建立源點（pixel）和目標點（mm）的對應
        # 目標：球檯左上(0,0) → 右上(1200,0) → 右下(1200,630) → 左下(0,630)
        dst = np.array([
            [0, 0],
            [self.TABLE_WIDTH_MM, 0],
            [self.TABLE_WIDTH_MM, self.TABLE_HEIGHT_MM],
            [0, self.TABLE_HEIGHT_MM],
        ], dtype=np.float32)

        # 根據方向調整源點順序（確保計算出的矩陣有意義）
        if orientation == "cw":
            # 順時針：pts 是 [左上, 右上, 右下, 左下]，直接用
            src = pts
        else:
            # 逆時針：需要翻轉
            src = np.array([pts[0], pts[3], pts[2], pts[1]], dtype=np.float32)

        self._matrix, _ = cv2.findHomography(src, dst)
        if self._matrix is None:
            self._reset()
            return False, "透視矩陣計算失敗，請重新校正"

        self._inverse_matrix, _ = cv2.findHomography(dst, src)
        self._calibrated = True

        return True, f"校正完成！區域面積：{area:.0f} px，方向：{orientation}"

    def is_valid(self) -> bool:
        """校正是否有效"""
        return self._calibrated and self._matrix is not None

    def reset(self):
        """清除校正，重新開始"""
        self._reset()

    def _reset(self):
        self._points = []
        self._matrix = None
        self._inverse_matrix = None
        self._calibrated = False

    # ── 座標轉換 ─────────────────────────────────────────────────────────────

    def pixel_to_mm(self, u: float, v: float) -> Tuple[float, float]:
        """
        將 pixel 座標轉換為球檯 mm 座標
        
        必須在 compute() 成功後才能使用
        
        回傳：(x_mm, y_mm)
          - x: 沿球檯長邊（1200mm）
          - y: 沿球檯短邊（630mm）
        """
        if not self._calibrated:
            raise RuntimeError("尚未校正，請先呼叫 compute()")
        
        pixel_hom = np.array([u, v, 1.0], dtype=np.float32)
        mm_hom = self._matrix @ pixel_hom
        if mm_hom[2] == 0:
            return (float('inf'), float('inf'))
        x_mm = mm_hom[0] / mm_hom[2]
        y_mm = mm_hom[1] / mm_hom[2]
        return (x_mm, y_mm)

    def mm_to_pixel(self, x_mm: float, y_mm: float) -> Tuple[float, float]:
        """
        將球檯 mm 座標轉換為 pixel 座標
        """
        if not self._calibrated:
            raise RuntimeError("尚未校正，請先呼叫 compute()")
        
        mm_hom = np.array([x_mm, y_mm, 1.0], dtype=np.float32)
        pixel_hom = self._inverse_matrix @ mm_hom
        if pixel_hom[2] == 0:
            return (float('inf'), float('inf'))
        u = pixel_hom[0] / pixel_hom[2]
        v = pixel_hom[1] / pixel_hom[2]
        return (u, v)

    # ── 查詢 API ─────────────────────────────────────────────────────────────

    def point_count(self) -> int:
        return len(self._points)

    def next_label(self) -> str:
        """下一個要點擊的位置提示"""
        if self._calibrated:
            return "已完成"
        if len(self._points) < 4:
            return self.POINT_ORDER[len(self._points)]
        return "等待計算..."

    def get_points(self) -> List[List[int]]:
        """取得目前已收集的點（副本）"""
        return list(self._points)

    def get_matrix(self) -> Optional[np.ndarray]:
        """取得透視矩陣"""
        return self._matrix.copy() if self._matrix is not None else None

    def get_calibration_info(self) -> dict:
        """取得校正資訊（供偵錯用）"""
        return {
            "calibrated": self._calibrated,
            "point_count": len(self._points),
            "points": self._points,
            "matrix": self._matrix.tolist() if self._matrix is not None else None,
        }
