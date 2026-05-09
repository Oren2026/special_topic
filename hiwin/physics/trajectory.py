"""
physics/trajectory.py
軌跡預測模擬器

職責：
    給定初始條件（白球位置/速度 + 目標球位置 + 障礙球 + 口袋）
    模擬每一步的物理積分、碰撞偵測、庫邊反彈
    回傳完整軌跡紀錄

不使用策略邏輯——純粹物理預測。

子功能：
    predict_single() — 單一球體的摩擦+庫邊軌跡預測
                       用途：碰撞後球會停在哪？路上會不會碰到障礙球？
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Union
from .collision import (
    BallState,
    collision_detect,
    resolve_elastic,
    table_bounds,
    is_in_pocket,
)
from .parameters import (
    TABLE_WIDTH,
    TABLE_HEIGHT,
    RAIL_WIDTH,
    BALL_RADIUS,
    ROLLING_FRICTION,
    RESTITUTION,
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
class WallHit:
    """庫邊碰撞事件（predict_single 與 simulate 通用）"""
    step: int
    ball_id: str          # "cue" | "target" | "single" | "ball_N"
    rail: str             # "left" | "right" | "top" | "bottom"
    pos: tuple[float, float]
    v_before: tuple[float, float]
    v_after: tuple[float, float]


@dataclass
class StopPrediction:
    """
    單一球體的停止預測結果（predict_single 的回傳格式）。

    用途舉例：
        target 碰撞後 → predict_single(target) → target 會停在哪？
        路上會不會碰到障礙球？
    """
    final_pos: tuple[float, float]           # 停止時球心座標 (x, y) mm
    total_distance: float                    # 總運動距離 mm
    wall_bounces: int                        # 庫邊反彈次數
    stopped_at_step: int                     # 停止時的模擬步數
    wall_hits: list[WallHit] = field(default_factory=list)
    # 障礙球碰撞查詢
    collision_before_stop: bool = False
    first_collision: Optional[CollisionEvent] = None
    collision_point: Optional[tuple[float, float]] = None
    collision_step: Optional[int] = None


@dataclass
class TrajectoryResult:
    """軌跡模擬結果（simulate 的回傳格式）"""
    cue_path: list[tuple[float, float]] = field(default_factory=list)
    target_path: list[tuple[float, float]] = field(default_factory=list)

    cue_final: Optional[tuple[float, float]] = None
    target_final: Optional[tuple[float, float]] = None

    pocket_sunk: bool = False
    pocket_sunk_at_step: Optional[int] = None
    pocket_sunk_ball: Optional[str] = None  # "cue" | "target"

    collision_events: list[CollisionEvent] = field(default_factory=list)
    wall_hits: list[WallHit] = field(default_factory=list)      # 統一用 wall_hits

    # 額外軌跡（其他球）
    obstacle_paths: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    # 各球總路程
    cue_distance: float = 0.0
    target_distance: float = 0.0

    def is_target_sunk(self) -> bool:
        return self.pocket_sunk and self.pocket_sunk_ball == "target"


# ── Single Ball Predictor ────────────────────────────────────────────────────

def predict_single(
    x: float,
    y: float,
    vx: float,
    vy: float,
    friction: float = ROLLING_FRICTION,
    restitution: float = RESTITUTION,
    dt_ms: int = DT_MS,
    max_steps: int = 5000,
    ball_id: str = "single",
    obstacles: Union[list[BallState], list[tuple[float, float]]] = [],
) -> StopPrediction:
    """
    預測單一球體從 (x, y, vx, vy) 到停止的完整軌跡。

    模擬內容：
        ✓ 滾動摩擦（速度衰減）
        ✓ 庫邊反彈（clamp + 反轉 + restitution 損耗）
        ✓ 停止條件：speed < 0.5 mm/s

    不模擬（predict_single 的範圍外）：
        ✗ 球-球碰撞（僅查詢「路上有沒有障礙球」，靜態偵測）
        ✗ 進袋偵測（本函式不用於帶口袋的擊球模擬）

    參數：
        x, y, vx, vy: 初始狀態
        friction:     滾動摩擦加速度 mm/s²（預設 150）
        restitution:  庫邊彈性係數（預設 0.95）
        dt_ms:        時間步長 ms（預設 10）
        max_steps:     最大模擬步數
        ball_id:      球的識別名稱（wall_hits 記錄用）
        obstacles:     障礙球列表（BallState 或 (x,y) tuples）

    回傳：StopPrediction
    """
    dt = dt_ms / 1000.0
    bounds = table_bounds()

    ball = BallState(x, y, vx, vy, BALL_RADIUS)

    # 障礙球統一轉 BallState
    obstacle_balls: list[BallState] = []
    for obs in obstacles:
        if isinstance(obs, BallState):
            obstacle_balls.append(obs)
        else:
            ox, oy = obs
            obstacle_balls.append(BallState(ox, oy, 0.0, 0.0, BALL_RADIUS))

    wall_hits: list[WallHit] = []
    total_dist = 0.0
    prev_x, prev_y = x, y
    stopped_at_step = 0
    speed = math.hypot(vx, vy)

    # 碰撞查詢
    collision_before_stop = False
    first_ci: Optional[CollisionEvent] = None
    first_cp: Optional[tuple[float, float]] = None
    first_cs: Optional[int] = None

    for step in range(1, max_steps + 1):
        if speed < 0.5:
            stopped_at_step = step
            break

        # ── 1. 摩擦衰減 + 前進 ──────────────────────────────────────────
        new_speed = max(0.0, speed - friction * dt)
        factor = new_speed / speed if speed > 0 else 0.0
        ball.vx *= factor
        ball.vy *= factor
        speed = new_speed

        nx = ball.x + ball.vx * dt
        ny = ball.y + ball.vy * dt

        # ── 2. 庫邊碰撞 ──────────────────────────────────────────────────
        bounced_rail = None
        if nx < bounds["left"]:
            nx = bounds["left"]
            ball.vx = -ball.vx * restitution
            bounced_rail = "left"
        elif nx > bounds["right"]:
            nx = bounds["right"]
            ball.vx = -ball.vx * restitution
            bounced_rail = "right"
        if ny < bounds["top"]:
            ny = bounds["top"]
            ball.vy = -ball.vy * restitution
            bounced_rail = "top"
        elif ny > bounds["bottom"]:
            ny = bounds["bottom"]
            ball.vy = -ball.vy * restitution
            bounced_rail = "bottom"

        if bounced_rail is not None:
            # 反推反彈前速度（factor 已知）
            v_before_x = ball.vx / factor if factor > 0 else 0.0
            v_before_y = ball.vy / factor if factor > 0 else 0.0
            wall_hits.append(WallHit(
                step=step,
                ball_id=ball_id,
                rail=bounced_rail,
                pos=(nx, ny),
                v_before=(v_before_x, v_before_y),
                v_after=(ball.vx, ball.vy),
            ))

        ball.x, ball.y = nx, ny

        # ── 3. 路徑累加 ───────────────────────────────────────────────────
        seg_dist = math.hypot(nx - prev_x, ny - prev_y)
        total_dist += seg_dist
        prev_x, prev_y = nx, ny

        # ── 4. 障礙球碰撞查詢（靜態偵測，不影響軌跡）──────────────────
        if not collision_before_stop:
            for obs in obstacle_balls:
                ci = collision_detect(ball, obs)
                if ci is not None:
                    collision_before_stop = True
                    # 構造 CollisionEvent（格式與 simulate 一致）
                    first_ci = CollisionEvent(
                        step=step,
                        ball1_id=ball_id,
                        ball2_id="obstacle",
                        point=ci.point,
                        normal=ci.normal,
                        v1_before=(v_before_x, v_before_y),
                        v2_before=(0.0, 0.0),
                        v1_after=(ball.vx, ball.vy),
                        v2_after=(0.0, 0.0),
                    )
                    first_cp = (ci.point[0], ci.point[1])
                    first_cs = step
                    break

    if stopped_at_step == 0:
        stopped_at_step = max_steps

    return StopPrediction(
        final_pos=(round(ball.x, 2), round(ball.y, 2)),
        total_distance=round(total_dist, 2),
        wall_bounces=len(wall_hits),
        stopped_at_step=stopped_at_step,
        wall_hits=wall_hits,
        collision_before_stop=collision_before_stop,
        first_collision=first_ci,
        collision_point=first_cp,
        collision_step=first_cs,
    )


# ── Main Simulator ──────────────────────────────────────────────────────────

def simulate(
    cue_pos: tuple[float, float],
    cue_dir: tuple[float, float],        # 瞄準方向單位向量 (dx, dy)
    target_pos: tuple[float, float],
    pocket_pos: tuple[float, float],
    obstacles: list[tuple[float, float]] = [],  # 障礙球位置列表（僅位置）
    speed: float = 3000.0,                # 擊球初速 mm/s
    dt_ms: int = DT_MS,
    ball_restitution: float = 1.0,        # 球-球碰撞恢復係數（<1 有損耗）
    restitution: float = None,            # 庫邊碰撞（None → 用 RESTITUTION）
    max_steps: int = MAX_STEPS,
    pocket_name: str = "",
) -> TrajectoryResult:
    """
    模擬一次擊球的全軌跡（純物理積分）。

    流程：
        每一步：
        1. advance all balls（摩擦 + 前進）
        2. 球-球碰撞偵測與結算
        3. 庫邊碰撞偵測與反射
        4. 口袋進袋偵測
        5. 速度趨零終止

    參數：
        cue_pos, cue_dir, target_pos, pocket_pos, obstacles, speed
        dt_ms, ball_restitution, restitution, max_steps, pocket_name

    回傳：TrajectoryResult
    """
    dt = dt_ms / 1000.0
    if restitution is None:
        restitution = RESTITUTION

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

    # 路徑累加
    total_cue_dist = 0.0
    total_target_dist = 0.0
    prev_cue = cue.pos()
    prev_target = target.pos()

    for step in range(1, max_steps + 1):
        if done:
            break

        # ── 1. 前進一步 ──────────────────────────────────────────────────
        _advance(cue, dt, friction=ROLLING_FRICTION)
        _advance(target, dt, friction=ROLLING_FRICTION)
        for obs in obstacle_balls:
            _advance(obs, dt, friction=ROLLING_FRICTION)

        # ── 2. 庫邊碰撞 ──────────────────────────────────────────────────
        _resolve_wall(cue,    bounds, step, result, "cue",    restitution)
        _resolve_wall(target, bounds, step, result, "target",  restitution)

        # ── 3. 球-球碰撞 ─────────────────────────────────────────────────
        # cue ↔ target
        ci = collision_detect(cue, target)
        if ci is not None:
            c_before = (cue.vx, cue.vy)
            t_before = (target.vx, target.vy)
            cue, target = resolve_elastic(cue, target, ci, ball_restitution)
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
                cue, obs = resolve_elastic(cue, obs, ci, ball_restitution)
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
                target, obs = resolve_elastic(target, obs, ci, ball_restitution)
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

        # ── 6. 路徑累加 ────────────────────────────────────────────────
        total_cue_dist    += math.hypot(cue.x - prev_cue[0],    cue.y - prev_cue[1])
        total_target_dist += math.hypot(target.x - prev_target[0], target.y - prev_target[1])
        prev_cue    = cue.pos()
        prev_target = target.pos()
        result.cue_path.append(cue.pos())
        result.target_path.append(target.pos())
        for i, obs in enumerate(obstacle_balls):
            result.obstacle_paths[f"obstacle_{i}"].append(obs.pos())

    # 最後一幀仍未記錄 final
    if result.cue_final is None:
        result.cue_final = cue.pos()
    if result.target_final is None:
        result.target_final = target.pos()

    result.cue_distance = round(total_cue_dist, 2)
    result.target_distance = round(total_target_dist, 2)
    return result


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _advance(ball: BallState, dt: float, friction: float = ROLLING_FRICTION) -> None:
    """
    位置積分（in-place）+ 滾動摩擦損耗。

    速度為 mm/s，dt 為秒，結果為 mm。
    """
    speed = math.hypot(ball.vx, ball.vy)
    if speed > 0.5:
        new_speed = max(0, speed - friction * dt)
        factor = new_speed / speed
        ball.vx *= factor
        ball.vy *= factor
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt


def _resolve_wall(
    ball: BallState,
    bounds: dict,
    step: int,
    result: TrajectoryResult,
    ball_id: str,
    restitution: float = RESTITUTION,
) -> None:
    """
    庫邊碰撞偵測 + 修正（clamp + reflect）。

    流程：
        1. 檢查四邊是否越界
        2. 若越界：clamp 位置至邊界，反轉速度分量（× RESTITUTION）
        3. 記錄 WallHit
    """
    v_before = (ball.vx, ball.vy)
    hit_rail = None

    if ball.x < bounds["left"]:
        ball.x = bounds["left"]
        ball.vx = -ball.vx * restitution
        hit_rail = "left"
    elif ball.x > bounds["right"]:
        ball.x = bounds["right"]
        ball.vx = -ball.vx * restitution
        hit_rail = "right"

    if ball.y < bounds["top"]:
        ball.y = bounds["top"]
        ball.vy = -ball.vy * restitution
        hit_rail = "top"
    elif ball.y > bounds["bottom"]:
        ball.y = bounds["bottom"]
        ball.vy = -ball.vy * restitution
        hit_rail = "bottom"

    if hit_rail is not None:
        result.wall_hits.append(WallHit(
            step=step,
            ball_id=ball_id,
            rail=hit_rail,
            pos=(ball.x, ball.y),
            v_before=v_before,
            v_after=(ball.vx, ball.vy),
        ))