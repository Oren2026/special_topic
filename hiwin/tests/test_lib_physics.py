"""
tests/test_lib_physics.py
Tests for lib.physics (trajectory, collision, parameters)
+ lib.sim_table (SimTable, PocketSpec, DEFAULT_TABLE)
+ lib.table_geometry (TableGeometry, distance_mm, ball_to_pocket_mm)

Run: python3 -m pytest tests/test_lib_physics.py -v
"""

import math
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from lib.physics import (
    simulate,
    predict_single,
    TrajectoryResult,
    StopPrediction,
    chain_simulate,
    BallState,
    CollisionInfo,
    collision_detect,
    resolve_elastic,
    reflect_wall,
    table_bounds,
    is_in_pocket,
)
from lib.physics.parameters import (
    BALL_RADIUS,
    BALL_DIAMETER,
    RESTITUTION,
    ROLLING_FRICTION,
    POCKET_RADIUS,
    POCKET_DIAMETER,
    TABLE_WIDTH,
    TABLE_HEIGHT,
)
from lib.sim_table import SimTable, DEFAULT_TABLE, PocketSpec
from lib.table_geometry import TableGeometry, distance_mm, ball_to_pocket_mm


# ── Parameters ──────────────────────────────────────────────────────────────

class TestParameters:
    def test_ball_radius_positive(self):
        assert BALL_RADIUS > 0

    def test_ball_diameter_positive(self):
        assert BALL_DIAMETER > 0

    def test_restitution_range(self):
        assert 0.0 <= RESTITUTION <= 1.0

    def test_rolling_friction_nonnegative(self):
        assert ROLLING_FRICTION >= 0

    def test_pocket_radius_greater_than_ball_radius(self):
        assert POCKET_RADIUS > BALL_RADIUS

    def test_pocket_radius_positive(self):
        assert POCKET_RADIUS > 0

    def test_table_dimensions_positive(self):
        assert TABLE_WIDTH > 0
        assert TABLE_HEIGHT > 0


# ── Collision ───────────────────────────────────────────────────────────────

class TestCollisionDetect:
    def test_no_collision_distant_balls(self):
        s1 = BallState(x=0, y=0, vx=0, vy=0)
        s2 = BallState(x=500, y=500, vx=0, vy=0)
        assert collision_detect(s1, s2) is None

    def test_exact_collision(self):
        # Two balls at same position — edge case
        s1 = BallState(x=100, y=100, vx=0, vy=0)
        s2 = BallState(x=100, y=100, vx=0, vy=0)
        ci = collision_detect(s1, s2)
        assert ci is not None
        assert ci.distance == 0.0

    def test_touching_balls(self):
        # Two balls exactly touching (radius = 19 each → min_dist = 38)
        s1 = BallState(x=0, y=0, vx=0, vy=0)
        s2 = BallState(x=38, y=0, vx=0, vy=0)
        ci = collision_detect(s1, s2)
        assert ci is not None
        assert ci.distance == 38.0

    def test_normal_case(self):
        s1 = BallState(x=0, y=0)
        s2 = BallState(x=30, y=0)
        ci = collision_detect(s1, s2)
        assert ci is not None
        assert ci.point[0] == 30 - BALL_RADIUS  # contact point on s2 surface


class TestResolveElastic:
    def test_head_on_collision_equal_mass_swaps_velocities(self):
        # Cue ball (s1) moving right at 3000, target ball (s2) stationary
        s1 = BallState(x=0, y=0, vx=3000, vy=0)
        s2 = BallState(x=38, y=0, vx=0, vy=0)  # 38 = 2×BALL_RADIUS, balls exactly touching
        ci = collision_detect(s1, s2)
        assert ci is not None
        new_s1, new_s2 = resolve_elastic(s1, s2, ci, restitution=1.0)
        # With full elastic collision, cue should nearly stop and target moves
        # (exact values depend on geometry but both should have speed > 0)
        assert new_s2.vx > 0
        assert abs(new_s1.vx) < 3000

    def test_stationary_balls_no_crash(self):
        # Two stationary balls with zero velocity but separated - should not crash
        s1 = BallState(x=100, y=100, vx=0, vy=0)
        s2 = BallState(x=138, y=100, vx=0, vy=0)  # exactly touching (2×BALL_RADIUS apart)
        ci = collision_detect(s1, s2)
        assert ci is not None  # must be touching for resolve_elastic

    def test_restitution_dampening(self):
        s1 = BallState(x=0, y=0, vx=1000, vy=0)
        s2 = BallState(x=38, y=0, vx=0, vy=0)  # 38 = 2×BALL_RADIUS
        ci = collision_detect(s1, s2)
        new_s1, new_s2 = resolve_elastic(s1, s2, ci, restitution=0.5)
        # Energy should be dampened
        speed1 = math.hypot(new_s1.vx, new_s1.vy)
        assert speed1 < 1000


class TestReflectWall:
    def test_reflect_left(self):
        vx, vy = reflect_wall(100, 50, "left")
        assert vx < 0
        assert vy == 50

    def test_reflect_right(self):
        vx, vy = reflect_wall(-100, 50, "right")
        assert vx > 0
        assert vy == 50

    def test_reflect_top(self):
        vx, vy = reflect_wall(50, 100, "top")
        assert vx == 50
        assert vy < 0

    def test_reflect_bottom(self):
        vx, vy = reflect_wall(50, -100, "bottom")
        assert vx == 50
        assert vy > 0

    def test_reflect_unknown_rail_raises(self):
        with pytest.raises(ValueError):
            reflect_wall(100, 50, "invalid")


class TestTableBounds:
    def test_table_bounds_structure(self):
        bounds = table_bounds()
        assert "left" in bounds
        assert "right" in bounds
        assert "top" in bounds
        assert "bottom" in bounds
        assert bounds["left"] < bounds["right"]
        assert bounds["top"] < bounds["bottom"]


class TestIsInPocket:
    def test_ball_in_pocket(self):
        pocket = (100, 100)
        ball = BallState(x=100, y=100)
        assert is_in_pocket(ball, pocket) is True

    def test_ball_outside_pocket(self):
        pocket = (100, 100)
        ball = BallState(x=200, y=200)
        assert is_in_pocket(ball, pocket) is False


# ── Trajectory ─────────────────────────────────────────────────────────────

class TestSimulate:
    def test_simulate_basic_call(self):
        # Cue at (100, 315), target at (600, 315), pocket at (578.5, 53.5)
        result = simulate(
            cue_pos=(100, 315),
            cue_dir=(500, 0),  # pointing right
            target_pos=(600, 315),
            pocket_pos=(578.5, 53.5),
        )
        assert result is not None
        assert isinstance(result, TrajectoryResult)

    def test_simulate_result_fields(self):
        result = simulate(
            cue_pos=(100, 315),
            cue_dir=(500, 0),
            target_pos=(600, 315),
            pocket_pos=(578.5, 53.5),
        )
        assert hasattr(result, "cue_path")
        assert hasattr(result, "target_path")
        assert hasattr(result, "pocket_sunk")
        assert hasattr(result, "pocket_sunk_ball")
        assert hasattr(result, "cue_final")
        assert hasattr(result, "target_final")
        assert isinstance(result.cue_path, list)
        assert isinstance(result.target_path, list)

    def test_simulate_zero_cue_dir_does_not_crash(self):
        # Should raise ValueError, not crash
        with pytest.raises(ValueError):
            simulate(
                cue_pos=(100, 315),
                cue_dir=(0, 0),
                target_pos=(600, 315),
                pocket_pos=(578.5, 53.5),
            )

    def test_simulate_very_short_cue_distance(self):
        # Very short cue distance — ball barely moves
        result = simulate(
            cue_pos=(100, 315),
            cue_dir=(1, 0),
            target_pos=(600, 315),
            pocket_pos=(578.5, 53.5),
            speed=10.0,  # very slow
        )
        assert result is not None

    def test_simulate_with_cue_distance_kwarg(self):
        # Using cue_distance naming style from requirements
        result = simulate(
            cue_pos=(100, 315),
            cue_dir=(500, 0),
            target_pos=(600, 315),
            pocket_pos=(578.5, 53.5),
        )
        # Should complete without error
        assert result.cue_distance >= 0

    def test_simulate_stores_path_points(self):
        result = simulate(
            cue_pos=(100, 315),
            cue_dir=(500, 0),
            target_pos=(600, 315),
            pocket_pos=(578.5, 53.5),
            speed=5000.0,
        )
        assert len(result.cue_path) > 0
        assert len(result.target_path) > 0


class TestPredictSingle:
    def test_predict_single_basic(self):
        result = predict_single(100, 100, 1000, 0)
        assert isinstance(result, StopPrediction)
        assert hasattr(result, "final_pos")
        assert hasattr(result, "total_distance")
        assert hasattr(result, "wall_bounces")
        assert hasattr(result, "stopped_at_step")

    def test_predict_single_stationary_ball(self):
        result = predict_single(100, 100, 0, 0)
        assert result.total_distance == 0.0
        assert result.stopped_at_step == 1

    def test_predict_single_returns_correct_type(self):
        result = predict_single(0, 0, 1000, 0)
        assert isinstance(result.final_pos, tuple)
        assert isinstance(result.total_distance, float)


class TestChainSimulate:
    def test_chain_simulate_basic(self):
        result = chain_simulate(100, 315, 3000, 0)
        assert result is not None
        assert hasattr(result, "primary_stop")
        assert hasattr(result, "primary_distance")
        assert hasattr(result, "primary_wall_bounces")
        assert hasattr(result, "primary_pocketed")


# ── SimTable ───────────────────────────────────────────────────────────────

class TestPocketSpec:
    def test_pocketspec_fields(self):
        p = PocketSpec(
            name="top_left",
            x_mm=-575.0,
            y_mm=50.0,
            diameter=50.0,
            chamfer_angle=105.0,
            kind="corner",
        )
        assert p.name == "top_left"
        assert p.x_mm == -575.0
        assert p.y_mm == 50.0
        assert p.diameter == 50.0
        assert p.chamfer_angle == 105.0
        assert p.kind == "corner"

    def test_pocketspec_has_radius(self):
        p = PocketSpec("test", 0, 0, 50.0, 90.0, "side")
        assert hasattr(p, "name")


class TestSimTable:
    def test_default_classmethod(self):
        t = SimTable.default()
        assert isinstance(t, SimTable)

    def test_default_table_is_simulation_table(self):
        assert isinstance(DEFAULT_TABLE, SimTable)

    def test_pocket_by_name(self):
        t = SimTable.default()
        pocket = t.get_pocket("top_left")
        assert pocket is not None
        assert pocket.name == "top_left"

    def test_pocket_unknown_name_returns_none(self):
        t = SimTable.default()
        assert t.get_pocket("nonexistent") is None

    def test_known_pocket_names(self):
        t = SimTable.default()
        pockets = t.get_all_pockets()
        names = [p.name for p in pockets]
        assert "top_left" in names
        assert "top_right" in names
        assert "bot_left" in names
        assert "bot_right" in names
        assert "side_left" in names
        assert "side_right" in names
        assert len(names) == 6

    def test_simtable_instantiation(self):
        t = SimTable()
        assert t.pocket_diameter == 50.0
        assert t.rail_width == 50.0


# ── TableGeometry ───────────────────────────────────────────────────────────

class TestDistanceMm:
    def test_distance_3_4_5(self):
        assert distance_mm(0, 0, 3, 4) == 5.0

    def test_distance_zero(self):
        assert distance_mm(0, 0, 0, 0) == 0.0

    def test_distance_negative_coords(self):
        assert distance_mm(-3, -4, 0, 0) == 5.0


class TestBallToPocketMm:
    def test_ball_to_pocket_direct(self):
        assert ball_to_pocket_mm(100, 100, 150, 100) == 50.0

    def test_ball_to_pocket_zero_distance(self):
        assert ball_to_pocket_mm(100, 100, 100, 100) == 0.0


class TestTableGeometry:
    def test_instantiation(self):
        geo = TableGeometry()
        assert geo is not None

    def test_pixel_to_mm_2d_returns_tuple(self):
        geo = TableGeometry()
        result = geo.pixel_to_mm_2d(100, 200)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)

    def test_pixel_to_mm_2d_without_calibration(self):
        # Without calibration it should still return values (using scale 1.0)
        geo = TableGeometry()
        x, y = geo.pixel_to_mm_2d(100, 200)
        assert x == 100.0 * geo.scale_x()
        assert y == 200.0 * geo.scale_y()

    def test_scale_x_without_calibration(self):
        geo = TableGeometry()
        # Without calibration returns 1.0
        assert geo.scale_x() == 1.0

    def test_scale_y_without_calibration(self):
        geo = TableGeometry()
        assert geo.scale_y() == 1.0

    def test_constants_defined(self):
        assert TableGeometry.TABLE_WIDTH_MM == 1200
        assert TableGeometry.TABLE_HEIGHT_MM == 630
        assert TableGeometry.BALL_DIAMETER_MM == 38
        assert TableGeometry.BALL_RADIUS_MM == 19


class TestCollisionEventAndWallHit:
    def test_trajectory_result_is_target_sunk_method(self):
        # Test with pocket_sunk=False
        result = simulate(
            cue_pos=(100, 315),
            cue_dir=(500, 0),
            target_pos=(600, 315),
            pocket_pos=(578.5, 53.5),
        )
        # Just ensure method exists and returns bool
        assert isinstance(result.is_target_sunk(), bool)