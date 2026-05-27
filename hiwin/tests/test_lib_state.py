"""tests/test_lib_state.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.state import State


class TestState:
    def test_idle_defined(self):
        assert hasattr(State, "IDLE")
        assert State.IDLE == "IDLE"

    def test_table_calib_exists(self):
        assert hasattr(State, "TABLE_CALIB")
        assert State.TABLE_CALIB == "TABLE_CALIB"

    def test_circle_calib_exists(self):
        assert hasattr(State, "CIRCLE_CALIB")
        assert State.CIRCLE_CALIB == "CIRCLE_CALIB"

    def test_color_calib_exists(self):
        assert hasattr(State, "COLOR_CALIB")
        assert State.COLOR_CALIB == "COLOR_CALIB"

    def test_color_view_exists(self):
        assert hasattr(State, "COLOR_VIEW")
        assert State.COLOR_VIEW == "COLOR_VIEW"

    def test_shape_view_exists(self):
        assert hasattr(State, "SHAPE_VIEW")
        assert State.SHAPE_VIEW == "SHAPE_VIEW"

    def test_play_test_exists(self):
        assert hasattr(State, "PLAY_TEST")
        assert State.PLAY_TEST == "PLAY_TEST"

    def test_break_test_exists(self):
        assert hasattr(State, "BREAK_TEST")
        assert State.BREAK_TEST == "BREAK_TEST"

    def test_compete_exists(self):
        assert hasattr(State, "COMPETE")
        assert State.COMPETE == "COMPETE"

    def test_state_identity(self):
        assert State.PLAY_TEST == State.PLAY_TEST

    def test_all_states_non_empty_strings(self):
        for attr in dir(State):
            if not attr.startswith("_"):
                val = getattr(State, attr)
                assert isinstance(val, str), f"{attr} is not a string"
                assert len(val) > 0, f"{attr} is empty"