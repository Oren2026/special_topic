"""
tests/test_camera.py
Unit tests for windows/vision/camera.py — BilliardVision graceful degradation

Run: python -m pytest tests/test_camera.py -v
     python -m pytest tests/ -v  (full suite)

Key scenarios tested:
- Invalid camera indices → no crash (graceful degradation)
- Mixed success/failure camera open → partial init OK
- get_raw_frames with None caps → returns (False, None)
- release() with None caps → no exception
- VideoCapture throws exception → caught, no crash
"""

import sys
import os
import importlib
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOWS_DIR = os.path.join(ROOT, "windows")


def _reimport_config():
    """
    Force reimport of config so camera.py gets windows/config.py.
    camera.py does: sys.path.insert(0, ROOT) then import config.
    Without reload, sys.modules['config'] may be a stale physics-workspace config
    that lacks FOURCC / CAM_TOP_ID.
    """
    # Ensure windows/ is first, then ROOT
    for p in [WINDOWS_DIR, ROOT]:
        if p in sys.path:
            sys.path.remove(p)
    sys.path.insert(0, WINDOWS_DIR)
    sys.path.insert(1, ROOT)

    # Reload so camera.py sees windows/config.py
    if "config" in sys.modules:
        import config as _cfg
        importlib.reload(_cfg)
    else:
        import config

    return sys.modules["config"]


def _import_camera_module():
    """Import vision.camera with correct sys.path, return the module."""
    _reimport_config()
    sys.path.insert(0, WINDOWS_DIR)
    sys.path.insert(1, ROOT)
    import vision.camera
    return vision.camera


def _cleanup_sys_path():
    """Remove windows/ and ROOT from sys.path front to avoid polluting other tests."""
    for p in [WINDOWS_DIR, ROOT]:
        while p in sys.path:
            sys.path.remove(p)


# ─── Init tests ───────────────────────────────────────────────────────────────

def test_init_both_cameras_invalid_no_crash():
    """Both camera indices are invalid → BilliardVision init must not raise."""
    try:
        cam = _import_camera_module()
        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.return_value = MagicMock(isOpened=MagicMock(return_value=False))
            bv = cam.BilliardVision(top_id=99, side_id=88)
            assert bv.cap_top is None
            assert bv.cap_side is None
    finally:
        _cleanup_sys_path()


def test_init_first_camera_fails_second_succeeds():
    """First camera fails, second succeeds → partial init, no crash."""
    try:
        cam = _import_camera_module()
        mock_top = MagicMock(isOpened=MagicMock(return_value=False))
        mock_side = MagicMock(isOpened=MagicMock(return_value=True))
        mock_side.read.return_value = (True, MagicMock())

        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.side_effect = [mock_top, mock_side]
            bv = cam.BilliardVision(top_id=0, side_id=1)
            assert bv.cap_top is None
            assert bv.cap_side is not None
    finally:
        _cleanup_sys_path()


def test_init_video_capture_raises_exception():
    """VideoCapture throws exception during init → caught, no crash, caps are None."""
    try:
        cam = _import_camera_module()
        with patch("cv2.VideoCapture", side_effect=RuntimeError("Cannot open camera")):
            bv = cam.BilliardVision(top_id=0, side_id=1)
            assert bv.cap_top is None
            assert bv.cap_side is None
    finally:
        _cleanup_sys_path()


def test_init_config_defaults():
    """BilliardVision uses config.CAM_TOP_ID / CAM_SIDE_ID when no args given."""
    try:
        cfg = _reimport_config()
        cam = _import_camera_module()
        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.return_value = MagicMock(isOpened=MagicMock(return_value=False))
            bv = cam.BilliardVision()
            assert bv.top_id == cfg.CAM_TOP_ID
            assert bv.side_id == cfg.CAM_SIDE_ID
    finally:
        _cleanup_sys_path()


# ─── get_raw_frames tests ──────────────────────────────────────────────────────

def test_get_raw_frames_both_caps_none():
    """Both caps are None → get_raw_frames returns (False, None) for both."""
    try:
        cam = _import_camera_module()
        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.return_value = MagicMock(isOpened=MagicMock(return_value=False))
            bv = cam.BilliardVision(top_id=99, side_id=88)

            (ret_t, frame_t), (ret_s, frame_s) = bv.get_raw_frames()
            assert ret_t is False
            assert frame_t is None
            assert ret_s is False
            assert frame_s is None
    finally:
        _cleanup_sys_path()


def test_get_raw_frames_top_camera_only():
    """Top camera works, side is None → top returns frame, side returns (False, None)."""
    try:
        import numpy as np
        cam = _import_camera_module()
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_top = MagicMock()
        mock_top.isOpened.return_value = True
        mock_top.read.return_value = (True, fake_frame)
        mock_side = MagicMock(isOpened=MagicMock(return_value=False))

        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.side_effect = [mock_top, mock_side]
            bv = cam.BilliardVision(top_id=0, side_id=1)

            assert bv.cap_top is not None
            assert bv.cap_side is None  # Side failed to open

            (ret_t, frame_t), (ret_s, frame_s) = bv.get_raw_frames()
            assert ret_t is True
            assert frame_t is not None
            assert ret_s is False
            assert frame_s is None
    finally:
        _cleanup_sys_path()


def test_get_raw_frames_both_cameras_return_frames():
    """Both cameras return valid frames → both return (True, frame)."""
    try:
        import numpy as np
        cam = _import_camera_module()
        fake_frame_t = np.zeros((480, 640, 3), dtype=np.uint8)
        fake_frame_s = np.zeros((480, 640, 3), dtype=np.uint8)

        mock_top = MagicMock(isOpened=MagicMock(return_value=True),
                             read=MagicMock(return_value=(True, fake_frame_t)))
        mock_side = MagicMock(isOpened=MagicMock(return_value=True),
                              read=MagicMock(return_value=(True, fake_frame_s)))

        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.side_effect = [mock_top, mock_side]
            bv = cam.BilliardVision(top_id=0, side_id=1)

            (ret_t, frame_t), (ret_s, frame_s) = bv.get_raw_frames()
            assert ret_t is True and frame_t is not None
            assert ret_s is True and frame_s is not None
    finally:
        _cleanup_sys_path()


# ─── release tests ─────────────────────────────────────────────────────────────

def test_release_with_none_caps():
    """release() called when both caps are None → must not raise."""
    try:
        cam = _import_camera_module()
        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.return_value = MagicMock(isOpened=MagicMock(return_value=False))
            bv = cam.BilliardVision(top_id=99, side_id=88)
            bv.release()  # Must not raise
            assert bv.cap_top is None
            assert bv.cap_side is None
    finally:
        _cleanup_sys_path()


def test_release_with_open_caps():
    """release() called when caps are open → closes and sets to None."""
    try:
        cam = _import_camera_module()
        mock_top = MagicMock(isOpened=MagicMock(return_value=True))
        mock_side = MagicMock(isOpened=MagicMock(return_value=True))

        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.side_effect = [mock_top, mock_side]
            bv = cam.BilliardVision(top_id=0, side_id=1)

            bv.release()
            mock_top.release.assert_called_once()
            mock_side.release.assert_called_once()
            assert bv.cap_top is None
            assert bv.cap_side is None
    finally:
        _cleanup_sys_path()


# ─── Warning message test ──────────────────────────────────────────────────────

def test_camera_not_opened_warning_message(capsys):
    """Invalid camera → warning message printed."""
    try:
        cam = _import_camera_module()
        with patch("cv2.VideoCapture") as mock_cap:
            mock_cap.return_value = MagicMock(isOpened=MagicMock(return_value=False))
            bv = cam.BilliardVision(top_id=99, side_id=88)
            captured = capsys.readouterr()
            assert "無法開啟鏡頭" in captured.out or "id=99" in captured.out
    finally:
        _cleanup_sys_path()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
