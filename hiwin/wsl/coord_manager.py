"""
wsl/coord_manager.py
像素 ↔ 毫米座標轉換（透視變換）

依賴：numpy, cv2, config (TABLE_WIDTH, TABLE_HEIGHT, ROBOT_OFFSET_X, ROBOT_OFFSET_Y)
輸出：pixel_to_mm(u,v) / mm_to_pixel(x,y) / update_calibration(pts_src)
使用：robot_brain.py
"""
import numpy as np
import cv2
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


class CoordinateManager:
    def __init__(self):
        self.TABLE_WIDTH  = config.TABLE_WIDTH
        self.TABLE_HEIGHT = config.TABLE_HEIGHT
        self.OFFSET_X     = config.ROBOT_OFFSET_X
        self.OFFSET_Y     = config.ROBOT_OFFSET_Y

        self._M     = None   # 正向：pixel → mm
        self._M_inv = None   # 逆向：mm → pixel

    # ── 校正 ────────────────────────────────────────────────────────────────

    def update_calibration(self, pts_src):
        """
        一次性校正：接收 4 個像素點（左上/右上/右下/左下），
        計算正向與逆向透視矩陣
        """
        pts_dst = np.array([
            [0,              0             ],
            [self.TABLE_WIDTH, 0           ],
            [self.TABLE_WIDTH, self.TABLE_HEIGHT],
            [0,              self.TABLE_HEIGHT],
        ], dtype=np.float32)

        pts_src_arr = np.array(pts_src, dtype=np.float32)
        self._M     = cv2.getPerspectiveTransform(pts_src_arr, pts_dst)
        self._M_inv = np.linalg.inv(self._M)
        print("[CoordinateManager] 校正完成")
        return True

    def is_calibrated(self) -> bool:
        return self._M is not None

    # ── 轉換 ────────────────────────────────────────────────────────────────

    def pixel_to_mm(self, u, v):
        """
        像素 (u,v) → 手臂毫米座標 (arm_x, arm_y, is_calibrated)
        """
        if self._M is None:
            # Fallback：粗略線性映射
            arm_x = u * (self.TABLE_WIDTH / 800) - self.OFFSET_X
            arm_y = v * (self.TABLE_HEIGHT / 600)
            return arm_x, arm_y, False

        pt = np.array([[[float(u), float(v)]]], dtype=np.float32)
        real = cv2.perspectiveTransform(pt, self._M)[0][0]
        arm_x = real[0] - self.OFFSET_X
        arm_y = real[1] + self.OFFSET_Y
        return round(arm_x, 2), round(arm_y, 2), True

    def mm_to_pixel(self, arm_x, arm_y):
        """
        手臂毫米座標 (arm_x, arm_y) → 畫面像素 (u, v)
        """
        if self._M_inv is None:
            return int((arm_x + self.OFFSET_X) / (self.TABLE_WIDTH / 800)), \
                   int(arm_y / (self.TABLE_HEIGHT / 600))

        real_x = arm_x + self.OFFSET_X
        real_y = arm_y - self.OFFSET_Y
        pt = np.array([[[real_x, real_y]]], dtype=np.float32)
        pixel = cv2.perspectiveTransform(pt, self._M_inv)[0][0]
        return int(pixel[0]), int(pixel[1])

    # 向前相容別名
    convert = pixel_to_mm

    def get_pockets_pixel(self, pockets_mm: dict) -> dict:
        """
        將口袋 mm 座標轉為像素座標
        輸入：{"pocket_name": (x_mm, y_mm)}
        輸出：{"pocket_name": [u_pixel, v_pixel]}
        """
        return {
            name: list(self.mm_to_pixel(x, y))
            for name, (x, y) in pockets_mm.items()
        }
