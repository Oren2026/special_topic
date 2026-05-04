"""
wsl/strategy_module.py
Ghost Ball 演算法 + 擊球可行性評估

依賴：math, config (ROBOT_MAX_REACH, FIXED_LENGTH, SAFE_GAP, MAX_STROKE, TABLE_*)
輸出：get_best_shot(cue_ball, target_ball, pocket_name) → dict
使用：robot_brain.py
"""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


class BilliardStrategy:
    """
    擊球策略：Ghost Ball 瞄點法
    """

    def __init__(self):
        self.D              = config.BALL_DIAMETER
        self.hole_D         = config.POCKET_DIAMETER
        self.fixed_length   = config.FIXED_LENGTH
        self.safe_gap       = config.SAFE_GAP
        self.max_stroke     = config.MAX_STROKE
        self.ROBOT_MAX_REACH = config.ROBOT_MAX_REACH

        self.POCKETS = {
            # 4角袋
            "top_left":   (-600,   0),
            "top_right":  ( 600,   0),
            "bot_left":   (-600, config.TABLE_HEIGHT),
            "bot_right":  ( 600, config.TABLE_HEIGHT),
            # 2側袋（長邊中央）— 9-ball 第5/6袋
            "side_left":  (   0,   0),
            "side_right": (   0, config.TABLE_HEIGHT),
        }

    def get_all_pockets_mm(self):
        """回傳所有口袋的 mm 座標（名稱, x, y）"""
        return {name: pos for name, pos in self.POCKETS.items()}

    def get_best_shot(self, cue_ball, target_ball, pocket_name="top_left"):
        """
        計算完整擊球參數：鬼球、手臂目標位、擊球角度與所需衝程

        cue_ball, target_ball: {"x": float, "y": float}（手臂毫米座標）
        回傳：{
            ghost: (gx, gy),
            robot_tcp: (rx, ry),
            angle: float,
            stroke_dist: float,
            is_reachable: bool,
        }
        """
        # 1. 計算鬼球位置
        gx, gy = self._ghost_pos(target_ball, pocket_name)

        # 2. 計算擊球向量（從白球指向鬼球）
        dx = gx - cue_ball['x']
        dy = gy - cue_ball['y']
        dist_cg = math.hypot(dx, dy)

        ux, uy = dx / dist_cg, dy / dist_cg  # 單位方向向量

        # 3. 計算手臂 TCP 停駐位置
        total_offset = self.fixed_length + self.safe_gap
        rx = cue_ball['x'] - ux * total_offset
        ry = cue_ball['y'] - uy * total_offset

        # 4. 計算所需衝程
        stroke_dist = self._calc_stroke(dist_cg)

        # 5. 計算手臂 C 角（度）
        angle = math.degrees(math.atan2(dy, dx))

        return {
            "ghost":        (round(gx, 2), round(gy, 2)),
            "robot_tcp":    (round(rx, 2), round(ry, 2)),
            "angle":        round(angle, 2),
            "stroke_dist":  round(stroke_dist, 2),
            "is_reachable": self._is_reachable(rx, ry),
        }

    # ── 內部 ────────────────────────────────────────────────────────────────

    def _ghost_pos(self, target_ball, pocket_name):
        """計算鬼球座標：沿「目標球→口袋」方向延伸一個球徑"""
        tp = self.POCKETS[pocket_name]
        tb = (target_ball['x'], target_ball['y'])
        dx = tb[0] - tp[0]
        dy = tb[1] - tp[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            return tb
        gx = tb[0] + (dx / dist) * self.D
        gy = tb[1] + (dy / dist) * self.D
        return round(gx, 2), round(gy, 2)

    def _calc_stroke(self, target_dist):
        """變量衝程邏輯：根據距離計算所需的加速行程"""
        base_stroke  = 100.0
        dynamic_add  = target_dist * 0.05
        return min(base_stroke + dynamic_add, self.max_stroke)

    def _is_reachable(self, x, y):
        """檢查點位是否在手臂工作範圍內"""
        return math.sqrt(x**2 + y**2) <= self.ROBOT_MAX_REACH
