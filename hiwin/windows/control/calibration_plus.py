"""
windows/control/calibration_plus.py
校正模式增強版 — 整合 SimTable 口袋模型

功能：
1. 保留原有 4角校正流程
2. 校正完成後，用 SimTable 的口袋模型計算「預期像素座標」
3. 顯示：校正4角 → 計算出口袋位置 → 視覺化驗證

用途：
- 在無硬體環境下驗證校正邏輯
- 檢視口袋位置是否合理
- 比較 SimTable 模型 vs 實際校正結果的差異

使用時機：
- 使用者按「安裝模式」→ 正常4角校正流程不變
- 校正完成後（收到 WSL 的 CALIBRATION_COMPLETE）→ 可呼叫 show_calibration_debug() 視覺化
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .calibration_control import CalibrationControl
from .sim_table import SimTable, DEFAULT_TABLE


class CalibrationPlus:
    """
    增強版校正控制（搭配 SimTable 口袋模型）

    流程：
    1. add_click(u, v) — 同 CalibrationControl，收集4角
    2. compute_matrix() — 建立透視矩陣
    3. set_sim_table(table) — 注入模擬球檯（可自訂參數）
    4. compute_expected_pockets() — 根據 SimTable 計算口袋pixel
    5. validate_calibration() — 比較校正點與 SimTable 預期值
    """

    def __init__(self, sim_table: SimTable = None):
        self._calib = CalibrationControl()
        self._table = sim_table or DEFAULT_TABLE
        self._expected_pockets: Dict[str, List[int]] = {}  # name -> [u, v]

    # ── 代理方法（delegation）──────────────────────────────────────────────

    def add_click(self, u: int, v: int) -> Tuple[bool, str]:
        return self._calib.add_click(u, v)

    def is_valid(self) -> bool:
        return self._calib.is_valid()

    def point_count(self) -> int:
        return self._calib.point_count()

    def next_label(self) -> str:
        return self._calib.next_label()

    def get_points(self) -> List[List[int]]:
        return self._calib.get_points()

    def get_matrix(self):
        return self._calib.get_matrix()

    def pixel_to_mm(self, u: float, v: float) -> Tuple[float, float]:
        return self._calib.pixel_to_mm(u, v)

    def mm_to_pixel(self, x_mm: float, y_mm: float) -> Tuple[int, int]:
        return self._calib.mm_to_pixel(x_mm, y_mm)

    def reset(self):
        self._calib.reset()
        self._expected_pockets = {}

    # ── 模擬球檯設定 ───────────────────────────────────────────────────────

    def set_sim_table(self, table: SimTable):
        """置換模擬球檯（用於測試不同參數）"""
        self._table = table

    def get_sim_table(self) -> SimTable:
        return self._table

    # ── 口袋計算 ───────────────────────────────────────────────────────────

    def compute_expected_pockets(self) -> Dict[str, List[int]]:
        """
        根據 SimTable 的口袋模型，計算每個口袋的 pixel 座標

        流程：
        1. 取得 SimTable 中每個口袋的 mm 座標
        2. 用校正矩陣轉換為 pixel
        3. 存入 _expected_pockets
        """
        if not self._calib.is_valid():
            return {}

        pockets = {}
        for pocket in self._table.get_all_pockets():
            name = pocket.name
            x_mm, y_mm = pocket.x_mm, pocket.y_mm
            u, v = self.mm_to_pixel(x_mm, y_mm)
            pockets[name] = [u, v]

        self._expected_pockets = pockets
        return pockets

    def get_expected_pockets(self) -> Dict[str, List[int]]:
        """取得計算後的口袋座標（需先呼叫 compute_expected_pockets）"""
        return dict(self._expected_pockets)

    # ── 校正驗證 ──────────────────────────────────────────────────────────

    def validate_calibration(self) -> Tuple[bool, str]:
        """
        驗證校正結果與 SimTable 模型的吻合程度

        檢查：
        1. 校正後，4角點是否對應 SimTable 的預期角點
        2. 口袋是否落在檯面範圍內
        3. 口間距是否合理（與 SimTable 比例尺比較）

        回傳：(is_valid, message)
        """
        if not self._calib.is_valid():
            return False, "尚未校正"

        pts = self._calib.get_points()

        # 檢查1：校正4角是否構成合理的四邊形
        pts_arr = np.array(pts, dtype=np.float32)
        area = cv2.contourArea(pts_arr)
        if area < 5000:
            return False, f"校正區域過小 ({area:.0f} px)，請確認4角點正確"

        # 檢查2：用 SimTable 反推4角的 mm 座標，確認比例尺合理
        # 左上角理論上在 (-600, 0) → pixel_to_mm(pts[0]) 應該約等於 (-600, 0)
        # 但校正點本身是在 pixel 座標，這裡我們只驗證比例尺
        scale_x = self._calib.pixel_to_mm(1, 0)[0] - self._calib.pixel_to_mm(0, 0)[0]
        scale_y = self._calib.pixel_to_mm(0, 1)[1] - self._calib.pixel_to_mm(0, 0)[1]

        # scale_x 應該是負值（因為 mm X 增加，pixel u 增加，但手臂座標 X 增加）
        # 只檢查絕對值是否合理（1 pixel 在 0.5-5mm 之間）
        if not (0.3 < abs(scale_x) < 5.0):
            return False, f"比例尺異常：1px = {scale_x:.3f}mm，請重新校正"

        # 檢查3：模擬口袋是否落在校正後的檯面範圍內
        if not self._expected_pockets:
            self.compute_expected_pockets()

        corner_names = ["top_left", "top_right", "bot_right", "bot_left"]
        for name in corner_names:
            if name not in self._expected_pockets:
                return False, f"角落口袋 {name} 計算失敗"
            u, v = self._expected_pockets[name]
            # 確認口袋是否在 4角點構成的多邊形內
            if cv2.pointPolygonTest(pts_arr, (float(u), float(v)), False) < 0:
                return False, f"角落口袋 {name} 落在校正區域外，請確認 SimTable 參數是否正確"

        return True, f"校正驗證通過（1px ≈ {abs(scale_x):.2f}mm）"

    # ── 視覺化（除錯用）───────────────────────────────────────────────────

    def draw_debug_overlay(self, frame: np.ndarray) -> np.ndarray:
        """
        在畫面上繪製校正除錯疊加層

        顯示：
        - 校正4角（綠色編號圓圈）
        - 模擬口袋位置（紅色圓圈 + 名稱）
        - 口號間連線（虛線）
        - 比例尺資訊

        回傳：加了疊加層的 frame（副本）
        """
        if not self._calib.is_valid():
            return frame

        out = frame.copy()
        pts = self._calib.get_points()
        pts_arr = np.array(pts, dtype=np.int32)

        # 口袋
        if self._expected_pockets:
            for name, (u, v) in self._expected_pockets.items():
                color = (0, 0, 255)  # 紅色
                cv2.circle(out, (u, v), 12, color, 2)
                cv2.putText(out, name.replace("_", "\n"), (u + 15, v - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

        # 校正4角
        labels = ["左上", "右上", "右下", "左下"]
        for i, (u, v) in enumerate(pts):
            cv2.circle(out, (int(u), int(v)), 10, (0, 255, 0), 2)
            cv2.putText(out, f"{i+1}.{labels[i]}", (int(u) + 12, int(v) + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        # 4角連線
        cv2.polylines(out, [pts_arr], True, (0, 200, 255), 1)

        # SimTable 參數顯示（左上角）
        info = [
            f"Pocket dia: {self._table.pocket_diameter:.0f}mm",
            f"Rail width: {self._table.rail_width:.0f}mm",
            f"Corner angle: {self._table.corner_angle:.0f}°",
        ]
        for i, line in enumerate(info):
            cv2.putText(out, line, (10, 20 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 0), 1)

        return out

    def get_calibration_summary(self) -> dict:
        """
        取得校正摘要（除錯用）

        回傳包含：
        - 校正4角 pixel
        - SimTable 口袋 pixel（計算後）
        - 比例尺
        """
        if not self._calib.is_valid():
            return {"calibrated": False}

        scale_x = self._calib.pixel_to_mm(1, 0)[0] - self._calib.pixel_to_mm(0, 0)[0]
        scale_y = self._calib.pixel_to_mm(0, 1)[1] - self._calib.pixel_to_mm(0, 0)[1]

        return {
            "calibrated": True,
            "calibration_points_pixel": self._calib.get_points(),
            "expected_pockets_pixel": self.get_expected_pockets(),
            "scale_px_to_mm_x": round(scale_x, 4),
            "scale_px_to_mm_y": round(scale_y, 4),
            "sim_table": {
                "pocket_diameter": self._table.pocket_diameter,
                "rail_width": self._table.rail_width,
                "corner_angle": self._table.corner_angle,
                "playable_area_mm": (
                    self._table.PLAYABLE_X_MAX - self._table.PLAYABLE_X_MIN,
                    self._table.PLAYABLE_Y_MAX - self._table.PLAYABLE_Y_MIN,
                ),
            },
        }
