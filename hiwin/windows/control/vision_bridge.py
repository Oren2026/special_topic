"""
windows/control/vision_bridge.py
視覺 bridge — 串接 VisionPipeline + StateMachine + robot_brain

職責：
1. 封裝相機擷取（mock / 實相機）
2. 執行 VisionPipeline → 取得球配置
3. 呼叫 robot_brain.compute_shot(obstacles=[...])
4. 將結果送入 ShotDispatcher

設計：
- mock 模式：使用 sim_table 模擬球配置（無需相機）
- 實機模式：從相機取 frame，傳入 VisionPipeline
- 為 StateMachine.COMPETE 提供乾淨的 API
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple
import sys, os

# ── 匯入策略：standalone（直接 python xxx.py）vs package（import 或 -m 執行）────
# 判斷：__name__ 包含 '.' 表示已在前綴模組下 = package 模式
#       否則為 standalone 模式（__name__ == "__main__" 但被直接執行）
def _is_package_mode():
    # 透過檢查模組路徑判斷是否為 package 成員
    # 若頂層 import 能成功則為 package，失敗則為 standalone
    try:
        # 嘗試相對匯入（package 模式）
        from . import vision_pipeline as _vp
        return True
    except ImportError:
        return False

if _is_package_mode():
    from .vision_pipeline import VisionPipeline, CompeteBall
    from .calibration_control import CalibrationControl
    from .table_geometry import TableGeometry
    from .ball_identifier import BallIdentifier
else:
    # standalone 模式：手動設定路徑後用絕對匯入
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _ROOT)
    from control.vision_pipeline import VisionPipeline, CompeteBall
    from control.calibration_control import CalibrationControl
    from control.table_geometry import TableGeometry
    from control.ball_identifier import BallIdentifier


# ─── Mock 球配置產生器 ────────────────────────────────────────────────────────

def make_mock_scene() -> List[dict]:
    """
    產生一個模擬的球配置（用於無相機時測試 COMPETE 流程）
    球徑 38mm，球心座標 (x_mm, y_mm)
    """
    return [
        # 白球
        {"x": 300, "y": 315, "color": "white", "number": 0},
        # 目標球（9號球前的任意球）
        {"x": 700, "y": 200, "color": "yellow", "number": 1},
        {"x": 800, "y": 400, "color": "blue", "number": 2},
        {"x": 500, "y": 500, "color": "red", "number": 3},
        # 障礙球
        {"x": 450, "y": 300, "color": "green", "number": 4},
        {"x": 600, "y": 350, "color": "purple", "number": 5},
    ]


# ─── VisionBridge ────────────────────────────────────────────────────────────

class VisionBridge:
    """
    視覺 bridge — 串接相機 / 虛擬場景 → VisionPipeline → robot_brain

    使用方式：
    1. set_calibration(calib) — 注入校正（pixel↔mm）
    2. start_camera() / start_mock() — 選擇資料來源
    3. capture_and_process() — 執行視覺流程 → 回傳 ShotPayload
    4. get_balls() — 查詢目前偵測到的球配置
    """

    def __init__(self, robot_brain=None):
        # 視覺元件
        self._calib: Optional[CalibrationControl] = None
        self._geometry = TableGeometry()
        self._identifier = BallIdentifier(table_geometry=self._geometry)
        self._pipeline = VisionPipeline()
        self._pipeline.set_calibration(self._calib)

        # 策略大腦
        self._robot_brain = robot_brain

        # 相機
        self._camera = None          # cv2.VideoCapture
        self._mock_mode = False
        self._mock_scene = make_mock_scene()
        self._mock_idx = 0           # 用於輪詢 mock frame

        # 目前偵測結果
        self._current_balls: List[CompeteBall] = []
        self._cue_ball: Optional[CompeteBall] = None
        self._targets: List[CompeteBall] = []

    # ── 相機控制 ──────────────────────────────────────────────────────────

    def start_camera(self, camera_index: int = 0) -> bool:
        """
        啟動真實相機
        回傳：成功與否
        """
        try:
            self._camera = cv2.VideoCapture(camera_index)
            if not self._camera.isOpened():
                self._camera.release()
                self._camera = None
                return False
            self._mock_mode = False
            return True
        except Exception:
            self._camera = None
            return False

    def start_mock(self, scene: List[dict] = None):
        """
        啟動 mock 模式（使用模擬球配置，無需相機）
        scene：自訂球配置，預設使用 make_mock_scene()
        """
        self._mock_mode = True
        if scene is not None:
            self._mock_scene = scene
        if self._camera is not None:
            self._camera.release()
            self._camera = None

    def stop(self):
        """停止相機，釋放資源"""
        if self._camera is not None:
            self._camera.release()
            self._camera = None

    # ── 注入依賴 ──────────────────────────────────────────────────────────

    def set_calibration(self, calib: CalibrationControl):
        """注入校正控制"""
        self._calib = calib
        self._geometry.set_calibration(calib)
        self._pipeline.set_calibration(calib)

    def set_robot_brain(self, brain):
        """注入策略大腦（用於 compute_shot）"""
        self._robot_brain = brain

    # ── Frame 產生（mock）─────────────────────────────────────────────────

    def _make_mock_frame(self) -> np.ndarray:
        """
        根據 mock_scene 產生一張模擬球檯影像（720p, 全黑背景）
        每個球畫一個彩色填充圓
        """
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        color_map = {
            "white":  (220, 220, 220),
            "yellow": (0, 255, 255),
            "blue":   (255, 0, 0),
            "red":    (0, 0, 255),
            "green":  (0, 255, 0),
            "purple": (128, 0, 128),
            "orange": (0, 165, 255),
            "maroon": (0, 0, 100),
            "black":  (0, 0, 0),
        }

        # 簡單的透視：把 mm 座標映射到 720p frame
        # 假設：球檯佔 frame 80%，置中
        scale = min(1280 / 1300, 720 / 700) * 0.8
        ox = (1280 - 1200 * scale) / 2
        oy = (720 - 630 * scale) / 2

        # 球半徑 pixel：19mm × scale → 但 scale=0.788 時只有 ~15px
        # HoughCircles 需要够大的圓才能穩定偵測（minRadius=13 邊緣）
        # 用 20px 固定半徑（≈真實 38mm 球在 720p 的投影大小）
        ball_radius_px = 20

        for ball in self._mock_scene:
            px = int(ball["x"] * scale + ox)
            py = int(ball["y"] * scale + oy)
            r = ball_radius_px
            color = color_map.get(ball["color"], (128, 128, 128))
            cv2.circle(frame, (px, py), r, color, -1)
            cv2.circle(frame, (px, py), r, (255, 255, 255), 2)

        return frame

    # ── 主要流程 ──────────────────────────────────────────────────────────

    def capture_and_process(self) -> Optional[dict]:
        """
        擷取一幀 → 執行 VisionPipeline → 呼叫 robot_brain.compute_shot()
        回傳：shot payload dict 或 None
        """
        # 1. 取得 frame
        if self._mock_mode:
            frame = self._make_mock_frame()
        elif self._camera is not None:
            ret, frame = self._camera.read()
            if not ret:
                return None
        else:
            return None

        # 2. VisionPipeline 處理
        self._pipeline.set_frame(frame)
        scene = self._pipeline.run()

        self._current_balls = scene.balls
        self._cue_ball = scene.cue_ball
        self._targets = scene.sorted_targets

        # 3. 如果沒有策略大腦，回傳偵測結果即可
        if self._robot_brain is None:
            return {
                "balls": self._current_balls,
                "cue_ball": self._cue_ball,
                "targets": self._targets,
            }

        # 4. 呼叫 robot_brain.compute_shot()
        if not self._cue_ball or not self._targets:
            return None

        target = self._targets[0]  # 下一個目標球（號碼最小）
        obstacles = self._pipeline.get_obstacles(exclude_numbers=[0, target.number])

        try:
            shot_payload = self._robot_brain.compute_shot(
                cue_ball={"x": self._cue_ball.x_mm, "y": self._cue_ball.y_mm},
                target_ball={"x": target.x_mm, "y": target.y_mm},
                pocket_name="top_left",  # TODO：動態選擇最佳口袋
                obstacles=obstacles,
            )
            return shot_payload
        except Exception as e:
            print(f"[VisionBridge] compute_shot error: {e}")
            return None

    # ── 查詢 API ──────────────────────────────────────────────────────────

    def get_balls(self) -> List[CompeteBall]:
        return self._current_balls

    def get_cue_ball(self) -> Optional[CompeteBall]:
        return self._cue_ball

    def get_targets(self) -> List[CompeteBall]:
        return self._targets

    def get_obstacles(self, exclude: List[int] = None) -> List[dict]:
        return self._pipeline.get_obstacles(exclude_numbers=exclude)

    def is_mock(self) -> bool:
        return self._mock_mode


# ── Standalone 測試 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== VisionBridge Standalone Test ===")

    bridge = VisionBridge(robot_brain=None)  # 不接 robot_brain，只測視覺 pipeline
    bridge.start_mock()  # 使用預設 mock scene

    print(f"Mode: {'MOCK' if bridge.is_mock() else 'CAMERA'}")
    print(f"Mock scene: {bridge._mock_scene}")

    # 執行一次 capture_and_process（不回傳 shot，只測視覺偵測）
    result = bridge.capture_and_process()

    if result:
        balls = result.get("balls", [])
        targets = result.get("targets", [])
        cue = result.get("cue_ball")
        print(f"\nDetected {len(balls)} balls:")
        for b in balls:
            print(f"  #{b.number} {b.color} ({b.x_mm:.0f}mm, {b.y_mm:.0f}mm) conf={b.confidence:.2f}")
        if cue:
            print(f"Cue ball: ({cue.x_mm:.0f}mm, {cue.y_mm:.0f}mm)")
        if targets:
            print(f"Top target: #{targets[0].number} {targets[0].color}")
    else:
        print("capture_and_process returned None")

    # 顯示 mock frame
    frame = bridge._make_mock_frame()
    cv2.putText(frame, "VisionBridge Mock Frame (press any key to exit)",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imshow("vision_bridge.py - Mock Frame", frame)
    key = cv2.waitKey(0)
    print(f"Key pressed: {key}")
    cv2.destroyAllWindows()
    print("Done.")
