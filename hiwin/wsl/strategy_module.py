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

        # 口袋座標（mm）— 使用者指定
        #
        # 原點 (0,0) = 球檯幾何左下角（不是手臂原點）
        # 口袋位置 = 洞口中心，直徑 50mm
        # 手臂原點大約在 (600, -50)
        #
        # 上排口袋：y = 580（距頂部邊緣約 50mm）
        # 下排口袋：y =  50（距底部邊緣約 50mm）
        # 左排：x =  50（距左側邊緣約 50mm）
        # WSL 端已廢除左上角原點，改用 SimTable 長邊中點原點
        # SimTable: X ∈ [-600, +600], Y ∈ [0, 630]
        # 長邊（1200mm）在上下側，短邊（630mm）在左右側
        # 角落口袋含倒角效應（cx_corner=pr×0.3=7.5mm），與 SimTable 同步
        self.POCKETS = {
            # 角落口袋（4個）：洞口徑 50mm，含倒角偏移
            "top_left":   (-578.5,  53.5),
            "top_right":  ( 578.5,  53.5),
            "bot_left":   (-578.5, 576.5),
            "bot_right":  ( 578.5, 576.5),
            # 側邊口袋（2個）：長邊中點，洞口在 rail 邊緣
            "side_left":  (-575.0, 315.0),
            "side_right": ( 575.0, 315.0),
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
        """計算鬼球座標：沿「口袋→目標球」方向，在目標球前方一個球徑

        G = T + normalize(P - T) × BALL_DIAMETER
        （不是 T-P，那是往反方向）
        """
        tp = self.POCKETS[pocket_name]
        tb = (target_ball['x'], target_ball['y'])
        # 從口袋到目標球的方向
        dx = tp[0] - tb[0]
        dy = tp[1] - tb[1]
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
