"""tests/test_lib_vision.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.vision import params
from lib.vision.objects import BilliardBall, SimulationScene


class TestParams:
    def test_ball_diameter(self):
        assert params.BALL_DIAMETER == 38.0

    def test_pocket_diameter(self):
        assert params.POCKET_DIAMETER == 50.0

    def test_ball_radius(self):
        assert params.BALL_RADIUS == params.BALL_DIAMETER / 2

    def test_pocket_radius(self):
        assert params.POCKET_RADIUS == params.POCKET_DIAMETER / 2

    def test_table_width(self):
        assert params.TABLE_WIDTH == 1200

    def test_table_height(self):
        assert params.TABLE_HEIGHT == 630

    def test_ball_colors_keys(self):
        assert isinstance(params.BALL_COLORS, dict)
        assert "CUE_BALL" in params.BALL_COLORS
        assert "TARGET_BALL" in params.BALL_COLORS
        assert "POCKET" in params.BALL_COLORS


class TestBilliardBall:
    def test_create_cue_ball(self):
        ball = BilliardBall("CUE_BALL", 100, 200)
        assert ball.type == "CUE_BALL"
        assert ball.u == 100.0
        assert ball.v == 200.0

    def test_update_pos(self):
        ball = BilliardBall("TARGET_BALL", 50, 60)
        ball.update_pos(150, 250)
        assert ball.u == 150.0
        assert ball.v == 250.0


class TestSimulationScene:
    def test_empty_start(self):
        scene = SimulationScene()
        assert scene.balls == {}

    def test_add_ball(self):
        scene = SimulationScene()
        scene.add_or_update("CUE_BALL", 100, 200)
        ball = scene.get("CUE_BALL")
        assert ball is not None
        assert ball.type == "CUE_BALL"
        assert ball.u == 100.0
        assert ball.v == 200.0

    def test_update_ball(self):
        scene = SimulationScene()
        scene.add_or_update("CUE_BALL", 100, 200)
        scene.add_or_update("CUE_BALL", 300, 400)
        ball = scene.get("CUE_BALL")
        assert ball.u == 300.0
        assert ball.v == 400.0

    def test_get_returns_correct_ball(self):
        scene = SimulationScene()
        scene.add_or_update("TARGET_BALL", 500, 600)
        ball = scene.get("TARGET_BALL")
        assert ball is not None
        assert ball.type == "TARGET_BALL"
        assert ball.u == 500.0
        assert ball.v == 600.0

    def test_get_nonexistent_returns_none(self):
        scene = SimulationScene()
        result = scene.get("DOES_NOT_EXIST")
        assert result is None

    def test_get_all_data(self):
        scene = SimulationScene()
        scene.add_or_update("CUE_BALL", 100, 200)
        scene.add_or_update("TARGET_BALL", 300, 400)
        data = scene.get_all_data()
        assert isinstance(data, list)
        assert len(data) == 2
        types = {d["type"] for d in data}
        assert "CUE_BALL" in types
        assert "TARGET_BALL" in types
        for d in data:
            assert "type" in d
            assert "u" in d
            assert "v" in d

    def test_set_pockets(self):
        scene = SimulationScene()
        pockets = {
            "POCKET_1": [100, 200],
            "POCKET_2": [300, 400],
        }
        scene.set_pockets(pockets)
        assert len(scene._pockets) == 2
        assert scene._pockets[0]["name"] == "POCKET_1"
        assert scene._pockets[0]["u"] == 100.0
        assert scene._pockets[0]["v"] == 200.0

    def test_set_calibration_points(self):
        scene = SimulationScene()
        points = [[10, 20], [30, 40], [50, 60], [70, 80]]
        scene.set_calibration_points(points)
        assert scene._calib_points == points

    def test_scene_balls_starts_empty(self):
        scene = SimulationScene()
        assert scene.balls == {}