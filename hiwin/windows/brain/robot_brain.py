"""
windows/brain/robot_brain.py
決策層核心（Windows-Only 版）

職責：
  - 接收 UI 事件（像素座標）
  - 座標轉換（pixel → mm）
  - 策略計算（Ghost Ball + Bank Shot）
  - 執行流程：手臂移動 → Z軸對準 → Arduino擊球 → 手臂抬起

執行流程（用户确认）：
  1. 手臂接收 x, y, z（z_approach = z + 30mm）
  2. 手臂移到 (x, y, z_approach）
  3. 手臂緩慢下移至 (x, y, z_target = Z_CUE_ALIGN)
  4. Arduino 發送 `goto {stroke_dist}` 驅動步進馬達
  5. 手臂抬起至安全高度 (z_safe)

依賴：
  brain.coord_manager   — 像素↔mm
  brain.strategy_module — Ghost Ball + Bank Shot
  brain.hiwin_arm       — HIWIN RA605 TCP/IP
  brain.striker_bridge  — Arduino Serial

使用：windows/control/state_v2.py（或其他 UI 層）
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coord_manager   import CoordinateManager
from strategy_module import BilliardStrategy
from hiwin_arm       import HiwinArmBridge
from striker_bridge  import StrikerBridge
from break_module    import BreakStrategy
from config          import (
    ARDUINO_PORT, ARDUINO_BAUD, ARDUINO_TIMEOUT, STRIKER_MOCK_MODE,
    Z_SAFE_HEIGHT, Z_CUE_ALIGN,
)


class RobotBrain:
    """
    決策層核心（Windows-Only）

    整合所有子模組，提供統一的打擊 API 給 state_v2.py 调用。
    """

    def __init__(self):
        # 策略層
        self._coord    = CoordinateManager()
        self._strategy = BilliardStrategy()
        self._break_s  = BreakStrategy()

        # 硬體 Bridge
        self._arm    = HiwinArmBridge(mock=True)   # TODO: mock=False 时填 real IP
        self._strike = StrikerBridge(
            port=ARDUINO_PORT,
            baud=ARDUINO_BAUD,
            timeout=ARDUINO_TIMEOUT,
            mock=STRIKER_MOCK_MODE,
        )

    # ── 起動 / 斷線 ────────────────────────────────────────────────────────

    def start(self):
        """連線至手臂 + 擊球機構"""
        self._arm.connect()
        self._strike.connect()

    def stop(self):
        """斷線"""
        self._arm.disconnect()
        self._strike.disconnect()

    # ── 校正 ───────────────────────────────────────────────────────────────

    def calibrate(self, points: list[list[int]]) -> dict:
        """
        4角校正
        points: [[u1,v1], [u2,v2], [u3,v3], [u4,v4]]（像素）
        回傳：{"pockets": {name: [u, v], ...}}
        """
        self._coord.update_calibration(points)
        pockets_mm = self._strategy.get_all_pockets_mm()
        pockets_pixel = self._coord.get_pockets_pixel(pockets_mm)
        return {"pockets": pockets_pixel}

    # ── 打擊計算 + 執行（統一入口）────────────────────────────────────────

    def compute_and_execute_shot(
        self,
        cue_pixel:      tuple[int, int],
        target_pixel:   tuple[int, int],
        pocket_pixel:   tuple[int, int],
        obstacles_pixel: list[tuple[int, int]] = None,
    ) -> dict:
        """
        MANUAL 指定打擊：預測 + 執行（全自動）

        流程：
          1. pixel → mm 座標轉換
          2. 策略計算（Ghost Ball / Bank Shot）
          3. 手臂執行（move → Z對準 → Arduino擊球 → 抬起）

        參數（皆為 pixel）：
            cue_pixel, target_pixel, pocket_pixel
            obstacles_pixel: 障礙球列表（可選）

        回傳：
            dict {
                "success":     bool,
                "ghost_pixel": [u, v],
                "robot_pixel": [u, v],
                "angle":       float,
                "stroke_dist": float,
                "is_reachable":bool,
                "shot_type":   "direct"|"bank",
                "striker_ok":  bool,
                "arm_ok":      bool,
            }
        """
        obstacles = obstacles_pixel or []
        result = self._compute_shot(
            cue_pixel, target_pixel, pocket_pixel, obstacles
        )
        if result is None:
            return {"success": False, "error": "compute failed"}

        # 執行手臂 + 擊球
        arm_ok = self._execute_shot(
            robot_tcp=result["robot_tcp_mm"],
            stroke_dist=result["stroke_dist"],
            angle=result["angle"],
        )

        return {
            "success":      arm_ok,
            "ghost_pixel":  result["ghost_pixel"],
            "robot_pixel":  result["robot_pixel"],
            "angle":        result["angle"],
            "stroke_dist":  result["stroke_dist"],
            "is_reachable":result["is_reachable"],
            "shot_type":    result["shot_type"],
            "striker_ok":   arm_ok,
            "arm_ok":       arm_ok,
        }

    def compute_shot_only(
        self,
        cue_pixel:      tuple[int, int],
        target_pixel:   tuple[int, int],
        pocket_pixel:   tuple[int, int],
        obstacles_pixel: list[tuple[int, int]] = None,
    ) -> dict:
        """
        STRATEGY 模式：只計算，不執行（返回所有口袋候選）
        回傳：list[dict]，每個口袋一個候選
        """
        obstacles = obstacles_pixel or []
        pockets_mm = self._strategy.get_all_pockets_mm()
        candidates = []

        cx, cy = self._pixel_to_mm(*cue_pixel)
        tx, ty = self._pixel_to_mm(*target_pixel)
        obs_mm = [{"x": x, "y": y} for x, y in
                  [self._pixel_to_mm(u, v) for u, v in obstacles]]

        for pocket_name, (px, py) in pockets_mm.items():
            shot = self._strategy.compute_shot(
                cue_ball={"x": cx, "y": cy},
                target_ball={"x": tx, "y": ty},
                pocket_name=pocket_name,
                obstacles=obs_mm,
            )
            if shot is None:
                continue

            rx, ry = shot["robot_tcp"]
            gu, gv = self._coord.mm_to_pixel(*shot["ghost"])
            ru, rv = self._coord.mm_to_pixel(rx, ry)

            candidates.append({
                "pocket":       pocket_name,
                "ghost_pixel":  [gu, gv],
                "robot_pixel":  [ru, rv],
                "angle":        shot["angle"],
                "stroke_dist":  shot["stroke_dist"],
                "is_reachable": shot["is_reachable"],
                "shot_type":    shot.get("type", "direct"),
                "robot_tcp_mm": (rx, ry),
                "ghost_mm":     shot["ghost"],
            })

        return candidates

    def execute_shot_by_candidate(self, candidate: dict) -> dict:
        """
        STRATEGY 模式：使用者點選口袋後，執行候選
        candidate: compute_shot_only() 回傳的其中一項
        """
        arm_ok = self._execute_shot(
            robot_tcp=candidate["robot_tcp_mm"],
            stroke_dist=candidate["stroke_dist"],
            angle=candidate["angle"],
        )
        return {
            "success":    arm_ok,
            "striker_ok": arm_ok,
            "arm_ok":     arm_ok,
        }

    def compute_and_execute_break(self, cue_pixel: tuple[int, int]) -> dict:
        """
        開球：計算 + 執行（全自動）
        """
        cx, cy = self._pixel_to_mm(*cue_pixel)

        result = self._break_s.compute_break(cue_ball_mm={"x": cx, "y": cy})
        if result is None:
            return {"success": False, "error": "break compute failed"}

        arm_ok = self._execute_shot(
            robot_tcp=result["robot_tcp"],
            stroke_dist=result["stroke_dist"],
            angle=result["angle"],
        )

        ru, rv = self._coord.mm_to_pixel(*result["robot_tcp"])
        return {
            "success":      arm_ok,
            "robot_pixel":  [ru, rv],
            "angle":        result["angle"],
            "stroke_dist":  result["stroke_dist"],
            "is_reachable": result["is_reachable"],
            "striker_ok":   arm_ok,
            "arm_ok":       arm_ok,
        }

    # ── 內部：計算 ────────────────────────────────────────────────────────

    def _compute_shot(
        self,
        cue_pixel:      tuple[int, int],
        target_pixel:   tuple[int, int],
        pocket_pixel:   tuple[int, int],
        obstacles_pixel: list[tuple[int, int]],
    ) -> "dict | None":
        """策略計算 + 座標轉換（不回傳硬體執行結果）"""

        cx, cy = self._pixel_to_mm(*cue_pixel)
        tx, ty = self._pixel_to_mm(*target_pixel)
        px, py = self._pixel_to_mm(*pocket_pixel)

        pocket_name = self._find_pocket_name(px, py)

        obs_dict = [{"x": x, "y": y} for x, y in
                    [self._pixel_to_mm(u, v) for u, v in obstacles_pixel]]

        shot = self._strategy.compute_shot(
            cue_ball={"x": cx, "y": cy},
            target_ball={"x": tx, "y": ty},
            pocket_name=pocket_name,
            obstacles=obs_dict,
        )
        if shot is None:
            return None

        rx, ry = shot["robot_tcp"]
        gu, gv = self._coord.mm_to_pixel(*shot["ghost"])
        ru, rv = self._coord.mm_to_pixel(rx, ry)

        return {
            "ghost_pixel":  [gu, gv],
            "robot_pixel":  [ru, rv],
            "robot_tcp_mm": (rx, ry),
            "angle":        shot["angle"],
            "stroke_dist":  shot["stroke_dist"],
            "is_reachable": shot["is_reachable"],
            "shot_type":    shot.get("type", "direct"),
        }

    # ── 內部：執行 ────────────────────────────────────────────────────────

    def _execute_shot(
        self,
        robot_tcp: tuple,
        stroke_dist: float,
        angle: float = 0.0,
    ) -> bool:
        """
        執行一次完整擊球流程：

        1. HOME（歸零）
        2. 手臂移到 (x, y+50, z=100, c=angle)  ← y+50 扣掉桿頭偏移
        3. Z軸對準：move_z_for_cue_alignment(x, y+50, z_target=Z_CUE_ALIGN, c=angle)
        4. Arduino 發送 `goto {stroke_dist}`
        5. 手臂抬起至 z=100
        6. HOME（歸零）

        參數：
            robot_tcp:  (rx, ry) 手臂 TCP 停泊位置（mm），ry 為球心 Y 座標
            stroke_dist: 擊球行程（mm），發給 Arduino
            angle:      打擊方向（度），對應 C 軸
        """
        rx, ry = robot_tcp
        # y 扣掉桿頭長度：法蘭停在 ball_y - 50，桿頭尖端在 ball_y
        flange_y = ry - 50
        # C軸轉換：strategy_angle=0°(+X) → HIWIN C=90°；strategy_angle=90°(+Y) → HIWIN C=0°
        c = (90 - angle) % 360

        # Step 0: 歸零
        print(f"[RobotBrain] HOME")
        self._arm.home(wait=True)

        # Step 1: approach（上方安全高度）
        z_approach = Z_CUE_ALIGN + 90.0
        if not self._arm.move_to(x=rx, y=flange_y, z=z_approach, c=c, wait=True):
            print("[RobotBrain] Step1 approach failed")
            return False

        # Step 2: Z軸對準白球（低速下降）
        if not self._arm.move_z_for_cue_alignment(
            x=rx, y=flange_y, z_target=Z_CUE_ALIGN, c=c
        ):
            print("[RobotBrain] Step2 Z對準 failed")
            return False

        # Step 3: Arduino 擊球
        striker_ok = self._strike.execute(
            robot_tcp=(rx, flange_y),
            stroke_dist=stroke_dist,
            angle=angle,
        )
        if not striker_ok:
            print("[RobotBrain] Step3 striker failed")

        # Step 4: 抬起手臂
        self._arm.lift_after_shot(x=rx, y=flange_y, z_safe=Z_SAFE_HEIGHT, c=c)

        # Step 5: 歸零
        print(f"[RobotBrain] HOME（打擊結束）")
        self._arm.home(wait=True)

        return striker_ok

    # ── 私有輔助 ─────────────────────────────────────────────────────────

    def _pixel_to_mm(self, u: int, v: int) -> tuple[float, float]:
        x, y, ok = self._coord.pixel_to_mm(u, v)
        if not ok:
            print("[RobotBrain] 未校正，使用預設值")
            return 0.0, 0.0
        return x, y

    def _find_pocket_name(self, px: float, py: float) -> str:
        pockets = self._strategy.get_all_pockets_mm()
        best_name, best_dist = "top_left", float("inf")
        for name, (wx, wy) in pockets.items():
            d = math.hypot(px - wx, py - wy)
            if d < best_dist:
                best_dist = d
                best_name = name
        return best_name if best_dist <= 100 else "top_left"