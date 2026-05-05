"""
wsl/bank_shot_planner.py
Bank Shot 路徑規劃器

職責：
1. 檢測直線路徑是否被障礙球阻擋
2. 計算庫邊反彈點（單次反彈）
3. 計算 bank shot 的 ghost ball 位置
4. 比較 direct shot vs bank shot，選擇最佳路徑

依賴：math, config
輸出：compute_shot() → 直線或反彈策略結果
使用：strategy_module.py（可選調用）
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


class BankShotPlanner:
    """
    庫邊反彈路徑規劃

    幾何模型：
    - 球檯為矩形，左上角 (0,0)，右下角 (TABLE_WIDTH, TABLE_HEIGHT)
    - 庫邊：x=0（左）, x=TABLE_WIDTH（右）, y=0（上）, y=TABLE_HEIGHT（下）
    - 柺邊宽度：RAIL_WIDTH（緩衝區，反彈點不能太靠近角落）
    """

    def __init__(self, strategy):
        """
        strategy: BilliardStrategy 實例（用於取得 POCKETS 等資訊）
        """
        self.strategy = strategy
        self.table_w  = config.TABLE_WIDTH
        self.table_h  = config.TABLE_HEIGHT
        self.rail_w   = getattr(config, 'RAIL_WIDTH', 50)   # 庫邊緩衝
        self.ball_d   = config.BALL_DIAMETER

        # 柺邊範圍（去除角落緩衝區）
        self._left   = self.rail_w
        self._right  = self.table_w - self.rail_w
        self._top    = self.rail_w
        self._bottom = self.table_h - self.rail_w

    # ══════════════════════════════════════════════════════════════════
    # 公開 API
    # ══════════════════════════════════════════════════════════════════

    def compute_shot(self, cue_ball, target_ball, pocket_name, obstacles=None):
        """
        計算最佳擊球路徑。

        參數：
            cue_ball:     {"x": float, "y": float}  mm 座標
            target_ball:  {"x": float, "y": float}  mm 座標
            pocket_name:  str  目標口袋名稱
            obstacles:    list[dict] 額外障礙球 [{"x": float, "y": float}, ...]
                         （預設不包含 target_ball 本身）

        回傳：
            dict {
                "type": "direct" | "bank",
                "ghost": (gx, gy),          # ghost ball mm 座標
                "robot_tcp": (rx, ry),      # 手臂 TCP mm 座標
                "angle": float,             # 手臂 C 角（度）
                "stroke_dist": float,       # 衝程
                "is_reachable": bool,
                "reflection_point": (bx, by) | None,  # bank shot 時的柺邊觸碰點
                "rail": str | None,          # "left" | "right" | "top" | "bottom"
                "cue_to_ref_dist": float,   # 白球到反彈點的距離（bank shot）
                "ref_to_ghost_dist": float, # 反彈點到 ghost 的距離（bank shot）
            }
        """
        obstacles = obstacles or []

        # 1. 先檢查直線是否通暢
        ghost_direct = self._ghost_pos_direct(target_ball, pocket_name)
        if not self._is_path_blocked(cue_ball, ghost_direct, [target_ball] + obstacles):
            # 直線通暢 → 回傳 direct shot
            return self._build_direct_result(cue_ball, ghost_direct)

        # 2. 直線被阻擋 → 計算 bank shot
        bank_result = self._compute_bank_shot(cue_ball, target_ball, pocket_name, obstacles)
        return bank_result

    # ══════════════════════════════════════════════════════════════════
    # 內部：Ghost Ball 位置計算
    # ══════════════════════════════════════════════════════════════════

    def _ghost_pos_direct(self, target_ball, pocket_name):
        """計算直線 Ghost Ball：沿「目標球→口袋」方向延伸一個球徑"""
        pocket = self.strategy.POCKETS[pocket_name]
        tb_x, tb_y = target_ball['x'], target_ball['y']
        p_x,  p_y  = pocket[0], pocket[1]

        dx = tb_x - p_x
        dy = tb_y - p_y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return (tb_x, tb_y)

        gx = tb_x + (dx / dist) * self.ball_d
        gy = tb_y + (dy / dist) * self.ball_d
        return (round(gx, 2), round(gy, 2))

    def _ghost_pos_bank(self, target_ball, pocket_name, reflection_point, rail):
        """
        計算 Bank Shot Ghost Ball。

        幾何：
        - 路徑：cue → ref → ghost → target → pocket
        - ghost 在 target→pocket 延伸線上（與 direct 相同）
        - 差異在於 cue 是瞄準 ref 而非 ghost
        """
        pocket   = self.strategy.POCKETS[pocket_name]
        tb_x, tb_y = target_ball['x'], target_ball['y']
        p_x,  p_y  = pocket[0], pocket[1]

        dx = tb_x - p_x
        dy = tb_y - p_y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return (tb_x, tb_y)

        # Ghost 在 target→pocket 方向
        gx = tb_x + (dx / dist) * self.ball_d
        gy = tb_y + (dy / dist) * self.ball_d

        return (round(gx, 2), round(gy, 2))

    # ══════════════════════════════════════════════════════════════════
    # 內部：路徑阻擋檢測
    # ══════════════════════════════════════════════════════════════════

    def _is_path_blocked(self, from_pt, to_pt, obstacles):
        """
        檢查 from_pt→to_pt 線段是否被任何障礙球阻擋。
        使用「點到線段距離」判斷。

        障礙球半徑 = 球半徑（考慮球的大小）
        白球本身也有半徑，所以要預留緩衝。
        """
        for obs in obstacles:
            if self._dist_point_to_segment(obs, from_pt, to_pt) < self.ball_d:
                return True
        return False

    def _dist_point_to_segment(self, pt, seg_a, seg_b):
        """
        點 pt 到線段 AB 的最短距離。
        pt, seg_a, seg_b 都是 (x, y) tuple。
        """
        ax, ay = pt[0] - seg_a[0], pt[1] - seg_a[1]
        bx, by = pt[0] - seg_b[0], pt[1] - seg_b[1]
        ab_x, ab_y = seg_b[0] - seg_a[0], seg_b[1] - seg_a[1]

        ab_sq = ab_x * ab_x + ab_y * ab_y
        if ab_sq == 0:
            return math.hypot(ax, ay)

        t = max(0, min(1, (ax * ab_x + ay * ab_y) / ab_sq))
        proj_x = seg_a[0] + t * ab_x
        proj_y = seg_a[1] + t * ab_y

        return math.hypot(pt[0] - proj_x, pt[1] - proj_y)

    # ══════════════════════════════════════════════════════════════════
    # 內部：Bank Shot 計算
    # ══════════════════════════════════════════════════════════════════

    def _compute_bank_shot(self, cue_ball, target_ball, pocket_name, obstacles):
        """
        計算最佳單次庫邊反彈路徑。
        嘗試 4 條庫邊，返回最佳（最短白球移動距離）的可行路徑。
        """
        ghost = self._ghost_pos_direct(target_ball, pocket_name)

        candidates = []

        # 嘗試 4 條庫邊
        for rail in ["left", "right", "top", "bottom"]:
            ref = self._compute_reflection_point(cue_ball, ghost, rail)
            if ref is None:
                continue

            # 檢查：cue→ref 是否被阻擋（不含 target，排除 target 本身）
            obs_no_target = [o for o in obstacles]
            if self._is_path_blocked(
                (cue_ball['x'], cue_ball['y']),
                ref,
                obs_no_target
            ):
                continue

            # 檢查：ref→ghost 是否被阻擋
            if self._is_path_blocked(ref, ghost, [target_ball] + obstacles):
                continue

            # 計算 cue→ref 距離（越短越好）
            cue_to_ref = math.hypot(
                ref[0] - cue_ball['x'],
                ref[1] - cue_ball['y']
            )

            candidates.append({
                "rail": rail,
                "reflection_point": ref,
                "cue_to_ref_dist": cue_to_ref,
            })

        if not candidates:
            # 沒有可行的 bank shot → fallback 到 direct（即使被阻擋）
            return self._build_direct_result(cue_ball, ghost)

        # 選擇 cue→ref 距離最短者
        best = min(candidates, key=lambda c: c["cue_to_ref_dist"])

        # 建立 bank shot 結果
        return self._build_bank_result(
            cue_ball, ghost,
            best["reflection_point"],
            best["rail"],
            best["cue_to_ref_dist"]
        )

    def _compute_reflection_point(self, from_pt, to_pt, rail):
        """
        計算從 from_pt 瞄準 to_pt 時，在指定庫邊 rail 上的理論反射點。

        幾何：
        對 left/right 庫（垂直庫）：
          - 以庫邊為鏡像軸，取得 to_pt 的鏡像點 to_mirror
          - 連線 from_pt → to_mirror，與庫邊的交點即為反射點
        對 top/bottom 庫（水平庫）：
          - 以庫邊為鏡像軸，取得 to_pt 的鏡像點 to_mirror
          - 連線 from_pt → to_mirror，與庫邊的交點即為反射點

        反射服從：入射角 = 反射角
        這等價於「鏡像法」：從鏡像點看向 from_pt 的連線，與庫邊的交點
        """
        fx, fy = from_pt[0], from_pt[1]
        tx, ty = to_pt[0], to_pt[1]

        if rail == "left":
            # 鏡像：對 x=0 做鏡射 → tx_mirror = -tx
            tx_m = -tx
            ty_m = ty
            # 直線 from_pt → to_mirror 與 x=0 的交點
            if tx_m == fx:
                return None
            t = fx / (fx - tx_m)
            rx = 0
            ry = fy + t * (ty_m - fy)

        elif rail == "right":
            tx_m = 2 * self.table_w - tx
            ty_m = ty
            if tx_m == fx:
                return None
            t = (self.table_w - fx) / (tx_m - fx)
            rx = self.table_w
            ry = fy + t * (ty_m - fy)

        elif rail == "top":
            tx_m = tx
            ty_m = -ty
            if ty_m == fy:
                return None
            t = fy / (fy - ty_m)
            rx = fx + t * (tx_m - fx)
            ry = 0

        elif rail == "bottom":
            tx_m = tx
            ty_m = 2 * self.table_h - ty
            if ty_m == fy:
                return None
            t = (self.table_h - fy) / (ty_m - fy)
            rx = fx + t * (tx_m - fx)
            ry = self.table_h

        else:
            return None

        rx = round(rx, 2)
        ry = round(ry, 2)

        # 檢查反射點是否在有效範圍內（去除角落緩衝）
        if not self._is_ref_in_bounds(rx, ry, rail):
            return None

        return (rx, ry)

    def _is_ref_in_bounds(self, rx, ry, rail):
        """檢查反射點是否在有效庫邊範圍內（去除角落）"""
        if rail in ("left", "right"):
            return self._top <= ry <= self._bottom
        else:
            return self._left <= rx <= self._right

    # ══════════════════════════════════════════════════════════════════
    # 內部：結果建構
    # ══════════════════════════════════════════════════════════════════

    def _build_direct_result(self, cue_ball, ghost):
        """建構 direct shot 回傳結果"""
        gx, gy = ghost
        cx, cy = cue_ball['x'], cue_ball['y']

        dx = gx - cx
        dy = gy - cy
        dist_cg = math.hypot(dx, dy)
        if dist_cg == 0:
            ux, uy = 0, 0
        else:
            ux, uy = dx / dist_cg, dy / dist_cg

        total_offset = self.strategy.fixed_length + self.strategy.safe_gap
        rx = cx - ux * total_offset
        ry = cy - uy * total_offset

        stroke = self._calc_stroke(dist_cg)
        angle  = math.degrees(math.atan2(dy, dx))

        return {
            "type": "direct",
            "ghost": (gx, gy),
            "robot_tcp": (round(rx, 2), round(ry, 2)),
            "angle": round(angle, 2),
            "stroke_dist": round(stroke, 2),
            "is_reachable": self._is_reachable(rx, ry),
            "reflection_point": None,
            "rail": None,
            "cue_to_ref_dist": 0,
            "ref_to_ghost_dist": dist_cg,
        }

    def _build_bank_result(self, cue_ball, ghost, ref_pt, rail, cue_to_ref_dist):
        """建構 bank shot 回傳結果"""
        gx, gy = ghost
        cx, cy = cue_ball['x'], cue_ball['y']
        rx_r, ry_r = ref_pt

        # Bank shot：手臂瞄準反射點
        dx = rx_r - cx
        dy = ry_r - cy
        dist_cr = math.hypot(dx, dy)
        if dist_cr == 0:
            ux, uy = 0, 0
        else:
            ux, uy = dx / dist_cr, dy / dist_cr

        total_offset = self.strategy.fixed_length + self.strategy.safe_gap
        tcp_x = cx - ux * total_offset
        tcp_y = cy - uy * total_offset

        # 從反射點到 ghost 的距離
        ref_to_ghost = math.hypot(gx - rx_r, gy - ry_r)

        stroke = self._calc_stroke(dist_cr + ref_to_ghost)
        angle  = math.degrees(math.atan2(dy, dx))

        return {
            "type": "bank",
            "ghost": (gx, gy),
            "robot_tcp": (round(tcp_x, 2), round(tcp_y, 2)),
            "angle": round(angle, 2),
            "stroke_dist": round(stroke, 2),
            "is_reachable": self._is_reachable(tcp_x, tcp_y),
            "reflection_point": ref_pt,
            "rail": rail,
            "cue_to_ref_dist": round(cue_to_ref_dist, 2),
            "ref_to_ghost_dist": round(ref_to_ghost, 2),
        }

    def _calc_stroke(self, total_dist):
        """根據白球總移動距離計算衝程"""
        base  = 100.0
        dynamic = total_dist * 0.05
        return min(base + dynamic, self.strategy.max_stroke)

    def _is_reachable(self, x, y):
        return math.hypot(x, y) <= self.strategy.ROBOT_MAX_REACH
