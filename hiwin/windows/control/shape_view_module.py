"""
windows/control/shape_view_module.py
球形視圖模組（SHAPE_VIEW 模式）

職責：
1. 讀取 windows/calib/ball_geometry.yaml
2. 提供 Tkinter 拖曳介面（ball_radius / scale 滑桿）
3. 即時 Preview：疊加目前 HoughCircles 會偵測到的圓
4. 拖曳結束後寫回 YAML

資源隔離：
- 只在 SHAPE_VIEW 模式由 StateMachine 動態 import
"""

import cv2
import numpy as np
import yaml
import os
from typing import Optional

try:
    import tkinter as tk
except ImportError:
    tk = None


class ShapeViewModule:
    """
    SHAPE_VIEW 拖曳調整介面

    使用方式：
    1. start_view() → 開啟調整視窗（Toplevel）
    2. 拖曳 scale / min_radius / max_radius 滑桿
    3. 關閉視窗時自動寫回 YAML
    """

    def __init__(self, vision, hmi):
        self._vision = vision
        self._hmi = hmi
        self._yaml_path = self._get_yaml_path()
        self._data: dict = {}
        self._window: Optional[object] = None
        self._sliders: dict = {}  # key -> IntVar

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def start_view(self):
        if tk is None:
            print("[ShapeView] tkinter 不可用")
            return
        self._load_yaml()
        self._build_window()

    def get_overlay(self, frame) -> np.ndarray:
        """
        在 frame 上繪製 HoughCircles 偵測範圍 Preview
        使用目前的 slider 值（scale + min/max_radius）計算覆蓋範圍
        """
        result = frame.copy()
        (ret_t, frame_t), _ = self._vision.get_raw_frames()
        if not ret_t:
            return result

        gray = cv2.cvtColor(frame_t, cv2.COLOR_BGR2GRAY)
        blurred = cv2.medianBlur(gray, 5)

        min_r = self._data.get("hough_min_radius", 13)
        max_r = self._data.get("hough_max_radius", 35)

        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1,
            minDist=40, param1=50, param2=30,
            minRadius=max(1, min_r), maxRadius=max_r
        )

        if circles is not None:
            for c in circles[0]:
                cv2.circle(result, (int(c[0]), int(c[1])), int(c[2]), (0, 255, 0), 2)
                cv2.drawMarker(result, (int(c[0]), int(c[1])),
                                (0, 255, 0), cv2.MARKER_CROSS, 10, 1)

        # 顯示目前參數文字
        h, w = result.shape[:2]
        cv2.putText(result, f"minR={min_r} maxR={max_r}",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return result

    def reset(self):
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
        self._window = None

    # ── 內部 ─────────────────────────────────────────────────────────────────

    def _load_yaml(self):
        try:
            with open(self._yaml_path, "r") as f:
                self._data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self._data = {
                "ball_diameter_mm": 38, "ball_radius_mm": 19,
                "scale_x": None, "scale_y": None,
                "hough_min_radius": 13, "hough_max_radius": 35,
            }

    def _save_yaml(self):
        try:
            with open(self._yaml_path, "w") as f:
                yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)
            print(f"[ShapeView] 已寫入 {self._yaml_path}")
        except Exception as e:
            print(f"[ShapeView] 寫入失敗: {e}")

    def _build_window(self):
        root = self._hmi._root
        win = tk.Toplevel(root)
        win.title("球形校正 — 拖曳調整")
        win.geometry("450x350")
        win.resizable(False, False)
        self._window = win

        tk.Label(win, text="球形幾何參數調整", font=("Arial", 13, "bold")).pack(pady=(15, 5))
        tk.Label(win, text="拖曳滑桿，關閉視窗自動儲存",
                 fg="gray", font=("Arial", 9)).pack(pady=(0, 10))

        self._param_frame = tk.Frame(win)
        self._param_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        self._build_sliders()

        # 即時預覽按鈕
        tk.Button(win, text="🔄 更新預覽", command=self._refresh_preview,
                  bg="#e3f2fd", width=20).pack(pady=5)

        win.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sliders(self):
        for w in self._param_frame.winfo_children():
            w.destroy()
        self._sliders.clear()

        params = [
            ("Ball 直徑 (mm)",  "ball_diameter_mm", 30, 50,
             self._data.get("ball_diameter_mm", 38)),
            ("Scale X (mm/px)", "scale_x", 0.1, 2.0,
             self._data.get("scale_x") or 0.5),
            ("Hough Min R",     "hough_min_radius", 1, 50,
             self._data.get("hough_min_radius", 13)),
            ("Hough Max R",     "hough_max_radius", 10, 80,
             self._data.get("hough_max_radius", 35)),
        ]

        for label_text, key, lo, hi, default in params:
            row = tk.Frame(self._param_frame)
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=label_text, width=18, anchor=tk.W).pack(side=tk.LEFT)

            if key in ("scale_x",):
                var = tk.DoubleVar(value=float(default))
            else:
                var = tk.IntVar(value=int(default))

            scale = tk.Scale(row, from_=lo, to=hi, orient=tk.HORIZONTAL,
                             variable=var, showvalue=True, width=8,
                             resolution=0.01 if isinstance(default, float) else 1,
                             command=lambda _, k=key, v=var: self._on_slider(k, v))
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._sliders[key] = var

    def _on_slider(self, key: str, var):
        val = var.get()
        self._data[key] = round(val, 4) if isinstance(val, float) else int(val)
        # 即時更新 ball_radius_mm
        if key == "ball_diameter_mm":
            self._data["ball_radius_mm"] = round(val / 2, 2)

    def _refresh_preview(self):
        """強致刷新 HMI 的相機疊加層（目前由 HMI 自行處理）"""
        pass

    def _on_close(self):
        self._save_yaml()
        self._window = None
        try:
            self._window.destroy()
        except Exception:
            pass

    def _get_yaml_path(self) -> str:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "calib", "ball_geometry.yaml")
