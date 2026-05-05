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

# Bank Shot Planner（延遲匯入，避免循環依賴）
from bank_shot_planner import BankShotPlanner


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

        # 口袋座標（mm）— 位置需與實際球檯對齊
        #
        # ⚠️ 注意：TABLE_WIDTH/TABLE_HEIGHT 是球檯外框尺寸（包含庫邊）
        # 口袋位於庫邊內側，實際座標需由「口袋直徑」與「庫邊夾角」推算
        #
        # 待確認項目（#2）：
        #   - 口袋直徑（洞口 actual diameter）
        #   - 口袋開口夾角（corner pocket 兩庫邊夾角 ≠ 90°）
        # 實地測量後更新以下座標（目前假設口袋在檯面內側邊緣中心）
        self.POCKETS = {
            # 4角袋（庫邊轉角處）
            "top_left":   (-600,   0),
            "top_right":  ( 600,   0),
            "bot_left":   (-600, config.TABLE_HEIGHT),
            "bot_right":  ( 600, config.TABLE_HEIGHT),
            # 2側袋（長邊中央）
            "side_left":  (   0,   0),    # ⚠️ 待驗證
            "side_right": (   0, config.TABLE_HEIGHT),  # ⚠️ 待驗證
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

    def compute_shot(self, cue_ball, target_ball, pocket_name, obstacles=None):
        """
        增強版擊球計算（自動選擇 direct 或 bank shot）。

        當障礙球存在且阻擋直線路徑時，自動計算庫邊反彈。
        等同於 get_best_shot，但多一層 bank shot 能力。

        參數：
            cue_ball:    {"x": float, "y": float}
            target_ball: {"x": float, "y": float}
            pocket_name: str
            obstacles:   list[dict] [{"x": float, "y": float}, ...]
                        若為空或 None，相當於 get_best_shot

        回傳：與 BankShotPlanner.compute_shot() 相同格式
             額外包含 "shot_type": "direct" | "bank"
        """
        planner = BankShotPlanner(self)
        return planner.compute_shot(cue_ball, target_ball, pocket_name, obstacles)

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
