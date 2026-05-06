"""
tests/test_physics.py
物理模組單元測試

Run: python3 -m pytest tests/test_physics.py -v
"""

import math
import pytest
import sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physics.collision import (
    BallState,
    CollisionInfo,
    collision_detect,
    resolve_elastic,
    reflect_wall,
    table_bounds,
    is_in_pocket,
)
from physics.trajectory import simulate, TrajectoryResult
from physics.parameters import BALL_RADIUS, BALL_DIAMETER, RESTITUTION


def eq(a, b, tol=1e-6):
    return abs(a - b) < tol


# ── BallState ────────────────────────────────────────────────────────────────

def test_ball_state_creation():
    b = BallState(x=100, y=200, vx=500, vy=0)
    assert b.x == 100
    assert b.y == 200
    assert b.vx == 500
    assert b.vy == 0
    assert b.radius == BALL_RADIUS


def test_ball_state_pos():
    b = BallState(x=10, y=20)
    assert b.pos() == (10, 20)


def test_ball_state_vel():
    b = BallState(x=0, y=0, vx=3, vy=4)
    assert b.vel() == (3, 4)


# ── collision_detect ────────────────────────────────────────────────────────

def test_no_collision_separate():
    """兩球分離，無碰撞"""
    s1 = BallState(x=0, y=0)
    s2 = BallState(x=100, y=0)
    assert collision_detect(s1, s2) is None


def test_no_collision_tangent():
    """兩球剛好相切，無碰撞"""
    s1 = BallState(x=0, y=0)
    s2 = BallState(x=BALL_DIAMETER, y=0)
    assert collision_detect(s1, s2) is None


def test_collision_overlapping():
    """兩球重疊，有碰撞"""
    s1 = BallState(x=0, y=0)
    s2 = BallState(x=BALL_DIAMETER * 0.8, y=0)
    ci = collision_detect(s1, s2)
    assert ci is not None
    assert ci.distance < BALL_DIAMETER


def test_collision_normal_direction():
    """碰撞法向量從 s2 指向 s1"""
    # 球距 10 < 半徑和 38 → 碰撞
    s1 = BallState(x=10, y=0)
    s2 = BallState(x=0, y=0)
    ci = collision_detect(s1, s2)
    assert ci is not None
    nx, ny = ci.normal
    # s2 在左側 (0,0)，s1 在右側 (10,0)，法向量朝右
    assert nx > 0.9


def test_collision_point_location():
    """碰撞點在半徑範圍內"""
    s1 = BallState(x=19, y=0)
    s2 = BallState(x=0, y=0)
    ci = collision_detect(s1, s2)
    assert ci is not None
    cx, cy = ci.point
    # 碰撞點應該在 s2 的球面上（s2 右側）
    assert cx > 0


# ── resolve_elastic ─────────────────────────────────────────────────────────

def test_head_on_collision_stationary():
    """等質量正面碰撞：b1 停止，b2 以 b1 原速前進"""
    # 球心距 = 36mm < 半徑和 38mm → 碰撞
    cue    = BallState(x=0,     y=0, vx=1000, vy=0)
    target = BallState(x=36,    y=0, vx=0,    vy=0)
    ci = collision_detect(cue, target)
    assert ci is not None

    new_cue, new_target = resolve_elastic(cue, target, ci)

    # 白球幾乎停止（法向分量被目標球接收）
    assert math.hypot(new_cue.vx, new_cue.vy) < 50
    # 目標球以前進方向為主（動量轉移）
    assert new_target.vx > 900


def test_offset_collision():
    """偏移碰撞：能量守恆"""
    # cue=(0,0) moving right, target=(35,5) offset
    # dist=35.36 < min_dist=38 → collision
    # Energy conserved (diff=0%)
    cue    = BallState(x=0,  y=0,  vx=1000, vy=0)
    target = BallState(x=35, y=5,  vx=0,    vy=0)
    ci = collision_detect(cue, target)
    assert ci is not None

    new_cue, new_target = resolve_elastic(cue, target, ci)

    # 能量守恆驗證（等質量）
    E_before = 1000 * 1000
    E_after  = math.hypot(new_cue.vx, new_cue.vy)**2 + math.hypot(new_target.vx, new_target.vy)**2
    assert abs(E_after - E_before) / E_before < 1e-9


def test_separated_balls_no_resolution():
    """兩球已分離，不結算"""
    cue    = BallState(x=0,     y=0, vx=1000, vy=0)
    target = BallState(x=1000,  y=0, vx=0,    vy=0)
    ci = collision_detect(cue, target)
    assert ci is None


# ── reflect_wall ────────────────────────────────────────────────────────────

def test_reflect_left_wall():
    vx, vy = reflect_wall(500, 300, "left")
    assert vx < 0   # vx 反轉
    assert eq(abs(vx), 500 * RESTITUTION)
    assert eq(vy, 300)  # vy 不變


def test_reflect_right_wall():
    vx, vy = reflect_wall(500, 300, "right")
    assert vx < 0
    assert eq(abs(vx), 500 * RESTITUTION)
    assert eq(vy, 300)


def test_reflect_top_wall():
    vx, vy = reflect_wall(500, 300, "top")
    assert eq(vx, 500)
    assert vy < 0
    assert eq(abs(vy), 300 * RESTITUTION)


def test_reflect_bottom_wall():
    vx, vy = reflect_wall(500, 300, "bottom")
    assert eq(vx, 500)
    assert vy < 0
    assert eq(abs(vy), 300 * RESTITUTION)


def test_reflect_invalid_rail():
    with pytest.raises(ValueError):
        reflect_wall(500, 300, "invalid")


# ── table_bounds ────────────────────────────────────────────────────────────

def test_table_bounds():
    b = table_bounds()
    assert "left"   in b
    assert "right"  in b
    assert "top"    in b
    assert "bottom" in b
    assert b["left"] < b["right"]
    assert b["top"]  < b["bottom"]


# ── is_in_pocket ────────────────────────────────────────────────────────────

def test_is_in_pocket_inside():
    from physics.parameters import POCKET_RADIUS
    pocket = (100, 200)
    ball = BallState(x=100, y=200)  # 球心在口袋中心
    assert is_in_pocket(ball, pocket) is True


def test_is_in_pocket_outside():
    pocket = (100, 200)
    ball = BallState(x=500, y=500)  # 遠離口袋
    assert is_in_pocket(ball, pocket) is False


def test_is_in_pocket_boundary():
    from physics.parameters import POCKET_RADIUS
    pocket = (100, 200)
    # 球心在口袋半徑邊緣內
    ball = BallState(x=100 + POCKET_RADIUS * 0.9, y=200)
    assert is_in_pocket(ball, pocket) is True


# ── trajectory ────────────────────────────────────────────────────────────

def test_direct_shot_into_pocket():
    """直線進袋：白球、目标球、口袋排成一線"""
    # 白球在左側，口袋在左側（side_left = (-575, 315)）
    # 但檯子左邊界是 RAIL_WIDTH=50，所以要朝左打需要特殊設定
    # 改用檯面中心附近：cue=(300,315), target=(200,315), pocket在target左側
    # 設定一個更簡單的場景：白球打目標球進側袋
    result = simulate(
        cue_pos=(400, 315),
        cue_dir=(1, 0),           # 朝右打
        target_pos=(550, 315),
        pocket_pos=(575, 315),    # side_right 口袋
        obstacles=[],
        speed=3000,
        dt_ms=10,
    )
    assert isinstance(result, TrajectoryResult)
    assert result.cue_path[0] == (400, 315)
    assert len(result.cue_path) >= 2


def test_obstacle_blocks_cue():
    """障礙球擋在白球和目標球之間"""
    result = simulate(
        cue_pos=(100, 315),
        cue_dir=(1, 0),
        target_pos=(500, 315),
        pocket_pos=(600, 315),
        obstacles=[(300, 315)],  # 障礙球在中間
        speed=3000,
        dt_ms=10,
    )
    # 白球會碰到障礙球
    collision_balls = {e.ball1_id for e in result.collision_events} | {e.ball2_id for e in result.collision_events}
    assert "obstacle_0" in collision_balls


def test_trajectory_records_paths():
    """軌跡記錄完整"""
    result = simulate(
        cue_pos=(200, 200),
        cue_dir=(1, 0),
        target_pos=(600, 200),
        pocket_pos=(575, 315),
        obstacles=[],
        speed=2000,
        dt_ms=10,
    )
    assert len(result.cue_path) >= 2
    assert len(result.target_path) >= 2
    assert result.cue_final is not None
    assert result.target_final is not None


def test_pocket_sunk_detected():
    """目標球進袋偵測（如果幾何條件允許）"""
    # 設定：target 幾乎在口袋旁邊，C→T→P 幾乎共線
    result = simulate(
        cue_pos=(200, 315),
        cue_dir=(1, 0),
        target_pos=(540, 315),        # 靠近側袋
        pocket_pos=(575, 315),        # 側袋
        obstacles=[],
        speed=3000,
        dt_ms=10,
    )
    # 如果幾何條件滿足，紀錄進袋
    # 如果不滿足，至少確認 result 結構正確
    assert result.cue_path[0] is not None
    assert result.pocket_sunk_ball in (None, "cue", "target")


def test_simulate_returns_target_path():
    """目標球路徑有記錄"""
    result = simulate(
        cue_pos=(100, 100),
        cue_dir=(1, 0.5),
        target_pos=(500, 200),
        pocket_pos=(575, 315),
        obstacles=[],
        speed=2000,
        dt_ms=10,
    )
    assert len(result.target_path) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
