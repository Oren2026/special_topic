"""
lib/physics/
物理模擬模組：碰撞、軌跡預測

子模組：
    collision  — 純物理計算（stateless）
    trajectory — 軌跡預測（逐步模擬 + 單球停止預測）
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
from .trajectory import (
    simulate,
    predict_single,
    chain_simulate,
    TrajectoryResult,
    StopPrediction,
    ChainResult,
    CollisionEvent,
    WallHit,
)

__all__ = [
    # collision
    "BallState",
    "CollisionInfo",
    "collision_detect",
    "resolve_elastic",
    "reflect_wall",
    "table_bounds",
    "is_in_pocket",
    # trajectory
    "simulate",
    "predict_single",
    "chain_simulate",
    "TrajectoryResult",
    "StopPrediction",
    "ChainResult",
    "CollisionEvent",
    "WallHit",
]