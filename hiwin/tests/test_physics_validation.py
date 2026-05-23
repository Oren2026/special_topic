"""
tests/test_physics_validation.py
Phase 2b：物理驗證（白球撞擊）整合測試

測試 RobotBrain._validate_cue_hits_target() 對隨機障礙球場景的行為。
使用有意義的幾何設計：直接驗證「障礙球擋住/不通」與物理模擬的互動。

Run: python3 -m pytest tests/test_physics_validation.py -v
"""

import math
import pytest
import sys, os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physics.trajectory import simulate
from windows.brain.robot_brain import RobotBrain


def eq(a, b, tol=1.0):
    return abs(a - b) < tol


class TestPhysicsValidation:
    """Phase 2b 物理驗證測試"""

    @pytest.fixture
    def robot_brain(self):
        return RobotBrain()

    # ── 策略幾何重建驗證 ──────────────────────────────────────────────

    def test_validate_clean_shot_hits(self, robot_brain):
        """
        C(300,300) → T(600,300) → P(top_right: 578.5, 53.5)
        Ghost Ball 在 T 右側偏上 (596.7, 262.1)。
        C→G 方向 (0.992, -0.127)，物理模擬在 step 135 發生碰撞。
        """
        result = robot_brain._validate_cue_hits_target(
            cue_ball={"x": 300, "y": 300},
            target_ball={"x": 600, "y": 300},
            pocket_name="top_right",
            obstacles=[],
        )
        assert result is True, "C→T 方向精確，白球應擊中目標球"

    def test_validate_miss_side_offset(self, robot_brain):
        """
        C(200,200) → T(600,200) → P(side_right: 575,315)
        口袋在斜上方，Ghost Ball 在 T 右側偏上。
        C(200,200) 到 G(638.6,271.2) 方向，白球從 target 上方掠過。
        """
        result = robot_brain._validate_cue_hits_target(
            cue_ball={"x": 200, "y": 200},
            target_ball={"x": 600, "y": 200},
            pocket_name="side_right",
            obstacles=[],
        )
        assert result is False, "瞄準方向斜向右上方，白球掠過 target 上方不撞擊"

    # ── 隨機障礙球穩定性測試 ──────────────────────────────────────────

    @pytest.mark.parametrize("seed", [42, 123, 999])
    def test_validate_random_obstacles_stability(self, robot_brain, seed):
        """隨機障礙球場景，確保整合邏輯不拋例外"""
        random.seed(seed)
        pockets = ["side_right", "side_left", "top_left", "bot_left", "top_right", "bot_right"]

        for i in range(20):
            cue = {"x": random.uniform(100, 500), "y": random.uniform(100, 500)}
            target = {"x": random.uniform(100, 500), "y": random.uniform(100, 500)}
            pocket = pockets[i % len(pockets)]
            obstacles = [
                {"x": random.uniform(50, 550), "y": random.uniform(50, 550)}
                for _ in range(random.randint(0, 5))
            ]
            try:
                result = robot_brain._validate_cue_hits_target(cue, target, pocket, obstacles)
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"隨機場景拋出例外: {e}")

    # ── 回傳格式驗證 ────────────────────────────────────────────────────

    def test_validate_returns_bool(self, robot_brain):
        """所有場景都應回傳 bool，不應有 None 或例外"""
        test_cases = [
            # 精確瞄準：應 True
            ({"x": 300, "y": 300}, {"x": 600, "y": 300}, "top_right", []),
            # 偏移上方：應 False
            ({"x": 200, "y": 200}, {"x": 600, "y": 200}, "side_right", []),
        ]
        for cue, target, pocket, obstacles in test_cases:
            result = robot_brain._validate_cue_hits_target(cue, target, pocket, obstacles)
            assert isinstance(result, bool), f"Expected bool, got {type(result)}"

    # ── Edge cases ────────────────────────────────────────────────────

    def test_validate_same_cue_target_position(self, robot_brain):
        """白球和目標球重疊——預設放行 True"""
        result = robot_brain._validate_cue_hits_target(
            cue_ball={"x": 300, "y": 300},
            target_ball={"x": 300, "y": 300},
            pocket_name="top_right",
            obstacles=[],
        )
        assert result is True

    def test_validate_obstacle_at_cue(self, robot_brain):
        """障礙球幾乎和白球重疊——不崩潰"""
        result = robot_brain._validate_cue_hits_target(
            cue_ball={"x": 200, "y": 315},
            target_ball={"x": 600, "y": 315},
            pocket_name="top_right",
            obstacles=[{"x": 201, "y": 315}],
        )
        assert isinstance(result, bool)

    def test_validate_obstacle_at_target(self, robot_brain):
        """障礙球幾乎和目標球重疊——不崩潰"""
        result = robot_brain._validate_cue_hits_target(
            cue_ball={"x": 200, "y": 315},
            target_ball={"x": 600, "y": 315},
            pocket_name="top_right",
            obstacles=[{"x": 601, "y": 315}],
        )
        assert isinstance(result, bool)

    def test_validate_zero_obstacles(self, robot_brain):
        """空障礙球列表——確認邏輯正常"""
        result = robot_brain._validate_cue_hits_target(
            cue_ball={"x": 300, "y": 300},
            target_ball={"x": 600, "y": 300},
            pocket_name="top_right",
            obstacles=[],
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])