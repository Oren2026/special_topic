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

    def render_all(self, img):
        """
        根據 canvas 寬度計算比例尺，統一 render 口袋 + 球
        scale = canvas_width / TABLE_WIDTH → 真實世界比例
        """
        canvas_w = img.shape[1]
        scale = canvas_w / config.TABLE_WIDTH  # pixels per mm

        # 口袋（口徑 50mm → 半徑 25*scale pixels）
        pocket_radius = int((config.POCKET_DIAMETER / 2) * scale)
        for pkt in self._pockets:
            u, v = int(pkt["u"]), int(pkt["v"])
            color = (255, 255, 0)  # 青藍色
            cv2.circle(img, (u, v), pocket_radius, color, 2)
            # 名稱分兩行顯示（"top" 放上面，"left" 放下面）
            name_parts = pkt["name"].split("_")
            text = name_parts[0]
            cv2.putText(img, text, (u - pocket_radius, v - pocket_radius - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # 球（口徑 38mm → 半徑 19*scale pixels）
        for ball in self.balls.values():
            ball.draw(img, scale)

    def get_all_data(self):
        """
        格式化為 vision_data 格式（符合 protocol.py 定義）
        """
        return [
            {"type": b.type, "u": int(b.u), "v": int(b.v)}
            for b in self.balls.values()
        ]
