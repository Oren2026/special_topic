"""
hiwin/lib/
獨立邏輯模組（無 UI、無硬體依賴）

組成：
- physics/     物理引擎（碰撞、軌跡、參數）
- sim_table    球檯資料類（口袋、球檯幾何）
- table_geometry  幾何計算輔助函式
- state        狀態列舉

使用方式：
    from lib.physics import simulate, TrajectoryResult
    from lib.sim_table import SimTable, DEFAULT_TABLE
    from lib.state import State
"""

from lib.physics import (
    simulate,
    predict_single,
    TrajectoryResult,
)
from lib.sim_table import SimTable, DEFAULT_TABLE, PocketSpec
from lib.table_geometry import TableGeometry, distance_mm, ball_to_pocket_mm
from lib.state import State

__all__ = [
    # physics
    "simulate",
    "predict_single",
    "TrajectoryResult",
    # sim_table
    "SimTable",
    "DEFAULT_TABLE",
    "PocketSpec",
    # geometry
    "TableGeometry",
    "distance_mm",
    "ball_to_pocket_mm",
    # state
    "State",
]