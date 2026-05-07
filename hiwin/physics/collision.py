"""
physics/collision.py
純物理計算（stateless）

提供：
    BallState         — 球狀態 dataclass
    CollisionInfo      — 碰撞資訊 dataclass
    collision_detect   — 兩球是否碰撞
    resolve_elastic    — 等質量彈性碰撞速度計算
    reflect_wall       — 庫邊反彈速度修正
    table_bounds       — 球檯有效邊界
    is_in_pocket       — 球心是否在口袋內
"""

import math
from dataclasses import dataclass
from typing import Optional
from .parameters import (
    TABLE_WIDTH,
    TABLE_HEIGHT,
    RAIL_WIDTH,
    BALL_RADIUS,
    POCKET_RADIUS,
    RESTITUTION,
)


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class BallState:
    """球狀態：位置 (mm) + 速度 (mm/s)"""
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    radius: float = BALL_RADIUS

    def pos(self):
        return (self.x, self.y)

    def vel(self):
        return (self.vx, self.vy)


@dataclass
class CollisionInfo:
    """碰撞事件資料"""
    point: tuple[float, float]   # 碰撞點座標
    normal: tuple[float, float]  # 碰撞法向量（從 ball2 指向 ball1）
    distance: float              # 碰撞時球心距


# ── 球檯邊界 ────────────────────────────────────────────────────────────────

def table_bounds():
    """球檯有效邊界（不含角落緩衝區）

    回傳：(left, right, top, bottom)
    """
    return {
        "left":   RAIL_WIDTH,
        "right":  TABLE_WIDTH - RAIL_WIDTH,
        "top":    RAIL_WIDTH,
        "bottom": TABLE_HEIGHT - RAIL_WIDTH,
    }


# ── 碰撞偵測 ────────────────────────────────────────────────────────────────

def collision_detect(s1: BallState, s2: BallState) -> Optional[CollisionInfo]:
    """
    偵測兩球是否碰撞。

    條件：球心距 ≤ r1 + r2

    回傳：
        CollisionInfo（若碰撞）
        None（若無碰撞）
    """
    dx = s1.x - s2.x
    dy = s1.y - s2.y
    dist = math.hypot(dx, dy)
    min_dist = s1.radius + s2.radius

    if dist >= min_dist:
        return None

    # 法向量（從 s2 指向 s1）
    if dist == 0:
        # 完全重疊，任意方向
        nx, ny = 1.0, 0.0
    else:
        nx = dx / dist
        ny = dy / dist

    # 碰撞點：球面接觸點（沿法向量方向偏移 r2）
    cx = s2.x + nx * s2.radius
    cy = s2.y + ny * s2.radius

    return CollisionInfo(
        point=(cx, cy),
        normal=(nx, ny),
        distance=dist,
    )


# ── 彈性碰撞速度結算 ──────────────────────────────────────────────────────

def resolve_elastic(
    s1: BallState,
    s2: BallState,
    collision: CollisionInfo,
    restitution: float = 1.0,
) -> tuple[BallState, BallState]:
    """
    等質量二維彈性碰撞速度結算（動量守恆）。

    當 restitution < 1.0 時，法向分量產生能量損耗。

    公式（動量守恆 + 恢復係數）：
        v1n' = e * v1n
        v2n' = e * v2n

    參數：
        s1:        球1（通常為白球）
        s2:        球2（通常為目標球，v2 可以是零）
        collision: collision_detect() 回傳的碰撞資訊
        restitution: 恢復係數 e（0~1），1.0 = 完全彈性（無損耗）
                    撞球球-球約 0.90~0.97

    回傳：(new_s1, new_s2)
    """
    nx, ny = collision.normal

    # 法向分量（純量投影）
    v1_dot_n = s1.vx * nx + s1.vy * ny
    v2_dot_n = s2.vx * nx + s2.vy * ny

    rel_v_n = (s2.vx - s1.vx) * nx + (s2.vy - s1.vy) * ny
    if rel_v_n <= 0:
        return s1, s2

    # 等質量：兩球交換法向分量（並乘以恢復係數）
    delta = (v1_dot_n - v2_dot_n) * restitution

    new_s1_vx = s1.vx - delta * nx
    new_s1_vy = s1.vy - delta * ny

    new_s2_vx = s2.vx + delta * nx
    new_s2_vy = s2.vy + delta * ny

    return (
        BallState(s1.x, s1.y, new_s1_vx, new_s1_vy, s1.radius),
        BallState(s2.x, s2.y, new_s2_vx, new_s2_vy, s2.radius),
    )


# ── 庫邊反彈 ────────────────────────────────────────────────────────────────

def reflect_wall(vx: float, vy: float, rail: str) -> tuple[float, float]:
    """
    庫邊反彈速度修正。

    只反轉對應分量，並乘以 RESTITUTION（能量損耗）。

    參數：
        vx, vy: 當前速度分量 (mm/s)
        rail:   "left" | "right" | "top" | "bottom"

    回傳：(new_vx, new_vy)
    """
    r = RESTITUTION
    if rail == "left":
        return (-vx * r, vy)
    elif rail == "right":
        return (-vx * r, vy)
    elif rail == "top":
        return (vx, -vy * r)
    elif rail == "bottom":
        return (vx, -vy * r)
    else:
        raise ValueError(f"Unknown rail: {rail}")


# ── 口袋偵測 ───────────────────────────────────────────────────────────────

def is_in_pocket(state: BallState, pocket_pos: tuple[float, float]) -> bool:
    """
    判斷球心是否在口袋有效半徑內。

    入口徑 = 50mm，球徑 = 38mm。
    進袋條件：球心距口袋中心 < POCKET_RADIUS
              （實務上球心進入口徑範圍即視為進袋）
    """
    dx = state.x - pocket_pos[0]
    dy = state.y - pocket_pos[1]
    return math.hypot(dx, dy) < POCKET_RADIUS
