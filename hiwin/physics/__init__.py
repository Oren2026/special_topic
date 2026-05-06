"""
physics/
物理模擬模組：碰撞、軌跡預測

子模組：
    collision  — 純物理計算（stateless）
    trajectory — 軌跡預測
"""

from .collision import (
    BallState,
    CollisionInfo,
    collision_detect,
    resolve_elastic,
    reflect_wall,
    table_bounds,
    is_in_pocket,
)
from .trajectory import simulate, TrajectoryResult, CollisionEvent, WallEvent

__all__ = [
    "BallState",
    "CollisionInfo",
    "collision_detect",
    "resolve_elastic",
    "reflect_wall",
    "table_bounds",
    "is_in_pocket",
    "simulate",
    "TrajectoryResult",
    "CollisionEvent",
    "WallEvent",
]
