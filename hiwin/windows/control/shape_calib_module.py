"""
windows/control/shape_calib_module.py
球形校正模組（CIRCLE_CALIB 模式）

職責：
1. 點擊球取樣 → 自動偵測圓形邊界
2. 計算球半徑 pixel → 由已知球徑（38mm）推算 scale_x / scale_y
3. 寫入 windows/calib/ball_geometry.yaml

資源隔離：
- 只在 CIRCLE_CALIB 模式由 StateMachine 動態 import
- 不在 PLAY_TEST / COMPETE 的 import chain 中
"""

import cv2
import numpy as np
import yaml
import os
import datetime
import math
from typing import Optional

# 物理球徑（mm）
BALL_DIAMETER_MM = 38.0
BALL_RADIUS_MM = BALL_DIAMETER_MM / 2.0  # 19mm


class ShapeCalibModule:
    """
    球形校正控制邏輯

    流程：
    1. 使用者點擊畫面中的球
    2. 系統在點擊位置周圍 ROI 找圓形邊界
    3. 記錄半徑 pixel，累積多個樣本取平均
    4. 由 38mm 球徑計算 scale_x / scale_y
    5. 寫入 windows/calib/ball_geometry.yaml

    取樣策略（與 COLOR_CALIB 相同的「一樣取樣」）：
    - 使用者在球上任意點一下
    - 系統找到該球的準確圓心和半徑
    """

    def __init__(self, vision):
        """
        vision: BilliardVision 實例（用於取 frame）
        """
        self._vision = vision
        # 半徑樣本（pixel）：每次點擊量到的半徑
        self._radius_samples: list[float] = []
        self._last_center: Optional[tuple[float, float]] = None
        self._last_radius: Optional[float] = None

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def handle_click(self, u: int, v: int) -> dict:
        """
        處理點擊：找球、量半徑、存樣本
        回傳：{ok, radius_pixel, avg_radius, count, complete}
        """
        # 抓 frame
        (ret_t, frame_t), _ = self._vision.get_raw_frames()
        if not ret_t:
            return {"ok": False, "error": "無法取得相機畫面"}

        gray = cv2.cvtColor(frame_t, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # 以點擊為中心，取局部 ROI（半徑 50px 範圍）
        roi_radius = 60
        x1 = max(0, u - roi_radius)
        x2 = min(w, u + roi_radius)
        y1 = max(0, v - roi_radius)
        y2 = min(h, v + roi_radius)
        roi = gray[y1:y2, x1:x2]

        if roi.size == 0:
            return {"ok": False, "error": "ROI 無效"}

        # Canny 邊緣偵測
        blurred = cv2.medianBlur(roi, 3)
        edges = cv2.Canny(blurred, 50, 150)

        # 找輪廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 在 ROI 範圍內找通過點擊位置的輪廓
        click_in_roi = (u - x1, v - y1)
        best_circle = None
        best_dist = float("inf")

        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 3, True)
            if len(approx) < 5:
                continue
            try:
                (cx, cy), cr = cv2.minEnclosingCircle(approx)
                # 檢查輪廓是否通過點擊位置（點擊在半徑範圍內）
                dist = math.hypot(cx - click_in_roi[0], cy - click_in_roi[1])
                if dist < cr and dist < best_dist:
                    best_dist = dist
                    best_circle = (cx + x1, cy + y1, cr)  # 轉回全域座標
            except Exception:
                continue

        if best_circle is None:
            return {"ok": False, "error": "找不到圓形，請在球上清晰處點擊"}

        cx, cy, cr = best_circle
        self._last_center = (cx, cy)
        self._last_radius = cr
        self._radius_samples.append(cr)

        count = len(self._radius_samples)
        avg_r = sum(self._radius_samples) / count
        scale = BALL_DIAMETER_MM / (avg_r * 2)  # mm per pixel

        done = count >= 3  # 取 3 個樣本後自動完成
        if done:
            ok, msg = self._write_yaml()
            return {"complete": True, "ok": ok, "message": msg,
                    "avg_radius": avg_r, "scale_mm_per_pixel": scale, "samples": count}

        return {
            "ok": True,
            "radius_pixel": cr,
            "avg_radius": avg_r,
            "scale_mm_per_pixel": scale,
            "count": count,
            "complete": False,
        }

    def get_last_circle(self) -> Optional[tuple[float, float, float]]:
        """取得最後一次偵測到的圓 (cx, cy, radius)"""
        return (self._last_center[0], self._last_center[1], self._last_radius) if self._last_center else None

    def get_stats(self) -> dict:
        return {
            "samples": len(self._radius_samples),
            "avg_radius": sum(self._radius_samples) / len(self._radius_samples) if self._radius_samples else 0,
            "last_radius": self._last_radius,
        }

    def reset(self):
        self._radius_samples.clear()
        self._last_center = None
        self._last_radius = None

    # ── 寫入 YAML ────────────────────────────────────────────────────────────

    def _write_yaml(self) -> tuple[bool, str]:
        """
        將計算結果寫入 windows/calib/ball_geometry.yaml
        回傳：(ok, message)
        """
        try:
            avg_r = sum(self._radius_samples) / len(self._radius_samples)
            scale_x = BALL_DIAMETER_MM / (avg_r * 2)  # 假設 X/Y 解析度相同
            scale_y = BALL_DIAMETER_MM / (avg_r * 2)
            min_r = max(5, int(avg_r * 0.7))
            max_r = int(avg_r * 1.3)

            path = self._yaml_path()
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}

            data["updated_at"] = datetime.datetime.now().isoformat()
            data["ball_diameter_mm"] = BALL_DIAMETER_MM
            data["ball_radius_mm"] = BALL_RADIUS_MM
            data["scale_x"] = round(scale_x, 4)
            data["scale_y"] = round(scale_y, 4)
            data["hough_min_radius"] = min_r
            data["hough_max_radius"] = max_r
            data["avg_radius_pixel"] = round(avg_r, 2)
            data["sample_count"] = len(self._radius_samples)

            with open(path, "w") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

            return True, f"已寫入 {path}"
        except Exception as e:
            return False, f"寫入失敗: {e}"

    def _yaml_path(self) -> str:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "calib", "ball_geometry.yaml")
