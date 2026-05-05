"""
windows/control/sim_table.py
模擬球檯幾何模型

用於：
1. 校正模式：虛擬球檯，驗證 4 角校正邏輯
2. 物理驗證：庫邊反彈、鬼球計算、擊球角度
3. COMPETE 前置測試：在無硬體環境下確認軟體邏輯

設計原則：
- 標準 9-foot 球檯比例
- 口袋位置由「洞口直徑」+「倒角」推算
- 所有物理計算都應該通過這個模型的驗證

洞口直徑參考：標準 9-foot 球檯約 1.75-2.0 inch ≈ 44-50mm
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class PocketSpec:
    """口袋規格"""
    name: str
    x_mm: float       # 手臂座標 x（已對齊原點）
    y_mm: float       # 手臂座標 y
    diameter: float    # 洞口直徑 mm
    chamfer_angle: float  # 倒角角度（度），兩庫邊的夾角
    # 洞口類型：corner（角落）, side（側袋）
    kind: str         # "corner" or "side"


class SimTable:
    """
    模擬球檯幾何模型

    座標系：手臂原點 (0,0) 在球檯長邊中點
    X軸：[-600, +600]（長邊）
    Y軸：[0, 630]（短邊）
    """

    # ── 球檯尺寸（外框，含庫邊）─────────────────────────────────────────────
    OUTER_WIDTH  = 1200   # mm
    OUTER_HEIGHT = 630    # mm

    # ── 庫邊標準（常規值，可調整）─────────────────────────────────────────
    # 標準 9-foot 球檯：rail 寬約 1.5-2.0 inch ≈ 38-51mm
    RAIL_WIDTH = 50.0    # mm（單側庫邊寬度）
    CUSHION_HEIGHT = 38.0  # 庫邊高度（橡膠墊高度）

    # ── 洞口直徑（標準值，容許±2mm誤差）─────────────────────────────────
    POCKET_DIAMETER = 50.0   # mm（標準 2 inch）
    CORNER_CHAMFER_ANGLE = 105.0  # 度（角落口袋兩庫邊夾角，常規 100-110°）
    SIDE_CHAMFER_ANGLE  = 90.0   # 度（側袋兩庫邊夾角，通常 90°）

    # ── 口袋位置（derived from 外框 - 庫邊）───────────────────────────────
    #  playable area = 外框 - 2×庫邊
    PLAYABLE_X_MIN = -580.0  # 原點對齊：長邊中點，故 ±580
    PLAYABLE_X_MAX =  580.0
    PLAYABLE_Y_MIN =   50.0  # 短邊兩側各留 50mm
    PLAYABLE_Y_MAX =  580.0

    # 口袋 x 座標：距長邊邊緣一個庫邊寬度
    POCKET_X_NEAR = -575.0   # 左側袋 x
    POCKET_X_FAR  =  575.0  # 右側袋 x

    # 口袋 y 座標：距短邊邊緣一個庫邊寬度
    POCKET_Y_EDGE =   50.0  # 上下兩側

    def __init__(self,
                 pocket_diameter: float = POCKET_DIAMETER,
                 rail_width: float = RAIL_WIDTH,
                 corner_angle: float = CORNER_CHAMFER_ANGLE,
                 side_angle: float = SIDE_CHAMFER_ANGLE):
        """
        模擬球檯建構式

        所有參數都可以在建立後調整（.update()）
        """
        self.pocket_diameter = pocket_diameter
        self.rail_width = rail_width
        self.corner_angle = corner_angle
        self.side_angle = side_angle

        # 計算內部 playable area
        self._compute_geometry()

    def _compute_geometry(self):
        """根據尺寸計算內部幾何"""
        half_rail = self.rail_width / 2

        # 口袋半徑
        pr = self.pocket_diameter / 2

        # ── 角落口袋 ────────────────────────────────────────────────────
        # 角落口袋位於：X=playable邊緣, Y=playable邊緣
        # 但洞口實際在「庫邊轉角處」，會稍微內縮
        cx_corner = pr * 0.3   # 洞口中心略向內（倒角效應）

        self.CORNER_POCKETS = [
            PocketSpec(
                name="top_left",
                x_mm=self.PLAYABLE_X_MIN + cx_corner,
                y_mm=self.PLAYABLE_Y_MIN + cx_corner,
                diameter=self.pocket_diameter,
                chamfer_angle=self.corner_angle,
                kind="corner",
            ),
            PocketSpec(
                name="top_right",
                x_mm=self.PLAYABLE_X_MAX - cx_corner,
                y_mm=self.PLAYABLE_Y_MIN + cx_corner,
                diameter=self.pocket_diameter,
                chamfer_angle=self.corner_angle,
                kind="corner",
            ),
            PocketSpec(
                name="bot_left",
                x_mm=self.PLAYABLE_X_MIN + cx_corner,
                y_mm=self.PLAYABLE_Y_MAX - cx_corner,
                diameter=self.pocket_diameter,
                chamfer_angle=self.corner_angle,
                kind="corner",
            ),
            PocketSpec(
                name="bot_right",
                x_mm=self.PLAYABLE_X_MAX - cx_corner,
                y_mm=self.PLAYABLE_Y_MAX - cx_corner,
                diameter=self.pocket_diameter,
                chamfer_angle=self.corner_angle,
                kind="corner",
            ),
        ]

        # ── 側邊口袋 ──────────────────────────────────────────────────
        # 側袋位於長邊中央，洞口在 rail 邊緣
        # Y 方向略內縮（倒角效應）
        cy_side = pr * 0.2

        self.SIDE_POCKETS = [
            PocketSpec(
                name="side_left",
                x_mm=self.POCKET_X_NEAR,
                y_mm=(self.OUTER_HEIGHT / 2) - cy_side,
                diameter=self.pocket_diameter,
                chamfer_angle=self.side_angle,
                kind="side",
            ),
            PocketSpec(
                name="side_right",
                x_mm=self.POCKET_X_FAR,
                y_mm=(self.OUTER_HEIGHT / 2) - cy_side,
                diameter=self.pocket_diameter,
                chamfer_angle=self.side_angle,
                kind="side",
            ),
        ]

        # ── 所有口袋 ──────────────────────────────────────────────────
        self.ALL_POCKETS = self.CORNER_POCKETS + self.SIDE_POCKETS
        self.POCKET_MAP = {p.name: p for p in self.ALL_POCKETS}

    def get_pocket(self, name: str) -> Optional[PocketSpec]:
        return self.POCKET_MAP.get(name)

    def get_all_pockets(self) -> List[PocketSpec]:
        return list(self.ALL_POCKETS)

    def get_pocket_mm(self, name: str) -> Optional[Tuple[float, float]]:
        p = self.POCKET_MAP.get(name)
        return (p.x_mm, p.y_mm) if p else None

    # ── 物理計算 ────────────────────────────────────────────────────────────

    def ghost_position(self, target_x: float, target_y: float,
                       pocket_name: str, ball_radius: float = 19.0) -> Tuple[float, float]:
        """
        計算 Ghost Ball 位置

        目標球→口袋方向，延伸 (球半徑 + 口袋半徑)

        注意：corner pocket 的 ghost ball 位置受倒角影響
        倒角越大，ghost ball 需要更靠外側才能進球
        """
        pocket = self.POCKET_MAP.get(pocket_name)
        if pocket is None:
            raise ValueError(f"Unknown pocket: {pocket_name}")

        dx = target_x - pocket.x_mm
        dy = target_y - pocket.y_mm
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return (target_x, target_y)

        # 標準 ghost ball 偏移
        offset = ball_radius + (pocket.diameter / 2)

        # corner pocket 倒角修正：偏移量需要根據口袋角度調整
        if pocket.kind == "corner":
            # 夾角越大（越平坦的角），ghost ball 越需要往外
            angle_factor = pocket.chamfer_angle / 90.0  # 標準化（90°=1.0）
            offset *= angle_factor

        gx = target_x + (dx / dist) * offset
        gy = target_y + (dy / dist) * offset
        return (round(gx, 2), round(gy, 2))

    def is_reachable(self, x: float, y: float, max_reach: float = 750.0) -> bool:
        """檢查座標是否在手臂工作範圍內"""
        return math.hypot(x, y) <= max_reach

    def is_on_table(self, x: float, y: float, ball_radius: float = 19.0) -> bool:
        """檢查球是否在球檯範圍內（playable area）"""
        margin = ball_radius
        return (self.PLAYABLE_X_MIN + margin <= x <= self.PLAYABLE_X_MAX - margin and
                self.PLAYABLE_Y_MIN + margin <= y <= self.PLAYABLE_Y_MAX - margin)

    def distance_to_pocket(self, x: float, y: float, pocket_name: str) -> float:
        """球心到口袋中心的 mm 距離"""
        px, py = self.get_pocket_mm(pocket_name)
        return math.hypot(x - px, y - py)

    def best_pocket_for(self, target_x: float, target_y: float) -> str:
        """
        找到對目標球最理想的口袋（直線可達、無遮擋）
        簡單版本：選距離最近的口袋
        """
        pockets = self.get_all_pockets()
        best = None
        best_dist = float('inf')
        for p in pockets:
            d = self.distance_to_pocket(target_x, target_y, p.name)
            if d < best_dist:
                best_dist = d
                best = p.name
        return best

    # ── 預設實例（供直接取用）─────────────────────────────────────────────

    @classmethod
    def default(cls) -> "SimTable":
        """預設模擬球檯（標準 9-foot 規格）"""
        return cls(
            pocket_diameter=50.0,
            rail_width=50.0,
            corner_angle=105.0,
            side_angle=90.0,
        )


# ── 預設全域實例 ──────────────────────────────────────────────────────────
DEFAULT_TABLE = SimTable.default()
