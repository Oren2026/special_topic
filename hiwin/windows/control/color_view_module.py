"""
windows/control/color_view_module.py
顏色視圖模組（COLOR_VIEW 模式）

職責：
1. 讀取 windows/calib/color_ranges.yaml
2. 提供 Tkinter 拖曳介面（Hue/Sat/Val slider）
3. 即時 Preview：畫面上標記符合目前參數的球
4. 拖曳結束後寫回 YAML

資源隔離：
- 只在 COLOR_VIEW 模式由 StateMachine 動態 import
"""

import cv2
import numpy as np
import yaml
import os
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None


# ── 顏色名稱 ────────────────────────────────────────────────────────────────
NUMBER_TO_NAME = {
    0: "cue_ball", 1: "yellow", 2: "blue", 3: "red", 4: "purple",
    5: "orange", 6: "green", 7: "maroon", 8: "black", 9: "stripe_yellow",
}


class ColorViewModule:
    """
    COLOR_VIEW 拖曳調整介面

    使用方式：
    1. start_view() → 開啟調整視窗（Toplevel）
    2. 使用者拖曳 slider 即時更新參數
    3. 關閉視窗時自動寫回 YAML
    """

    def __init__(self, vision, hmi):
        """
        vision: BilliardVision 實例
        hmi: HMI 實例（用於更新相機疊加層）
        """
        self._vision = vision
        self._hmi = hmi
        self._yaml_path = self._get_yaml_path()
        self._data: dict = {}
        self._selected_ball: int = 1  # 目前編輯的球號
        self._window: Optional[object] = None  # Toplevel 視窗
        self._sliders: dict = {}  # ball_number -> {hue_low, hue_high, sat_low, ...}

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def start_view(self):
        """啟動調整視窗"""
        if tk is None:
            print("[ColorView] tkinter 不可用")
            return

        self._load_yaml()
        self._build_window()

    def get_overlay(self, frame) -> np.ndarray:
        """
        在目前 frame 上繪製 Preview 疊加層
        回傳加上標記的 frame（不修改原圖）
        """
        if self._data.get("balls") is None:
            return frame

        result = frame.copy()
        (ret_t, frame_t), _ = self._vision.get_raw_frames()
        if not ret_t:
            return result

        hsv = cv2.cvtColor(frame_t, cv2.COLOR_BGR2HSV)
        balls = self._data["balls"]

        for number, info in balls.items():
            if number == "cue_ball":
                # 白球用亮度判斷
                lower = np.array([0, 0, 180])
                upper = np.array([180, 30, 255])
            else:
                h_low = info.get("hue_low", 0)
                h_high = info.get("hue_high", 180)
                if h_low > h_high:
                    # 跨 Hue=0 邊界（紅色）
                    lower = np.array([0, info.get("sat_low", 0), info.get("val_low", 0)])
                    upper = np.array([h_high, info.get("sat_high", 255), info.get("val_high", 255)])
                else:
                    lower = np.array([h_low, info.get("sat_low", 0), info.get("val_low", 0)])
                    upper = np.array([h_high, info.get("sat_high", 255), info.get("val_high", 255)])

            mask = cv2.inRange(hsv, lower, upper)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 50:
                    continue
                try:
                    (cx, cy), _ = cv2.minEnclosingCircle(cnt)
                    cv2.circle(result, (int(cx), int(cy)), 8, (0, 255, 0), 2)
                    cv2.putText(result, f"#{info.get('number', '?')}", (int(cx) - 10, int(cy) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                except Exception:
                    continue

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
        """載入 YAML 參數"""
        try:
            with open(self._yaml_path, "r") as f:
                self._data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self._data = {"balls": {}, "version": "1.0", "updated_at": None}

    def _save_yaml(self):
        """寫回 YAML"""
        try:
            with open(self._yaml_path, "w") as f:
                yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)
            print(f"[ColorView] 已寫入 {self._yaml_path}")
        except Exception as e:
            print(f"[ColorView] 寫入失敗: {e}")

    def _build_window(self):
        """建立調整視窗"""
        root = self._hmi._root
        win = tk.Toplevel(root)
        win.title("顏色校正 — 拖曳調整")
        win.geometry("500x600")
        win.resizable(False, False)

        self._window = win

        # 選擇球號
        tk.Label(win, text="選擇球號：", font=("Arial", 11, "bold")).pack(pady=(10, 5))
        ball_frame = tk.Frame(win)
        ball_frame.pack()
        for n in range(1, 10):
            name = NUMBER_TO_NAME.get(n, str(n))
            color_bg = _BALL_COLOR_BG.get(n, "#cccccc")
            b = tk.Button(ball_frame, text=str(n), width=3,
                          bg=color_bg, fg="white",
                          command=lambda num=n: self._select_ball(num))
            b.pack(side=tk.LEFT, padx=2)

        # 說明
        tk.Label(win, text="拖曳滑桿即時調整，關閉視窗自動儲存",
                 fg="gray", font=("Arial", 9)).pack(pady=5)

        # 參數區
        self._param_frame = tk.Frame(win)
        self._param_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self._build_sliders()

        # 關閉時寫入
        win.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sliders(self):
        """根據選中的球號建立滑桿"""
        for w in self._param_frame.winfo_children():
            w.destroy()
        self._sliders.clear()

        info = self._data.get("balls", {}).get(f"ball_{self._selected_ball}",
                 {"hue_low": 20, "hue_high": 40, "sat_low": 80, "sat_high": 255,
                  "val_low": 150, "val_high": 255})
        if self._selected_ball == 0:
            info = {"hue_low": 0, "hue_high": 180, "sat_low": 0, "sat_high": 30,
                    "val_low": 180, "val_high": 255}

        params = [
            ("Hue Low",  "hue_low",  0, 180, info.get("hue_low", 0)),
            ("Hue High", "hue_high", 0, 180, info.get("hue_high", 180)),
            ("Sat Low",  "sat_low",  0, 255, info.get("sat_low", 0)),
            ("Sat High", "sat_high", 0, 255, info.get("sat_high", 255)),
            ("Val Low",  "val_low",  0, 255, info.get("val_low", 0)),
            ("Val High", "val_high", 0, 255, info.get("val_high", 255)),
        ]

        for label_text, key, lo, hi, default in params:
            row = tk.Frame(self._param_frame)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label_text, width=10, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.IntVar(value=default)
            scale = tk.Scale(row, from_=lo, to=hi, orient=tk.HORIZONTAL,
                             variable=var, showvalue=True, width=8,
                             command=lambda _, k=key, v=var: self._on_slider(k, v))
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._sliders[key] = var

    def _select_ball(self, number: int):
        """切換編輯的球號"""
        # 先寫入當前球的參數
        self._write_current_ball()
        self._selected_ball = number
        self._build_sliders()

    def _on_slider(self, key: str, var: 'tk.IntVar'):
        """Slider 拖曳時更新內存（不寫入 YAML）"""
        pass  # 讀取時直接從 var 取值，無需主動更新

    def _write_current_ball(self):
        """將目前 sliders 的值寫入記憶體"""
        key = f"ball_{self._selected_ball}"
        if key not in self._data["balls"]:
            self._data["balls"][key] = {"number": self._selected_ball, "name": NUMBER_TO_NAME.get(self._selected_ball)}
        for k in ["hue_low", "hue_high", "sat_low", "sat_high", "val_low", "val_high"]:
            self._data["balls"][key][k] = self._sliders[k].get()

    def _on_close(self):
        """關閉視窗：寫入 YAML"""
        self._write_current_ball()
        self._save_yaml()
        self._window = None
        try:
            self._window.destroy()
        except Exception:
            pass

    def _get_yaml_path(self) -> str:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "calib", "color_ranges.yaml")


# 球號 → Tkinter 按鈕背景色（視覺輔助）
_BALL_COLOR_BG = {
    1: "#e6cc00",  # yellow
    2: "#0066cc",  # blue
    3: "#cc0000",  # red
    4: "#660099",  # purple
    5: "#ff6600",  # orange
    6: "#009933",  # green
    7: "#800000",  # maroon
    8: "#333333",  # black
    9: "#e6cc00",  # stripe yellow
}
