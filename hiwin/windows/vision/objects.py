"""
windows/vision/objects.py
球體物件管理 + 模擬場景

依賴：cv2, config (BALL_DIAMETER, POCKET_DIAMETER, TABLE_WIDTH, TOP_CANVAS_W)
輸出：cv2 繪圖 / get_all_data() → list[dict]

繪圖比例尺：
  scale = canvas_width / TABLE_WIDTH（像素/mm）
  球半徑 = (BALL_DIAMETER / 2) * scale
  口袋半徑 = (POCKET_DIAMETER / 2) * scale
  → 球與口袋真實比例 38:50 = 19:25
"""
import cv2
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class BilliardBall:
    """
    單一球體物件
    """

    def __init__(self, ball_type, u=0, v=0):
        self.type = ball_type
        self.u = float(u)
        self.v = float(v)
        self._diameter = config.BALL_DIAMETER
        self.color = self._set_color()

    def _set_color(self):
        colors = {
            "CUE_BALL":     (255, 255, 255),   # 白
            "TARGET_BALL":  (0,   255,   0),   # 綠
            "POCKET":       (255, 255,   0),   # 青藍
        }
        return colors.get(self.type, (0, 0, 255))

    def update_pos(self, u, v):
        self.u = float(u)
        self.v = float(v)

    def draw(self, img, scale):
        """
        根據比例尺在 img 上繪製本球
        scale = canvas_width / TABLE_WIDTH（pixels per mm）
        """
        radius = int((self._diameter / 2) * scale)
        cv2.circle(img, (int(self.u), int(self.v)), radius, self.color, -1)
        label = self.type[0]  # "C", "T", "P"
        cv2.putText(img, label,
                    (int(self.u) - 5, int(self.v) - radius - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color, 1)


class SimulationScene:
    """
    管理畫面上所有模擬物件（球 + 口袋）
    """

    def __init__(self):
        self.balls = {}   # {"CUE_BALL": BilliardBall, ...}
        self._pockets = []  # [{"name": str, "u": float, "v": float, "diameter": float}, ...]
        self._calib_points = []  # 校正4點（pixel），用於繪製 felt + rails

    def set_pockets(self, pockets: dict):
        """
        設定口袋清單（校正完成後由 WSL 回傳）
        輸入：{"pocket_name": [u_pixel, v_pixel], ...}
        """
        self._pockets = [
            {"name": name, "u": float(uv[0]), "v": float(uv[1]),
             "diameter": config.POCKET_DIAMETER}
            for name, uv in pockets.items()
        ]

    def add_or_update(self, ball_type, u, v):
        if ball_type not in self.balls:
            self.balls[ball_type] = BilliardBall(ball_type, u, v)
        else:
            self.balls[ball_type].update_pos(u, v)

    def get(self, ball_type):
        return self.balls.get(ball_type)

    def set_calibration_points(self, points):
        """
        注入 4 個校正點（pixel 座標），用於繪製球桌邊框
        呼叫一次即可，之後每次 render_all() 都會繪製 felt + rails
        """
        self._calib_points = points  # [[u1,v1], [u2,v2], [u3,v3], [u4,v4]]

    def render_all(self, img):
        """
        根據 canvas 寬度計算比例尺，統一 render 球桌邊框 + 口袋 + 球
        """
        canvas_w = img.shape[1]
        scale = canvas_w / config.TABLE_WIDTH  # pixels per mm

        # ── 球桌邊框（Felt + Rails）───────────────────────────────
        if self._calib_points and len(self._calib_points) == 4:
            self._draw_table_border(img)

        # 口袋（口徑 50mm → 半徑 25*scale pixels）
        pocket_radius = int((config.POCKET_DIAMETER / 2) * scale)
        for pkt in self._pockets:
            u, v = int(pkt["u"]), int(pkt["v"])
            color = (255, 255, 0)  # 青藍色
            cv2.circle(img, (u, v), pocket_radius, color, 2)
            name_parts = pkt["name"].split("_")
            text = name_parts[0]
            cv2.putText(img, text, (u - pocket_radius, v - pocket_radius - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # 球（口徑 38mm → 半徑 19*scale pixels）
        for ball in self.balls.values():
            ball.draw(img, scale)

    def _draw_table_border(self, img):
        """
        在 img 上繪製球桌邊框：felt（綠色） + rails（棕色） + 庫邊標線
        使用 4 個校正點構成的四邊形
        """
        pts = np.array(
            [[int(p[0]), int(p[1])] for p in self._calib_points],
            dtype=np.int32
        )

        # 外層：Rails（棕色，稍微擴大一點）
        rail_expand = 12  # pixel向外擴展
        center = pts.mean(axis=0).astype(int)
        rail_pts = center + (pts - center) * (1 + rail_expand / 200)
        rail_pts = np.clip(rail_pts, 0, [img.shape[1], img.shape[0]]).astype(np.int32)

        cv2.fillPoly(img, [rail_pts], (93, 64, 55))        # 棕色 rails
        cv2.polylines(img, [rail_pts], isClosed=True,
                      color=(60, 40, 25), thickness=2)     # rail 邊線

        # 中層：Felt（綠色，校正點構成的真實球桌區域）
        cv2.fillPoly(img, [pts], (46, 139, 87))           # 深綠 felt
        cv2.polylines(img, [pts], isClosed=True,
                      color=(30, 90, 50), thickness=1)     # felt 邊線

        # 內層：檯面格子輔助線（淡白色）
        # 僅在 felt 內部畫簡單的透視參考線
        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        overlay = img.copy()
        overlay[mask > 0] = (
            (img[mask > 0].astype(int) * 0.92 + np.array([30, 80, 30]) * 0.08)
            .astype(np.uint8)
        )
        img[mask > 0] = overlay[mask > 0]

        # 四角口袋：以校正點為基礎，根據口袋類型微調
        # 口袋用來覆蓋 felt 邊緣（角袋位於校正點附近）
        # 口袋本身由 render_all() 的 _pockets 繪製（統一尺寸）

    def get_all_data(self):
        """
        格式化為 vision_data 格式（符合 protocol.py 定義）
        """
        return [
            {"type": b.type, "u": int(b.u), "v": int(b.v)}
            for b in self.balls.values()
        ]
