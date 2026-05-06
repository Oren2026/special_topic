"""
physics/trajectory.py
軌跡預測模擬器

職責：
    給定初始條件（白球位置/速度 + 目標球位置 + 障礙球 + 口袋）
    模擬每一步的物理積分、碰撞偵測、庫邊反彈
    回傳完整軌跡紀錄

不使用策略邏輯——純粹物理預測。
"""

import math
from dataclasses import dataclass, field
from typing import Optional
from .collision import (
    BallState,
    collision_detect,
    resolve_elastic,
    reflect_wall,
    table_bounds,
    is_in_pocket,
)
from .parameters import (
    TABLE_WIDTH,
    TABLE_HEIGHT,
    BALL_RADIUS,
    DT_MS,
    MAX_STEPS,
)


# ── Event Dataclasses ────────────────────────────────────────────────────────

@dataclass
class CollisionEvent:
    """球-球碰撞事件"""
    step: int
    ball1_id: str         # "cue" | "target" | "obstacle_N"
    ball2_id: str
    point: tuple[float, float]
    normal: tuple[float, float]
    v1_before: tuple[float, float]
    v2_before: tuple[float, float]
    v1_after: tuple[float, float]
    v2_after: tuple[float, float]


@dataclass
class WallEvent:
    """庫邊碰撞事件"""
    step: int
    ball_id: str          # "cue" | "target"
    rail: str             # "left" | "right" | "top" | "bottom"
    point: tuple[float, float]
    v_before: tuple[float, float]
    v_after: tuple[float, float]


@dataclass
class TrajectoryResult:
    """軌跡模擬結果"""
    cue_path: list[tuple[float, float]] = field(default_factory=list)
    target_path: list[tuple[float, float]] = field(default_factory=list)

    cue_final: Optional[tuple[float, float]] = None
    target_final: Optional[tuple[float, float]] = None

    pocket_sunk: bool = False
    pocket_sunk_at_step: Optional[int] = None
    pocket_sunk_ball: Optional[str] = None  # "cue" | "target"

    collision_events: list[CollisionEvent] = field(default_factory=list)
    wall_events: list[WallEvent] = field(default_factory=list)

    # 額外軌跡（其他球）
    obstacle_paths: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    def is_target_sunk(self) -> bool:
        return self.pocket_sunk and self.pocket_sunk_ball == "target"


# ── Main Simulator ──────────────────────────────────────────────────────────

def simulate(
    cue_pos: tuple[float, float],
    cue_dir: tuple[float, float],        # 瞄準方向單位向量 (dx, dy)
    target_pos: tuple[float, float],
    pocket_pos: tuple[float, float],
    obstacles: list[tuple[float, float]] = [],  # 障礙球位置列表（僅位置）
    speed: float = 3000.0,                # 擊球初速 mm/s
    dt_ms: int = DT_MS,
    restitution: float = None,            # None → 使用預設 RESTITUTION
    max_steps: int = MAX_STEPS,
    pocket_name: str = "",
) -> TrajectoryResult:
    """
    模擬一次擊球的全軌跡（純物理積分）。

    流程：
        每一步：
        1. advance all balls
        2. 球-球碰撞偵測與結算（cue ↔ target, cue ↔ obstacles, target ↔ obstacles）
        3. 庫邊碰撞偵測與反射（clamp + reflect_wall）
        4. 口袋進袋偵測

    參數：
        cue_pos:     白球初始位置 (x, y) mm
        cue_dir:     白球瞄準方向單位向量 (dx, dy)（並非 G 位置，是瞄準方向）
        target_pos:  目標球初始位置 (x, y) mm
        pocket_pos:  口袋位置 (x, y) mm
        obstacles:   障礙球位置列表
        speed:       擊球初速 mm/s
        dt_ms:       時間步長（毫秒）
        restitution:  彈性係數（None → 使用預設值）
        max_steps:   最大模擬步數
        pocket_name: 口袋名稱（純記錄用）

    回傳：TrajectoryResult
    """
    dt = dt_ms / 1000.0  # 轉為秒

    # 初始化球狀態
    dx, dy = cue_dir
    d_len = math.hypot(dx, dy)
    if d_len == 0:
        raise ValueError("cue_dir must be non-zero")
    ux, uy = dx / d_len, dy / d_len

    cue    = BallState(cue_pos[0], cue_pos[1], ux * speed, uy * speed)
    target = BallState(target_pos[0], target_pos[1], 0.0, 0.0)

    # 障礙球（靜態）
    obstacle_balls = [
        BallState(ox, oy, 0.0, 0.0)
        for ox, oy in obstacles
    ]

    # 結果容器
    result = TrajectoryResult()
    result.cue_path.append(cue.pos())
    result.target_path.append(target.pos())
    result.obstacle_paths = {f"obstacle_{i}": [(ox, oy)] for i, (ox, oy) in enumerate(obstacles)}

    bounds = table_bounds()
    done = False

    for step in range(1, max_steps + 1):
        if done:
            break

        # ── 1. 前進一步 ──────────────────────────────────────────────────
        _advance(cue, dt)
        _advance(target, dt)
        for obs in obstacle_balls:
            _advance(obs, dt)

        # ── 2. 庫邊碰撞 ──────────────────────────────────────────────────
        _resolve_wall(cue,    bounds, step, result, "cue")
        _resolve_wall(target, bounds, step, result, "target")

        # ── 3. 球-球碰撞 ─────────────────────────────────────────────────
        # cue ↔ target
        ci = collision_detect(cue, target)
        if ci is not None:
            c_before = (cue.vx, cue.vy)
            t_before = (target.vx, target.vy)
            cue, target = resolve_elastic(cue, target, ci)
            result.collision_events.append(CollisionEvent(
                step=step,
                ball1_id="cue",
                ball2_id="target",
                point=ci.point,
                normal=ci.normal,
                v1_before=c_before,
                v2_before=t_before,
                v1_after=(cue.vx, cue.vy),
                v2_after=(target.vx, target.vy),
            ))

        # cue ↔ obstacles
        for i, obs in enumerate(obstacle_balls):
            ci = collision_detect(cue, obs)
            if ci is not None:
                c_before = (cue.vx, cue.vy)
                o_before = (obs.vx, obs.vy)
                cue, obs = resolve_elastic(cue, obs, ci)
                obstacle_balls[i] = obs
                result.collision_events.append(CollisionEvent(
                    step=step,
                    ball1_id="cue",
                    ball2_id=f"obstacle_{i}",
                    point=ci.point,
                    normal=ci.normal,
                    v1_before=c_before,
                    v2_before=o_before,
                    v1_after=(cue.vx, cue.vy),
                    v2_after=(obs.vx, obs.vy),
                ))

        # target ↔ obstacles
        for i, obs in enumerate(obstacle_balls):
            ci = collision_detect(target, obs)
            if ci is not None:
                t_before = (target.vx, target.vy)
                o_before = (obs.vx, obs.vy)
                target, obs = resolve_elastic(target, obs, ci)
                obstacle_balls[i] = obs
                result.collision_events.append(CollisionEvent(
                    step=step,
                    ball1_id="target",
                    ball2_id=f"obstacle_{i}",
                    point=ci.point,
                    normal=ci.normal,
                    v1_before=t_before,
                    v2_before=o_before,
                    v1_after=(target.vx, target.vy),
                    v2_after=(obs.vx, obs.vy),
                ))

        # ── 4. 進袋偵測 ─────────────────────────────────────────────────
        if is_in_pocket(cue, pocket_pos):
            result.pocket_sunk = True
            result.pocket_sunk_at_step = step
            result.pocket_sunk_ball = "cue"
            result.cue_final = cue.pos()
            result.target_final = target.pos()
            done = True
            continue

        if is_in_pocket(target, pocket_pos):
            result.pocket_sunk = True
            result.pocket_sunk_at_step = step
            result.pocket_sunk_ball = "target"
            result.cue_final = cue.pos()
            result.target_final = target.pos()
            done = True
            continue

        # ── 5. 速度趨近於零 → 終止 ────────────────────────────────────
        cue_speed    = math.hypot(cue.vx,    cue.vy)
        target_speed = math.hypot(target.vx, target.vy)
        if cue_speed < 1.0 and target_speed < 1.0:
            result.cue_final    = cue.pos()
            result.target_final = target.pos()
            done = True
            continue

        # ── 6. 記錄路徑 ────────────────────────────────────────────────
        result.cue_path.append(cue.pos())
        result.target_path.append(target.pos())
        for i, obs in enumerate(obstacle_balls):
            result.obstacle_paths[f"obstacle_{i}"].append(obs.pos())

    # 最後一幀仍未記錄 final
    if result.cue_final is None:
        result.cue_final = cue.pos()
    if result.target_final is None:
        result.target_final = target.pos()

    return result


def _advance(ball: BallState, dt: float) -> None:
    """
    位置積分（in-place）。
    速度為 mm/s，dt 為秒，結果為 mm。
    """
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt


def _resolve_wall(
    ball: BallState,
    bounds: dict,
    step: int,
    result: TrajectoryResult,
    ball_id: str,
) -> None:
    """
    庫邊碰撞偵測 + 修正（clamp + reflect）。

    流程：
        1. 檢查四邊是否越界
        2. 若越界：clamp 位置至邊界，反轉速度分量（× RESTITUTION）
        3. 記錄 WallEvent
    """
    v_before = (ball.vx, ball.vy)
    hit_rail = None

    if ball.x < bounds["left"]:
        ball.x = bounds["left"]
        ball.vx = -ball.vx * 0.95  # RESTITUTION 已在 reflect_wall，這裡直接寫死
        hit_rail = "left"
    elif ball.x > bounds["right"]:
        ball.x = bounds["right"]
        ball.vx = -ball.vx * 0.95
        hit_rail = "right"

    if ball.y < bounds["top"]:
        ball.y = bounds["top"]
        ball.vy = -ball.vy * 0.95
        hit_rail = "top"
    elif ball.y > bounds["bottom"]:
        ball.y = bounds["bottom"]
        ball.vy = -ball.vy * 0.95
        hit_rail = "bottom"

    if hit_rail is not None:
        result.wall_events.append(WallEvent(
            step=step,
            ball_id=ball_id,
            rail=hit_rail,
            point=(ball.x, ball.y),
            v_before=v_before,
            v_after=(ball.vx, ball.vy),
        ))
