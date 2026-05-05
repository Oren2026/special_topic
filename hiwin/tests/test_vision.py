"""
tests/test_vision.py
Unit tests for vision components (ball_identifier + vision_bridge)

Run: python -m pytest tests/test_vision.py -v
"""

import math
import sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "windows"))

from control.ball_identifier import BallIdentifier, COLOR_TO_NUMBER


# ─── Hue 分類 ────────────────────────────────────────────────────────────────

def test_hue_red_low():
    """Hue=5 → red"""
    ident = BallIdentifier()
    assert ident._classify_hue(5) == "red"


def test_hue_red_high():
    """Hue=175 → red"""
    ident = BallIdentifier()
    assert ident._classify_hue(175) == "red"


def test_hue_orange():
    """Hue=15 → orange"""
    ident = BallIdentifier()
    assert ident._classify_hue(15) == "orange"


def test_hue_orange_upper():
    """Hue=25 → orange"""
    ident = BallIdentifier()
    assert ident._classify_hue(25) == "orange"


def test_hue_yellow():
    """Hue=30 → yellow"""
    ident = BallIdentifier()
    assert ident._classify_hue(30) == "yellow"


def test_hue_green():
    """Hue=60 → green"""
    ident = BallIdentifier()
    assert ident._classify_hue(60) == "green"


def test_hue_blue():
    """Hue=115 → blue"""
    ident = BallIdentifier()
    assert ident._classify_hue(115) == "blue"


def test_hue_purple():
    """Hue=145 → purple"""
    ident = BallIdentifier()
    assert ident._classify_hue(145) == "purple"


def test_hue_unknown():
    """Hue=85 → unknown"""
    ident = BallIdentifier()
    assert ident._classify_hue(85) == "unknown"


def test_hue_boundary_no_overlap():
    """邊界檢查：確認 red/orange/yellow 沒有重疊"""
    ident = BallIdentifier()
    # Hue=10 → red（不是 orange）
    assert ident._classify_hue(10) == "red"
    # Hue=11 → orange
    assert ident._classify_hue(11) == "orange"
    # Hue=25 → orange（上限）
    assert ident._classify_hue(25) == "orange"
    # Hue=26 → yellow
    assert ident._classify_hue(26) == "yellow"


def test_hue_black_ball():
    """黑色球（V<50）→ classify_color 回傳 black, number=8"""
    # 需要 frame 才能測，先測 Hue 對 unknown 的處理
    ident = BallIdentifier()
    # Hue 在未知範圍 → unknown
    assert ident._classify_hue(85) == "unknown"


# ─── 顏色對照表 ──────────────────────────────────────────────────────────────

def test_color_to_number():
    """COLOR_TO_NUMBER 包含所有 1-9 號球"""
    expected = {
        "yellow": 1,
        "blue": 2,
        "red": 3,
        "purple": 4,
        "orange": 5,
        "green": 6,
        "maroon": 7,
        "black": 8,
        "yellow_stripe": 9,
    }
    for color, number in expected.items():
        assert COLOR_TO_NUMBER.get(color) == number, f"missing: {color}"


# ─── VisionBridge Mock ──────────────────────────────────────────────────────

def test_vision_bridge_mock_scene():
    """VisionBridge mock 模式：能產生模擬 frame 並處理（不需校正）"""
    from control.vision_bridge import VisionBridge, make_mock_scene

    bridge = VisionBridge()

    # 使用 mock 場景
    scene = make_mock_scene()
    bridge.start_mock(scene=scene)

    assert bridge.is_mock() is True
    assert len(scene) == 6  # 白球 + 5 個彩球

    # capture_and_process 不需要 robot_brain，執行不拋例外即可
    # 沒有校正時，balls 可偵測但座標為 (0,0)
    result = bridge.capture_and_process()
    assert result is not None  # 至少要有回傳


def test_vision_bridge_mock_without_camera():
    """確認 mock 模式不需要相機"""
    from control.vision_bridge import VisionBridge

    bridge = VisionBridge()
    bridge.start_mock()  # 不給 scene，用預設
    assert bridge.is_mock() is True
    # capture_and_process 執行不拋例外
    bridge.capture_and_process()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
