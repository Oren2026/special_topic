"""
lib/sim_table.py
模擬球檯幾何模型 - 資料類別

僅包含資料結構定義，不含物理計算邏輯。
"""

import math
from dataclasses import dataclass
from typing import List, Optional


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