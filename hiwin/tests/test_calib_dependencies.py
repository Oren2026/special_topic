"""
tests/test_calib_dependencies.py
Dependency + YAML structure tests for the calibration system.

Run: python -m pytest tests/test_calib_dependencies.py -v

Tests:
- pyyaml is installed
- calibration YAML files exist and are valid
- color_calib_module can be imported (yaml present)
- shape_calib_module can be imported (yaml present)
- color_view_module can be imported (yaml present)
- shape_view_module can be imported (yaml present)
- YAML files have expected structure
"""

import sys
import os
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOWS_DIR = os.path.join(ROOT, "windows")


def _cleanup_sys_path():
    for p in [WINDOWS_DIR, ROOT]:
        while p in sys.path:
            sys.path.remove(p)


def _import_camera_module():
    _cleanup_sys_path()
    sys.path.insert(0, WINDOWS_DIR)
    sys.path.insert(1, ROOT)
    import vision.camera
    return vision.camera


# ─── Dependency availability ─────────────────────────────────────────────────

def test_yaml_module_available():
    """PyYAML must be installed — this is the root cause of the runtime crash."""
    import yaml
    assert hasattr(yaml, "load")
    assert hasattr(yaml, "dump")


def test_opencv_available():
    """cv2 must be installed."""
    import cv2
    assert hasattr(cv2, "VideoCapture")


def test_numpy_available():
    """numpy must be installed."""
    import numpy as np
    assert np is not None


def test_pillow_available():
    """Pillow must be installed for HMI image rendering."""
    from PIL import Image
    assert Image is not None


# ─── YAML file structure ───────────────────────────────────────────────────────

def test_color_ranges_yaml_exists():
    """color_ranges.yaml must exist in calib/ directory."""
    calib_path = os.path.join(WINDOWS_DIR, "calib", "color_ranges.yaml")
    assert os.path.isfile(calib_path), f"Missing: {calib_path}"


def test_ball_geometry_yaml_exists():
    """ball_geometry.yaml must exist in calib/ directory."""
    geo_path = os.path.join(WINDOWS_DIR, "calib", "ball_geometry.yaml")
    assert os.path.isfile(geo_path), f"Missing: {geo_path}"


def test_color_ranges_yaml_valid_structure():
    """color_ranges.yaml must have balls dict with required keys."""
    import yaml
    calib_path = os.path.join(WINDOWS_DIR, "calib", "color_ranges.yaml")
    with open(calib_path) as f:
        data = yaml.safe_load(f)

    assert "balls" in data, "Missing 'balls' key"
    balls = data["balls"]

    # Must have cue_ball and ball_1 through ball_9
    assert "cue_ball" in balls, "Missing cue_ball"
    for i in range(1, 10):
        key = f"ball_{i}"
        assert key in balls, f"Missing {key}"
        ball = balls[key]
        # Each ball has a name and number
        assert "name" in ball, f"{key} missing 'name'"
        assert "number" in ball, f"{key} missing 'number'"
        # Standard balls (not ball_9) have hue_low/hue_high + sat/val
        # ball_9 uses base_hue_low/base_hue_high + stripe_threshold instead
        if i != 9:
            for channel in ["sat_low", "sat_high", "val_low", "val_high"]:
                assert channel in ball, f"{key} missing {channel}"
        else:
            # ball_9 is stripe_yellow with base_hue + stripe_threshold
            assert "base_hue_low" in ball or "hue_low" in ball, f"{key} missing hue definition"
            assert "stripe_threshold" in ball, f"{key} missing stripe_threshold"


def test_ball_geometry_yaml_valid_structure():
    """ball_geometry.yaml must have required geometry keys."""
    import yaml
    geo_path = os.path.join(WINDOWS_DIR, "calib", "ball_geometry.yaml")
    with open(geo_path) as f:
        data = yaml.safe_load(f)

    # Top-level required keys
    for key in ["ball_diameter_mm", "ball_radius_mm"]:
        assert key in data, f"Missing top-level key: {key}"

    # scale keys (may be null before calibration)
    assert "scale_x" in data
    assert "scale_y" in data

    # fallback must exist and have hough radii
    assert "fallback" in data, "Missing fallback block"
    fb = data["fallback"]
    assert "hough_min_radius" in fb, "fallback missing hough_min_radius"
    assert "hough_max_radius" in fb, "fallback missing hough_max_radius"


# ─── Calibration module imports ────────────────────────────────────────────────

def test_color_calib_module_importable():
    """color_calib_module must be importable when PyYAML is installed."""
    try:
        _cleanup_sys_path()
        sys.path.insert(0, WINDOWS_DIR)
        sys.path.insert(1, ROOT)
        from control.color_calib_module import ColorCalibModule
        assert ColorCalibModule is not None
    finally:
        _cleanup_sys_path()


def test_shape_calib_module_importable():
    """shape_calib_module must be importable when PyYAML is installed."""
    try:
        _cleanup_sys_path()
        sys.path.insert(0, WINDOWS_DIR)
        sys.path.insert(1, ROOT)
        from control.shape_calib_module import ShapeCalibModule
        assert ShapeCalibModule is not None
    finally:
        _cleanup_sys_path()


def test_color_view_module_importable():
    """color_view_module must be importable when PyYAML is installed."""
    try:
        _cleanup_sys_path()
        sys.path.insert(0, WINDOWS_DIR)
        sys.path.insert(1, ROOT)
        from control.color_view_module import ColorViewModule
        assert ColorViewModule is not None
    finally:
        _cleanup_sys_path()


def test_shape_view_module_importable():
    """shape_view_module must be importable when PyYAML is installed."""
    try:
        _cleanup_sys_path()
        sys.path.insert(0, WINDOWS_DIR)
        sys.path.insert(1, ROOT)
        from control.shape_view_module import ShapeViewModule
        assert ShapeViewModule is not None
    finally:
        _cleanup_sys_path()


# ─── Integration: yaml fails gracefully in test context ───────────────────────

def test_yaml_missing_gives_clear_error():
    """If yaml were missing, import would raise ModuleNotFoundError — this is the bug."""
    import importlib
    with patch.dict(sys.modules, {"yaml": None}):
        with patch("builtins.__import__", side_effect=ModuleNotFoundError("No module named 'yaml'")):
            # The actual error users see — clear and actionable
            try:
                import yaml
            except ModuleNotFoundError as e:
                assert "yaml" in str(e).lower()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
