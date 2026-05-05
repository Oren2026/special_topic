"""
windows/control/ball_identifier.py
單一球辨識 — 圓形偵測 + 顏色分類

Phase 1 核心模組：
1. HoughCircles 偵測圓形（形狀優先）
2. HSV 顏色分割（9號球規則）
3. 輸出 Ball 物件 {position, color, number, is_stripe}

依賴：cv2, numpy
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple


# ── 9號球顏色對照（Hue 範圍，HSV）─────────────────────────────────────────

COLOR_RANGES = {
    "yellow":  ( 25,  35),  # 球號 1
    "blue":    (100, 130),  # 球號 2
    "red":     (  0,  15),  # 球號 3（跨 Hue=0 邊界）
    "purple":  (130, 160),  # 球號 4
    "orange":  ( 10,  25),  # 球號 5
    "green":   ( 45,  75),  # 球號 6
    "maroon":  (  0,  10),  # 球號 7（暗紅）
    "black":   (  0, 180),  # 球號 8（黑色，用亮度判斷）
    # 球號 9 = 條紋黃色（與1號同色但條紋圖案）
}

NUMBER_TO_COLOR = {
    1: "yellow",
    2: "blue",
    3: "red",
    4: "purple",
    5: "orange",
    6: "green",
    7: "maroon",
    8: "black",
    9: "yellow_stripe",
}

COLOR_TO_NUMBER = {v: k for k, v in NUMBER_TO_COLOR.items()}


@dataclass
class DetectedBall:
    """偵測到的球"""
    u: float          # pixel x 中心
    v: float          # pixel y 中心
    radius: float      # 偵測半徑（pixel）
    color: str         # 顏色名稱
    number: int        # 球號（1-9）
    is_stripe: bool    # 是否為條紋球
    confidence: float  # 偵測置信度 0-1


class BallIdentifier:
    """
    單一球辨識 pipeline

    使用方式：
    1. set_frame(frame) — 餵入 BGR 畫面
    2. detect_circles() — HoughCircles 偵測圓形（半徑範圍由 TableGeometry 動態計算）
    3. classify_ball(u, v, radius) — 對特定位置做顏色分類
    4. detect_all() — 一次執行完整流程，回傳所有偵測到的球
    """

    # HoughCircles 固定參數
    HOUGH_PARAM1 = 50   # 邊緣偵測門檻
    HOUGH_PARAM2 = 30   # 圓心偵測門檻（越小越容易誤判）
    DIST_BETWEEN_CIRCLES = 40  # 兩圓最小距離

    # 條紋判斷參數
    STRIPE_BRIGHTNESS_DIFF = 30  # 邊緣vs中心亮度差閾值
    STRIPE_SATURATION_DIFF = 20  # 邊緣vs中心飽和度差閾值

    def __init__(self, table_geometry=None, hough_param1: int = None, hough_param2: int = None):
        self._frame: Optional[np.ndarray] = None
        self._gray: Optional[np.ndarray] = None
        self._hsv: Optional[np.ndarray] = None
        self._circles: Optional[np.ndarray] = None
        self._table_geometry = table_geometry  # 動態計算半徑範圍

        if hough_param1 is not None:
            self.HOUGH_PARAM1 = hough_param1
        if hough_param2 is not None:
            self.HOUGH_PARAM2 = hough_param2

    # ── 框架設定 ─────────────────────────────────────────────────────────────

    def set_frame(self, frame: np.ndarray):
        """餵入 BGR 畫面"""
        self._frame = frame
        self._gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self._hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        self._circles = None

    # ── 圓形偵測 ─────────────────────────────────────────────────────────────

    def detect_circles(self) -> List[Tuple[float, float, float]]:
        """
        HoughCircles 圓形偵測

        回傳：[(u, v, radius), ...] 圓心+半徑列表

        半徑範圍：由 TableGeometry 根據校正動態計算（pixel↔mm 比例）
        未校正時 fallback 為 (5, 100)
        """
        if self._gray is None:
            return []

        # 動態半徑範圍（由校正矩陣計算）
        if self._table_geometry:
            min_r, max_r = self._table_geometry.hough_radius_range()
        else:
            min_r, max_r = 5, 100  # fallback：未校正時

        # 去噪 + 模糊
        blurred = cv2.medianBlur(self._gray, 5)

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,                  # 解析度比例
            minDist=self.DIST_BETWEEN_CIRCLES,
            param1=self.HOUGH_PARAM1,
            param2=self.HOUGH_PARAM2,
            minRadius=min_r,        # 動態：由 TableGeometry 計算
            maxRadius=max_r,        # 動態：由 TableGeometry 計算
        )

        if circles is None:
            return []

        result = []
        for circle in circles[0]:
            u, v, r = circle
            result.append((float(u), float(v), float(r)))

        # 按半徑排序（較大的通常比較可靠）
        result.sort(key=lambda c: c[2], reverse=True)
        self._circles = result
        return result

    # ── 顏色分類 ─────────────────────────────────────────────────────────────

    def _get_hsv_at(self, u: int, v: int, mask: np.ndarray = None) -> Tuple[int, int, int]:
        """取得指定位置的 HSV 值"""
        if self._hsv is None:
            return (0, 0, 0)
        h, s, v_val = self._hsv[int(v), int(u)]
        if mask is not None and mask[int(v), int(u)] == 0:
            return (0, 0, 0)  # 被 mask 遮住
        return (int(h), int(s), int(v_val))

    def _is_stripe(self, u: int, v: int, r: int) -> bool:
        """
        判斷球是否為條紋球
        
        條紋球：邊緣亮、中心暗（白色條紋帶）
        全色球：整體均勻
        
        方法：比較中心區域 vs邊緣區域的亮度/飽和度
        """
        if self._hsv is None or r < 5:
            return False

        h, w = self._hsv.shape[:2]
        
        # 確保範圍在圖片內
        x1 = max(0, int(u) - int(r))
        x2 = min(w, int(u) + int(r))
        y1 = max(0, int(v) - int(r))
        y2 = min(h, int(v) + int(r))

        if x2 <= x1 or y2 <= y1:
            return False

        # 中心區域（半徑的 40%）
        center_mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
        cr = int(r * 0.4)
        center_u, center_v = int(u - x1), int(v - y1)
        cv2.circle(center_mask, (center_u, center_v), cr, 255, -1)

        # 邊緣區域（半徑的 70% ~ 100%）
        ring_mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
        cv2.circle(ring_mask, (center_u, center_v), int(r * 0.7), 255, -1)
        cv2.circle(ring_mask, (center_u, center_v), cr, 0, -1)

        hsv_region = self._hsv[y1:y2, x1:x2]

        # 中心 vs 邊緣 平均亮度
        center_vals = hsv_region[center_mask == 255]
        ring_vals = hsv_region[ring_mask == 255]

        if len(center_vals) == 0 or len(ring_vals) == 0:
            return False

        center_brightness = np.mean(center_vals[:, 2])  # V channel
        ring_brightness = np.mean(ring_vals[:, 2])      # V channel

        # 邊緣比中心亮超過閾值 → 條紋球
        brightness_diff = ring_brightness - center_brightness
        return brightness_diff > self.STRIPE_BRIGHTNESS_DIFF

    def classify_color(self, u: int, v: int, r: int) -> Tuple[str, int, bool]:
        """
        對指定位置做顏色分類

        回傳：(color_name, ball_number, is_stripe)

        邏輯：
        1. 先用亮度區分：黑色球（V < 50）
        2. 再用 Hue 對照顏色表
        3. 條紋判斷：_is_stripe()
        """
        if self._hsv is None:
            return ("unknown", 0, False)

        # 取球心周圍一小區域的平均 Hue（避免單點噪聲）
        h, s, v_val = self._get_hsv_at(u, v)

        # 步驟1：亮度極低 → 黑色球（8號）
        if v_val < 50:
            return ("black", 8, False)

        # 步驟2：Hue 映射
        color = self._classify_hue(h)

        # 步驟3：條紋判斷（只對非黑球判斷）
        is_stripe = False
        if color != "black":
            is_stripe = self._is_stripe(u, v, r)

        # 條紋球 → 球號 9
        if is_stripe and color == "yellow":
            return (f"{color}_stripe", 9, True)

        # 根據顏色查球號
        color_key = color if not is_stripe else f"{color}_stripe"
        number = COLOR_TO_NUMBER.get(color_key, 0)

        return (color, number, is_stripe)

    def _ball_confidence(self, circle: np.ndarray) -> float:
        """
        根據 HoughCircles accumulator 計算置信度

        param2 越大 → 圓形越明確 → 置信度越高
        circle = (u, v, r) — param2 在 circles[2] 不在這裡，
        但我們可以用半徑穩定性估算（邊緣清晰度）
        """
        u, v, r = circle
        if self._gray is None:
            return 0.5

        # 取圓周邊緣的梯度強度（邊緣越清晰 → 置信度越高）
        try:
            edges = cv2.Canny(self._gray, 50, 150)
            # 在圓周上採樣邊緣強度
            angles = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            x_pts = np.clip(np.round(u + r * np.cos(angles)).astype(int), 0, edges.shape[1] - 1)
            y_pts = np.clip(np.round(v + r * np.sin(angles)).astype(int), 0, edges.shape[0] - 1)
            edge_vals = edges[y_pts, x_pts]
            edge_strength = np.mean(edge_vals) / 255.0  # 0-1
            confidence = 0.4 + 0.5 * edge_strength  # 0.4-0.9
            return round(min(confidence, 0.95), 2)
        except Exception:
            return 0.7  # fallback

    def _classify_hue(self, h: int) -> str:
        """
        根據 Hue 值分類顏色（OpenCV HSV Hue: 0-180）

        HSV Hue 範圍（0-180）：
        - 紅色跨 0/180 邊界（0-10 或 170-180）
        - 橙色：10-25（不在紅色區間）
        - 黃色：25-35
        - 綠色：45-75
        - 藍色：100-130
        - 紫色：130-160
        - 栗色（暗紅）：0-10（已由紅色處理）
        """
        # 紅色（跨邊界）：0-10 或 170-180
        if h <= 10 or h >= 170:
            return "red"

        # 橙色：10-25（排除已處理的 0-10）
        if 11 <= h <= 25:
            return "orange"

        # 黃色：25-35
        if 25 <= h <= 35:
            return "yellow"

        # 綠色：45-75
        if 45 <= h <= 75:
            return "green"

        # 藍色：100-130
        if 100 <= h <= 130:
            return "blue"

        # 紫色：130-160
        if 130 <= h <= 160:
            return "purple"

        return "unknown"

    # ── 完整偵測流程 ─────────────────────────────────────────────────────────

    def detect_all(self) -> List[DetectedBall]:
        """
        一次執行完整 pipeline：
        圓形偵測 → 顏色分類 → 回傳所有球

        回傳：[DetectedBall, ...]
        """
        if self._frame is None:
            return []

        circles = self.detect_circles()
        balls = []

        for circle in circles:
            u, v, r = circle
            ui, vi, ri = int(u), int(v), int(r)

            # 跳过边缘区域（可能有噪点）
            if ui < ri or vi < ri:
                continue
            if ui + ri >= self._frame.shape[1] or vi + ri >= self._frame.shape[0]:
                continue

            color, number, is_stripe = self.classify_color(ui, vi, ri)
            confidence = self._ball_confidence(np.array([u, v, r]))

            balls.append(DetectedBall(
                u=u, v=v, radius=r,
                color=color, number=number,
                is_stripe=is_stripe,
                confidence=confidence,
            ))

        return balls

    def sort_by_number(self, balls: List[DetectedBall]) -> List[DetectedBall]:
        """
        對球列表排序（9號球規則：號碼小的先打）
        
        規則：
        - 正常：按球號 1-9 排序
        - 8號球：最後打（特殊處理，這裡先跳過）
        - 先進球（pocket）比其他目標優先
        """
        if not balls:
            return []
        
        # 分離白球（可能用亮度極高來識別）
        non_cue = [b for b in balls if b.number != 0]
        non_cue.sort(key=lambda b: b.number)
        return non_cue

    # ── 視覺化工具 ──────────────────────────────────────────────────────────

    def draw_balls(self, frame: np.ndarray, balls: List[DetectedBall]) -> np.ndarray:
        """
        在畫面上標記偵測到的球（除錯用）
        
        顯示：編號、顏色標籤、圓形輪廓
        """
        for ball in balls:
            u, v, r = int(ball.u), int(ball.v), int(ball.radius)
            
            # 圓形輪廓
            cv2.circle(frame, (u, v), r, (0, 255, 0), 2)
            
            # 球號標籤
            label = f"#{ball.number}"
            if ball.is_stripe:
                label += "s"
            
            cv2.putText(frame, label, (u - 10, v - r - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 顏色標記
            color_bgr = self._color_name_to_bgr(ball.color)
            cv2.circle(frame, (u, v), 3, color_bgr, -1)

        return frame

    def _color_name_to_bgr(self, color: str) -> Tuple[int, int, int]:
        """顏色名稱 → BGR tuple"""
        table = {
            "yellow":       (0, 255, 255),
            "blue":         (255, 0, 0),
            "red":          (0, 0, 255),
            "purple":       (128, 0, 128),
            "orange":       (0, 165, 255),
            "green":        (0, 255, 0),
            "maroon":       (0, 0, 100),
            "black":        (0, 0, 0),
            "yellow_stripe":(0, 255, 255),
        }
        return table.get(color, (128, 128, 128))
