"""
windows/control/vision_pipeline.py
視覺 pipeline — Phase 1 整合層

職責：
- 整合 BallIdentifier + CalibrationControl + TableGeometry
- 協調相機輸入 → 圓形偵測 → 顏色分類 → 策略排序
- 為 COMPETE 模式提供乾淨的 API

設計原則：
- Camera 解析度無關（720p / 640x480 皆可）
- 球徑 pixel 值由 TableGeometry 根據校正動態計算
- 形狀（圓形）先於顏色偵測
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, List

from .ball_identifier import BallIdentifier, DetectedBall
from .calibration_control import CalibrationControl
from .table_geometry import TableGeometry


@dataclass
class CompeteBall:
    """COMPETE 模式使用的球物件（包含 mm 座標）"""
    number: int
    color: str
    is_stripe: bool
    u_pixel: float   # pixel 座標
    v_pixel: float
    x_mm: float       # mm 座標（由校正矩陣轉換）
    y_mm: float
    pocket_candidate: Optional[str] = None  # 建議口袋


@dataclass
class CompeteScene:
    """完整的球檯配置（COMPETE 模式用）"""
    balls: List[CompeteBall]
    cue_ball: Optional[CompeteBall] = None
    sorted_targets: List[CompeteBall] = None  # 按擊球順序排列
    frame: Optional[np.ndarray] = None  # 原始畫面（用於繪圖）


class VisionPipeline:
    """
    視覺辨識 pipeline
    
    Phase 1 提供：形狀（圓形）→ 顏色 → 排序
    Phase 2 可擴充：障礙判斷、力度估算
    Phase 3 可擴充：側邊相機整合、物理參數
    """

    def __init__(self):
        self._calibration = CalibrationControl()
        self._geometry = TableGeometry()
        self._geometry.set_calibration(self._calibration)
        self._identifier = BallIdentifier(table_geometry=self._geometry)
        self._scene: Optional[CompeteScene] = None
        self._frame: Optional[np.ndarray] = None

    # ── 注入依賴 ─────────────────────────────────────────────────────────────

    def set_calibration(self, calib: CalibrationControl):
        """注入校正控制（提供 pixel↔mm 轉換，並同步到 TableGeometry）"""
        self._calibration = calib
        self._geometry.set_calibration(calib)

    # ── 主要流程 ─────────────────────────────────────────────────────────────

    def set_frame(self, frame: np.ndarray):
        """餵入相機畫面（BGR）"""
        self._frame = frame
        self._identifier.set_frame(frame)

    def run(self) -> CompeteScene:
        """
        執行完整視覺 pipeline
        
        流程：
        1. 圓形偵測（HoughCircles）
        2. 顏色分類（HSV Hue）
        3. 白球識別（高亮度）
        4. 剩餘球排序（號碼順序）
        5. pixel→mm 座標轉換（已校正時）
        """
        if self._frame is None:
            return CompeteScene(balls=[], cue_ball=None, sorted_targets=[])

        detected = self._identifier.detect_all()
        balls = self._translate_balls(detected)
        
        # 分離白球
        cue = self._find_cue_ball(balls)
        targets = [b for b in balls if b.number > 0 and b is not cue]
        
        # 9號球排序（號碼小的先打）
        targets.sort(key=lambda b: b.number)
        
        self._scene = CompeteScene(
            balls=balls,
            cue_ball=cue,
            sorted_targets=targets,
            frame=self._frame.copy(),
        )
        
        return self._scene

    def _translate_balls(self, detected: List[DetectedBall]) -> List[CompeteBall]:
        """將偵測結果轉換為 CompeteBall（包含 mm 座標）"""
        balls = []
        
        for d in detected:
            if self._calibration and self._calibration.is_valid():
                x_mm, y_mm = self._calibration.pixel_to_mm(d.u, d.v)
            else:
                x_mm, y_mm = 0.0, 0.0  # 未校正時用 pixel

            balls.append(CompeteBall(
                number=d.number,
                color=d.color,
                is_stripe=d.is_stripe,
                u_pixel=d.u,
                v_pixel=d.v,
                x_mm=x_mm,
                y_mm=y_mm,
            ))

        return balls

    def _find_cue_ball(self, balls: List[CompeteBall]) -> Optional[CompeteBall]:
        """
        識別白球
        
        方法：
        - 白球極亮（V > 150）
        - 無特定顏色（Hue 不在顏色帶內）
        - 或者：如果只有一個極亮的球 → 白球
        """
        if not balls:
            return None

        # 取最亮的球
        bright_candidates = []
        for b in balls:
            # 用 pixel 值估算亮度（白色 V 值高）
            if self._frame is not None:
                try:
                    hsv = cv2.cvtColor(
                        self._frame[int(b.v_pixel):int(b.v_pixel)+1,
                                    int(b.u_pixel):int(b.u_pixel)+1],
                        cv2.COLOR_BGR2HSV
                    )[0, 0]
                    v = hsv[2]
                    if v > 150:  # 高亮度 → 白球候選
                        bright_candidates.append((b, v))
                except:
                    pass

        if bright_candidates:
            bright_candidates.sort(key=lambda x: x[1], reverse=True)
            return bright_candidates[0][0]

        # fallback：最亮的當白球
        return None

    # ── 查詢 API ─────────────────────────────────────────────────────────────

    def get_scene(self) -> Optional[CompeteScene]:
        return self._scene

    def get_next_target(self) -> Optional[CompeteBall]:
        """取得下一個應該打的球（號碼最小）"""
        if self._scene is None:
            return None
        if not self._scene.sorted_targets:
            return None
        return self._scene.sorted_targets[0]

    # ── 視覺化 ─────────────────────────────────────────────────────────────

    def draw_debug(self, frame: np.ndarray) -> np.ndarray:
        """
        在畫面上繪製偵測結果（除錯用）
        
        顯示：
        - 圓形輪廓 + 編號
        - 顏色標籤
        - 瞄準順序（1→2→3...）
        """
        if self._scene is None:
            return frame

        # 先用 BallIdentifier 的繪圖
        detected = self._identifier.detect_all()
        frame = self._identifier.draw_balls(frame, detected)

        # 再加上瞄準順序
        if self._scene.sorted_targets:
            h, w = frame.shape[:2]
            for i, ball in enumerate(self._scene.sorted_targets[:6]):  # 最多6個
                u, v = int(ball.u_pixel), int(ball.v_pixel)
                
                # 順序標記
                cv2.circle(frame, (u, v), 20, (0, 200, 255), 2)
                cv2.putText(frame, str(i + 1), (u - 6, v + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

                # mm 座標（右上角）
                mm_text = f"({ball.x_mm:.0f}, {ball.y_mm:.0f})mm" if ball.x_mm else "?"
                cv2.putText(frame, mm_text, (u - 20, v + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 0), 1)

        # 白球標記
        if self._scene.cue_ball:
            cu = int(self._scene.cue_ball.u_pixel)
            cv = int(self._scene.cue_ball.v_pixel)
            cv2.circle(frame, (cu, cv), 18, (255, 255, 255), 2)
            cv2.putText(frame, "CUE", (cu - 15, cv - 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    # ── 參數空間（Phase 3 預留）─────────────────────────────────────────────

    class StrategyParams:
        """
        策略參數（預留空間，Phase 3 啟用）
        
        目前使用預設值，後期可透過 web UI 或檔案調整
        """
        FRICTION_COEFFICIENT = 0.2    # 桌面摩擦係數
        CUSHION_REBOUND = 0.75          # 庫邊反彈係數
        SIDE_CAMERA_OFFSET = 0          # 側邊相機擊球點 offset（mm）
        
        # 擊球選擇權重
        WEIGHT_DISTANCE = 0.3
        WEIGHT_ANGLE = 0.4
        WEIGHT_OBSTRUCTION = 0.3

        @classmethod
        def update(cls, **kwargs):
            """動態更新參數"""
            for key, val in kwargs.items():
                if hasattr(cls, key):
                    setattr(cls, key, val)
