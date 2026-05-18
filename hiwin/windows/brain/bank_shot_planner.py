"""
windows/brain/bank_shot_planner.py
Bank Shot 路徑規規器

從 wsl/bank_shot_planner.py 移入，config 改為相對引用

職責：
1. 檢測直線路徑是否被障礙球阻擋
2. 計算庫邊反彈點（單次反彈）
3. 計算 bank shot 的 ghost ball 位置
4. 比較 direct shot vs bank shot，選擇最佳路徑

依賴：math, config
輸出：compute_shot() → 直線或反彈策略結果
使用：strategy_module.py
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
        計算最佳擊球路徑（自動選擇 direct 或 bank shot）。

        雙條件觸發 bank shot：
        Condition A: C → G 路徑被阻（母球到不了碰撞點）
        Condition B: T → P 路徑被阻（目標球進袋路線被堵）
        Bank shot：白球走 C → ref → G（瞄 ref，抵達時自然對準 G 碰撞）

        參數：
            cue_ball:     {"x": float, "y": float}  mm 座標
            target_ball:  {"x": float, "y": float}  mm 座標
            pocket_name:  str  目標口袋名稱
            obstacles:    list[dict] 額外障礙球 [{"x":, "y":}, ...]

        回傳：
            dict {
                "type": "direct" | "bank",
                "ghost": (gx, gy),           # 碰撞點（ghost ball）mm
                "robot_tcp": (rx, ry),       # 手臂 TCP mm
                "angle": float,              # 手臂 C 角（度）
                "stroke_dist": float,        # 衝程
                "is_reachable": bool,
                "reflection_point": (bx, by) | None,
                "rail": str | None,
                "cue_to_ref_dist": float,
                "ref_to_ghost_dist": float,
            }
        """
        obstacles = obstacles or []

        ghost = self._ghost_pos_direct(target_ball, pocket_name)

        if not self._is_bank_needed(cue_ball, ghost, target_ball, pocket_name, obstacles):
            return self._build_direct_result(cue_ball, ghost)

        bank_result = self._compute_bank_shot(
            cue_ball, ghost, target_ball, pocket_name, obstacles
        )
        return bank_result

    # ══════════════════════════════════════════════════════════════════
    # 內部：Ghost Ball 位置計算
    # ══════════════════════════════════════════════════════════════════

    def _ghost_pos_direct(self, target_ball, pocket_name):
        """計算 Ghost Ball：在 target ball 表面外側（口袋方向），半徑處

        G = T + normalize(P - T) × D
        """
        pocket = self.strategy.POCKETS[pocket_name]
        tb_x, tb_y = target_ball['x'], target_ball['y']
        p_x,  p_y  = pocket[0], pocket[1]

        dx = p_x - tb_x
        dy = p_y - tb_y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return (tb_x, tb_y)

        gx = tb_x + (dx / dist) * self.ball_d
        gy = tb_y + (dy / dist) * self.ball_d
        return (round(gx, 2), round(gy, 2))

    def _ghost_pos_bank(self, target_ball, pocket_name, reflection_point, rail):
        """
        Bank Shot Ghost Ball：與 direct 相同——G 的位置由 T 和 P 決定，不隨瞄點改變。
        """
        pocket   = self.strategy.POCKETS[pocket_name]
        tb_x, tb_y = target_ball['x'], target_ball['y']
        p_x,  p_y  = pocket[0], pocket[1]

        dx = p_x - tb_x
        dy = p_y - tb_y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return (tb_x, tb_y)

        gx = tb_x + (dx / dist) * self.ball_d
        gy = tb_y + (dy / dist) * self.ball_d

        return (round(gx, 2), round(gy, 2))

    # ══════════════════════════════════════════════════════════════════
    # 內部：障礙物 Filter
    # ══════════════════════════════════════════════════════════════════

    def _filtered_obstacles(self, cue_ball, target_ball, obstacles, exclude_pocket_pos=None):
        """
        根據角色過濾障礙物：
        - C（白球）在所有路徑上均 exempt
        - T（目標球）在 C→G、C→ref、ref→G 上 exempt；在 T→P 上也 exempt
        - 口袋 exempt
        - 其他球全部是障礙物
        """
        exempt_positions = [
            (cue_ball['x'],  cue_ball['y']),
            (target_ball['x'], target_ball['y']),
        ]
        if exclude_pocket_pos:
            exempt_positions.append(exclude_pocket_pos)

        result = []
        for obs in obstacles:
            ox, oy = obs['x'], obs['y']
            if (ox, oy) in exempt_positions:
                continue
            result.append(obs)
        return result

    # ══════════════════════════════════════════════════════════════════
    # 內部：路徑阻擋檢測
    # ══════════════════════════════════════════════════════════════════

    def _is_path_blocked(self, from_pt, to_pt, filtered_obstacles):
        """
        檢查 from_pt→to_pt 路徑上，filtered_obstacles 是否阻斷路線。
        雙層偵測（任一滿足即阻斷）：
        1. Ray-circle intersection
        2. Perpendicular distance < ball_d × 1.5
        """
        def to_tuple(pt):
            if isinstance(pt, dict):
                return (pt["x"], pt["y"])
            return pt

        from_t = to_tuple(from_pt)
        to_t   = to_tuple(to_pt)

        for obs in filtered_obstacles:
            obs_t = to_tuple(obs)

            hit_t = self._ray_circle_intersection_t(from_t, to_t, obs_t, self.ball_d)
            if hit_t is not None and 0 < hit_t < 1.0:
                return True

            dist = self._dist_point_to_segment(obs_t, from_t, to_t)
            if dist < self.ball_d * 1.5:
                return True

        return False

    def _ray_circle_intersection_t(self, ray_origin, ray_end, circle_center, radius):
        """求射線 [ray_origin → ray_end] 與半徑為 radius 的圓的最近交點參數 t"""
        dx = ray_end[0] - ray_origin[0]
        dy = ray_end[1] - ray_origin[1]
        fx = ray_origin[0] - circle_center[0]
        fy = ray_origin[1] - circle_center[1]

        a = dx * dx + dy * dy
        if a == 0:
            return None

        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - radius * radius

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None

        sqrt_d = math.sqrt(discriminant)
        t1 = (-b - sqrt_d) / (2 * a)
        t2 = (-b + sqrt_d) / (2 * a)

        candidates = [t for t in [t1, t2] if 0 < t < 1]
        if not candidates:
            return None
        return min(candidates)

    def _dist_point_to_segment(self, pt, seg_a, seg_b):
        """點 pt 到線段 AB 的最短距離"""
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
    # 內部：雙條件 Bank Shot Trigger
    # ══════════════════════════════════════════════════════════════════

    def _is_bank_needed(self, cue_ball, ghost, target_ball, pocket_name, obstacles):
        """
        雙條件 OR：任一滿足就觸發 bank shot 計算。
        Condition A: C → G（母球到碰撞點）被障礙物阻斷
        Condition B: T → P（目標球到口袋）被障礙物阻斷
        """
        pocket = self.strategy.POCKETS[pocket_name]

        filtered_A = self._filtered_obstacles(cue_ball, target_ball, obstacles)
        if self._is_path_blocked(cue_ball, ghost, filtered_A):
            return True

        filtered_B = self._filtered_obstacles(cue_ball, target_ball, obstacles)
        if self._is_path_blocked(target_ball, pocket, filtered_B):
            return True

        return False

    # ══════════════════════════════════════════════════════════════════
    # 內部：Bank Shot 計算
    # ══════════════════════════════════════════════════════════════════

    def _compute_bank_shot(self, cue_ball, ghost, target_ball, pocket_name, obstacles):
        """
        計算最佳單次庫邊反彈路徑（strict mode）。
        窮舉 4 條庫邊候選 ref 點，滿足以下全部條件才算可行：
          ① C → ref：路徑無障礙（排除 C, T）
          ② ref → G：路徑無障礙（排除 C, T）
          ③ ref 在有效庫邊範圍內
        選擇：C→ref 距離最短的可行方案。
        若四條庫邊都不可行，fallback direct shot。
        """
        pocket = self.strategy.POCKETS[pocket_name]
        candidates = []

        for rail in ["left", "right", "top", "bottom"]:
            ref = self._compute_reflection_point(cue_ball, ghost, rail)
            if ref is None:
                continue

            filtered = self._filtered_obstacles(cue_ball, target_ball, obstacles)

            if self._is_path_blocked(cue_ball, ref, filtered):
                continue

            if self._is_path_blocked(ref, ghost, filtered):
                continue

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
            return self._build_direct_result(cue_ball, ghost)

        best = min(candidates, key=lambda c: c["cue_to_ref_dist"])

        return self._build_bank_result(
            cue_ball, ghost,
            best["reflection_point"],
            best["rail"],
            best["cue_to_ref_dist"]
        )

    def _compute_reflection_point(self, from_pt, to_pt, rail):
        """
        計算從 from_pt 瞄準 to_pt 時，在指定庫邊 rail 上的理論反射點。
        幾何：鏡像法（入射角 = 反射角）
        """
        def to_tuple(pt):
            if isinstance(pt, dict):
                return (pt["x"], pt["y"])
            return pt

        fx, fy = to_tuple(from_pt)
        tx, ty = to_tuple(to_pt)

        if rail == "left":
            tx_m = -tx
            ty_m = ty
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