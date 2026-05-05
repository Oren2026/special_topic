"""
windows/control/calibration.py
校正點收集邏輯

功能：
- 收集球桌四角像素座標
- 計算 Homography 矩陣（pixel→mm）
- JSON 持久化（覆寫）

使用：StateMachine（INSTALL 模式）
"""

import cv2
import numpy as np
import json
import os


class CalibrationHandler:
    """
    收集球桌四角像素座標，計算 Homography，組裝校正封包
    """

    POINT_ORDER = ["左上", "右上", "右下", "左下"]

    TABLE_WIDTH_MM = 1200
    TABLE_HEIGHT_MM = 630

    def __init__(self):
        self._points = []
        self._matrix: np.ndarray = None
        self._inverse_matrix: np.ndarray = None
        self._calibrated = False

    # ── 點收集 ─────────────────────────────────────────────────────────

    def add_point(self, u, v) -> bool:
        """
        加入一個校正點
        回傳：是否已收集滿 4 點（4點即完成，並計算 Homography）
        """
        if len(self._points) >= 4:
            return True
        self._points.append([int(u), int(v)])
        if len(self._points) == 4:
            self._compute()
        return len(self._points) == 4

    def is_ready(self) -> bool:
        return len(self._points) == 4 and self._calibrated

    def point_count(self) -> int:
        return len(self._points)

    def next_label(self) -> str:
        """下一個要點擊的位置提示"""
        if len(self._points) < 4:
            return self.POINT_ORDER[len(self._points)]
        return "已完成"

    def get_points(self):
        """取得目前已收集的點（副本）"""
        return list(self._points)

    def get_packet(self) -> dict:
        """
        組裝校正封包（符合 protocol.py 定義）
        """
        return {
            "calibration_points": list(self._points)
        }

    def reset(self):
        """清除所有點，重新開始"""
        self._points = []
        self._matrix = None
        self._inverse_matrix = None
        self._calibrated = False

    # ── Homography 計算 ────────────────────────────────────────────────

    def _compute(self):
        """
        計算 Homography 矩陣（內部呼叫）
        驗證：對角線比例、面積、方向
        """
        pts = np.array(self._points, dtype=np.float32)

        # 驗證：面積
        area = cv2.contourArea(pts)
        if area < 1000:
            self._reset_state()
            return

        # 驗證：對角線比例
        d1 = np.linalg.norm(pts[0] - pts[2])  # 左上→右下
        d2 = np.linalg.norm(pts[1] - pts[3])  # 右上→左下
        if max(d1, d2) / min(d1, d2) > 1.3:
            self._reset_state()
            return

        # 方向（用於調整 src 順序）
        cross_sum = sum(
            (pts[(i + 1) % 4][0] - pts[i][0]) * (pts[(i + 1) % 4][1] + pts[i][1])
            for i in range(4)
        )
        orientation = "cw" if cross_sum > 0 else "ccw"

        # 目標：球檯 mm 座標（與 SimTable 座標系對齊）
        # SimTable 原點在長邊中點：X ∈ [-600, +600]，Y ∈ [0, 630]
        # POINT_ORDER = ["左上", "右上", "右下", "左下"]
        dst = np.array([
            [-600,   0],   # 左上
            [ 600,   0],   # 右上
            [ 600, 630],   # 右下
            [-600, 630],   # 左下
        ], dtype=np.float32)

        # 根據方向調整 src 順序
        if orientation == "cw":
            src = pts
        else:
            src = np.array([pts[0], pts[3], pts[2], pts[1]], dtype=np.float32)

        self._matrix, _ = cv2.findHomography(src, dst)
        if self._matrix is None:
            self._reset_state()
            return

        self._inverse_matrix, _ = cv2.findHomography(dst, src)
        self._calibrated = True

    def _reset_state(self):
        self._matrix = None
        self._inverse_matrix = None
        self._calibrated = False

    # ── 座標轉換 ──────────────────────────────────────────────────────

    def pixel_to_mm(self, u: float, v: float):
        """
        將 pixel 座標轉換為球檯 mm 座標
        只能在 compute() 成功後使用
        回傳：(x_mm, y_mm)
        """
        if not self._calibrated:
            raise RuntimeError("尚未校正")
        pixel_hom = np.array([u, v, 1.0], dtype=np.float32)
        mm_hom = self._matrix @ pixel_hom
        if mm_hom[2] == 0:
            return (float('inf'), float('inf'))
        return (mm_hom[0] / mm_hom[2], mm_hom[1] / mm_hom[2])

    def mm_to_pixel(self, x_mm: float, y_mm: float):
        """將球檯 mm 座標轉換為 pixel 座標"""
        if not self._calibrated:
            raise RuntimeError("尚未校正")
        mm_hom = np.array([x_mm, y_mm, 1.0], dtype=np.float32)
        pixel_hom = self._inverse_matrix @ mm_hom
        if pixel_hom[2] == 0:
            return (float('inf'), float('inf'))
        return (pixel_hom[0] / pixel_hom[2], pixel_hom[1] / pixel_hom[2])

    # ── JSON 持久化 ──────────────────────────────────────────────────

    def save_json(self, path: str) -> tuple:
        """
        將校正結果寫入 JSON（覆寫）
        回傳：(success: bool, message: str)
        """
        if not self._calibrated:
            return False, "尚未校正，無法儲存"

        data = {
            "calibrated": True,
            "points": self._points,
            "matrix": self._matrix.tolist() if self._matrix is not None else None,
            "inverse_matrix": (
                self._inverse_matrix.tolist()
                if self._inverse_matrix is not None else None
            ),
            "table_width_mm": self.TABLE_WIDTH_MM,
            "table_height_mm": self.TABLE_HEIGHT_MM,
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True, f"已儲存：{path}"
        except Exception as e:
            return False, f"儲存失敗：{e}"

    def load_json(self, path: str) -> tuple:
        """
        從 JSON 載入校正結果
        回傳：(success: bool, message: str)
        """
        if not os.path.exists(path):
            return False, f"檔案不存在：{path}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data.get("calibrated"):
                return False, "JSON 記錄為未校正狀態"
            self._points = data["points"]
            self._matrix = (
                np.array(data["matrix"], dtype=np.float64)
                if data.get("matrix") else None
            )
            self._inverse_matrix = (
                np.array(data["inverse_matrix"], dtype=np.float64)
                if data.get("inverse_matrix") else None
            )
            self._calibrated = True
            return True, f"已載入（{len(self._points)} 點）"
        except Exception as e:
            return False, f"載入失敗：{e}"

    def is_calibrated(self) -> bool:
        """校正是否有效"""
        return self._calibrated

    def get_matrix(self):
        """取得 Homography 矩陣（副本）"""
        return self._matrix.copy() if self._matrix is not None else None
