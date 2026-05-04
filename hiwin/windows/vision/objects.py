"""
windows/vision/objects.py
球體物件管理 + 模擬場景

依賴：cv2, config (BALL_DIAMETER)
輸出：cv2 繪圖 / get_all_data() → list[dict]
"""
import cv2
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class BilliardBall:
    """
    單一球體物件
    """

    def __init__(self, ball_type, u=0, v=0, real_diameter=None):
        self.type = ball_type
        self.u = float(u)
        self.v = float(v)
        d = real_diameter if real_diameter is not None else config.BALL_DIAMETER
        # 視覺半徑（pixel），約為 球徑*0.66/2，但可依解析度調整
        self.radius = int((d / 2) * 0.66)
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

    def draw(self, img):
        cv2.circle(img, (int(self.u), int(self.v)), self.radius, self.color, -1)
        label = self.type[0]  # "C", "T", "P"
        cv2.putText(img, label,
                    (int(self.u) - 5, int(self.v) - self.radius - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color, 1)


class SimulationScene:
    """
    管理畫面上所有模擬物件（球 + 口袋）
    """

    def __init__(self):
        self.balls = {}   # {"CUE_BALL": BilliardBall, ...}
        self._pockets = []  # [{"name": str, "u": float, "v": float}, ...]

    def set_pockets(self, pockets: dict):
        """
        設定口袋清單（校正完成後由 WSL 回傳）
        輸入：{"pocket_name": [u_pixel, v_pixel], ...}
        """
        self._pockets = [
            {"name": name, "u": float(uv[0]), "v": float(uv[1])}
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
        # 繪製口袋（在校正完成後自動有6個）
        for pkt in self._pockets:
            u, v = int(pkt["u"]), int(pkt["v"])
            color = (255, 255, 0)  # 青藍色
            cv2.circle(img, (u, v), 8, color, 2)
            # 顯示口袋名稱
            cv2.putText(img, pkt["name"].replace("_", "\n"), (u - 12, v - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

        # 繪製球體
        for ball in self.balls.values():
            ball.draw(img)

    def get_all_data(self):
        """
        格式化為 vision_data 格式（符合 protocol.py 定義）
        """
        return [
            {"type": b.type, "u": int(b.u), "v": int(b.v)}
            for b in self.balls.values()
        ]
