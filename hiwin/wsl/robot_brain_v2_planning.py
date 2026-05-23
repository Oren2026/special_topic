"""
wsl/robot_brain_v2.py  [規劃中 - 未實施]
WSL 決策層 v2 設計骨架

Purpose:
- 把 robot_brain.py 的模式分派與商業邏輯分開
- 每個 mode = 一個乾淨的 Handler
- striker_bridge 從 MOCK 變正式
"""

# ══════════════════════════════════════════════════════════════════
# WSL 端接收的訊息類型（定義在 protocol.py）
# ══════════════════════════════════════════════════════════════════
#
# Windows → WSL
# ────────────────────────────────────────────────────────────────
# {"calibration_points": [[u1,v1], [u2,v2], [u3,v3], [u4,v4]]}
#     → _handle_calibration()
#
# {"mode": "MANUAL", "vision_data": [...]}
#     → _handle_manual()
#
# {"mode": "BREAK", "vision_data": [...]}
#     → _handle_break()
#
# {"mode": "AUTO", "vision_data": [...]}    ← STRATEGY 模式啟動
#     → _handle_auto()
#
# WSL → Windows
# ────────────────────────────────────────────────────────────────
# {"type": "CALIBRATION_COMPLETE", "pockets": [...]}
# {"type": "PREDICTION", ...}
# {"type": "BREAK_RESULT", ...}
# {"type": "STRATEGY_RESULT", ...}           ← 新增
# {"type": "ERROR", "message": "..."}


# ══════════════════════════════════════════════════════════════════
# Mode Handler 介面
# ══════════════════════════════════════════════════════════════════

from abc import ABC, abstractmethod
from typing import Optional


class ModeHandler(ABC):
    """
    WSL 端 Mode Handler 介面

    每個模式（MANUAL / BREAK / AUTO）對應一個 Handler，
    共同介面：
    - handle(packet: dict) → Optional[dict]
      回傳 None = 不回應 Windows
      回傳 dict = 主動回應（JSON 送回 Windows）
    """

    def __init__(self, coord_manager, strategy, striker, physics_validate):
        self._coord = coord_manager
        self._strategy = strategy
        self._striker = striker
        self._physics_validate = physics_validate

    @abstractmethod
    def handle(self, packet: dict) -> Optional[dict]:
        """處理該模式的封包，回傳回應或 None"""
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════
# Concrete Handlers
# ══════════════════════════════════════════════════════════════════

class ManualModeHandler(ModeHandler):
    """
    指定打擊

    輸入：
        {"mode": "MANUAL", "vision_data": [
            {"type": "POCKET", "u": int, "v": int},
            {"type": "TARGET_BALL", "u": int, "v": int},
            {"type": "CUE_BALL", "u": int, "v": int},
        ]}

    流程：
        1. pixel_to_mm (x3)
        2. _find_nearest_pocket_name (pixel → mm → 口袋名)
        3. strategy.compute_shot(obstacles=obstacles)
        4. striker.execute()            ← 實作（非 MOCK）
        5. _physics_validate()           ← Phase 2b
        6. 回應 PREDICTION

    輸出：
        {"type": "PREDICTION", "ghost_pixel": [...], "robot_pixel": [...],
         "is_reachable": bool, "angle": float, "shot_type": str,
         "physics_validated": bool}
    """

    def handle(self, packet: dict) -> dict:
        import math

        vision_data = packet.get("vision_data", [])

        # 解析
        p_pocket = next(p for p in vision_data if p["type"] == "POCKET")
        p_target = next(p for p in vision_data if p["type"] == "TARGET_BALL")
        p_cue    = next(p for p in vision_data if p["type"] == "CUE_BALL")

        # pixel → mm
        pocket_mm = self._coord.pixel_to_mm(p_pocket["u"], p_pocket["v"])
        target_mm = self._coord.pixel_to_mm(p_target["u"], p_target["v"])
        cue_mm    = self._coord.pixel_to_mm(p_cue["u"], p_cue["v"])

        # 口袋名稱
        pocket_name = self._find_pocket_name(p_pocket["u"], p_pocket["v"])

        # 策略計算（障礙球留空 = TODO）
        result = self._strategy.compute_shot(
            cue_ball={"x": cue_mm[0], "y": cue_mm[1]},
            target_ball={"x": target_mm[0], "y": target_mm[1]},
            pocket_name=pocket_name,
            obstacles=[],          # TODO: 從 AUTO 模式取得
        )

        # 手臂位置 (mm → pixel)
        ghost_u, ghost_v = self._coord.mm_to_pixel(*result["ghost"])
        robot_u, robot_v = self._coord.mm_to_pixel(*result["robot_tcp"])

        # ── 發送擊球指令（實作）───────────────────────────────────
        # 目前 MOCK → 實作後替換為真實 Arduino 指令
        striker_ok = self._striker.execute(
            robot_tcp=result["robot_tcp"],
            stroke_dist=result["stroke_dist"],
            angle=result["angle"],
        )
        # ───────────────────────────────────────────────────────────

        # 物理驗證（Phase 2b）
        physics_valid = self._physics_validate(
            cue_ball={"x": cue_mm[0], "y": cue_mm[1]},
            target_ball={"x": target_mm[0], "y": target_mm[1]},
            pocket_name=pocket_name,
            obstacles=[],
        )

        return {
            "type":               "PREDICTION",
            "ghost_pixel":        [ghost_u, ghost_v],
            "robot_pixel":        [robot_u, robot_v],
            "is_reachable":       result["is_reachable"],
            "angle":             result["angle"],
            "shot_type":         result.get("type", "direct"),
            "physics_validated": physics_valid,
            "striker_ok":         striker_ok,        # 新增：確認擊球機構狀態
        }

    def _find_pocket_name(self, u: int, v: int) -> str:
        """pixel → 口袋名稱（與現有 _find_nearest_pocket_name 相同）"""
        import math
        clicked_x, clicked_y, _ = self._coord.pixel_to_mm(u, v)
        pockets = self._strategy.get_all_pockets_mm()

        best_name, best_dist = "top_left", float("inf")
        for name, (px, py) in pockets.items():
            d = math.hypot(clicked_x - px, clicked_y - py)
            if d < best_dist:
                best_dist = d
                best_name = name

        if best_dist > 100:
            return "top_left"  # fallback
        return best_name


class BreakModeHandler(ModeHandler):
    """
    開球

    流程：
        1. pixel_to_mm (白球位置)
        2. break_module.compute_break()
        3. striker.execute(angle=90°, stroke=MAX)
        4. 回應 BREAK_RESULT
    """

    def handle(self, packet: dict) -> dict:
        vision_data = packet.get("vision_data", [])
        p_cue = next(p for p in vision_data if p["type"] == "CUE_BALL")

        cue_mm = self._coord.pixel_to_mm(p_cue["u"], p_cue["v"])

        result = self._break_strategy.compute_break(
            cue_ball_mm={"x": cue_mm[0], "y": cue_mm[1]}
        )

        robot_u, robot_v = self._coord.mm_to_pixel(*result["robot_tcp"])

        # 發送擊球指令
        striker_ok = self._striker.execute(
            robot_tcp=result["robot_tcp"],
            stroke_dist=result["stroke_dist"],
            angle=result["angle"],
        )

        return {
            "type":           "BREAK_RESULT",
            "robot_pixel":    [robot_u, robot_v],
            "is_reachable":   result["is_reachable"],
            "angle":          result["angle"],
            "stroke_dist":    result["stroke_dist"],
            "striker_ok":     striker_ok,
        }


class AutoModeHandler(ModeHandler):
    """
    自動打擊

    輸入：
        {"mode": "AUTO", "vision_data": [
            {"type": "CUE_BALL",    "u": int, "v": int, "number": 0},
            {"type": "TARGET_BALL", "u": int, "v": int, "number": 3},
            {"type": "OBSTACLE",    "u": int, "v": int, "number": 5},
            ...
        ]}

    流程：
        1. 解析所有球位置（pixel → mm）
        2. 分離 cue_ball / target_ball / obstacles
        3. 計算最佳 shot（考慮所有可行口袋）
        4. striker.execute()
        5. 回應 STRATEGY_RESULT（擴充版 PREDICTION）

    與 MANUAL 的區別：
        - MANUAL：使用者指定 POCKET + TARGET
        - AUTO：系統自動選擇 TARGET + POCKET（根據球位置排序）
    """

    def handle(self, packet: dict) -> dict:
        import math

        vision_data = packet.get("vision_data", [])

        # ── 分離球角色 ─────────────────────────────────────────
        cue_ball = None
        other_balls = []

        for ball in vision_data:
            x, y, _ = self._coord.pixel_to_mm(ball["u"], ball["v"])
            if ball.get("number") == 0 or ball["type"] == "CUE_BALL":
                cue_ball = {"x": x, "y": y}
            else:
                other_balls.append({"x": x, "y": y, "number": ball.get("number", -1)})

        if cue_ball is None:
            return {"type": "ERROR", "message": "未偵測到白球"}

        # ── 選擇目標球與口袋 ───────────────────────────────────
        # 策略：選擇最靠近的球 + 最近的口袋
        # TODO: 替換為完整策略排序（考慮 9號球、最短路徑等）
        target = other_balls[0] if other_balls else None
        if target is None:
            return {"type": "ERROR", "message": "無可打擊的球"}

        pocket_name = self._auto_select_pocket(cue_ball, target)

        # ── 障礙球 ─────────────────────────────────────────────
        obstacles = other_balls[1:]  # 除 cue + target 外的所有球

        # ── 策略計算 ───────────────────────────────────────────
        result = self._strategy.compute_shot(
            cue_ball=cue_ball,
            target_ball=target,
            pocket_name=pocket_name,
            obstacles=obstacles,
        )

        # ── 執行 ───────────────────────────────────────────────
        striker_ok = self._striker.execute(
            robot_tcp=result["robot_tcp"],
            stroke_dist=result["stroke_dist"],
            angle=result["angle"],
        )

        # ── 回應 ───────────────────────────────────────────────
        ghost_u, ghost_v = self._coord.mm_to_pixel(*result["ghost"])
        robot_u, robot_v = self._coord.mm_to_pixel(*result["robot_tcp"])

        return {
            "type":           "STRATEGY_RESULT",
            "target_number":  target.get("number", -1),
            "pocket_name":    pocket_name,
            "ghost_pixel":    [ghost_u, ghost_v],
            "robot_pixel":    [robot_u, robot_v],
            "is_reachable":   result["is_reachable"],
            "angle":          result["angle"],
            "shot_type":      result.get("type", "direct"),
            "obstacles_count": len(obstacles),
            "striker_ok":     striker_ok,
        }

    def _auto_select_pocket(self, cue_ball, target_ball) -> str:
        """
        自動選擇口袋：簡單貪心（選擇離目標球最近的口袋）
        TODO: 替換為 multi-pocket 評估（考慮障礙球、進球角度等）
        """
        import math
        pockets = self._strategy.get_all_pockets_mm()
        best_name, best_dist = "top_left", float("inf")

        tx, ty = target_ball["x"], target_ball["y"]
        for name, (px, py) in pockets.items():
            d = math.hypot(tx - px, ty - py)
            if d < best_dist:
                best_dist = d
                best_name = name

        return best_name


# ══════════════════════════════════════════════════════════════════
# StrikerBridge 實作（非 MOCK）
# ══════════════════════════════════════════════════════════════════
#
# Arduino 指令集（定義在 references/arduino-striker-sketch.md）：
#   home              → 回原點
#   goto {dist}       → 絕對移動至擊球距離（mm）
#   move {dist}       → 相對移動（mm）
#   speed {delay}     → 速度（越大越慢）
#   status            → 查詢狀態
#   stop              → 立即停止
#
# Arduino 回應：
#   "HOME DONE"       — 歸位完成
#   "DONE"            — 移動完成
#   "ERROR OUT_OF_RANGE" — 超出範圍
#   "UNKNOWN COMMAND"  — 不認識的指令
#
# 鮑率：9600


class StrikerBridge:
    """
    擊球機構 bridge

    實作（取代 MOCK）：
        1. 開啟 Serial 連線（/dev/ttyUSB0 或類似）
        2. 發送 "goto {stroke_dist}\n"
        3. 等待 "DONE\n" 回應（超时 30s）
        4. 回傳 True/False
    """

    def __init__(self, port="/dev/ttyUSB0", baud=9600, timeout=30):
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._serial = None

    # ── 連線管理 ─────────────────────────────────────────────────

    def connect(self) -> bool:
        """連線至 Arduino"""
        # TODO: 實作 serial.Serial() 連線
        # try:
        #     import serial
        #     self._serial = serial.Serial(self._port, self._baud, timeout=5)
        #     return True
        # except Exception as e:
        #     print(f"[StrikerBridge] 連線失敗: {e}")
        #     return False
        raise NotImplementedError("等待實作")

    def disconnect(self):
        if self._serial:
            self._serial.close()

    # ── 擊球執行 ─────────────────────────────────────────────────

    def execute(self, robot_tcp: tuple, stroke_dist: float, angle: float) -> bool:
        """
        執行擊球

        參數：
            robot_tcp: (x, y) 手臂停頓位置（目前未使用，預留）
            stroke_dist: 擊球距離（mm）
            angle: 擊球角度（度，目前未使用）

        回傳：True = 成功，False = 失敗
        """
        import time

        # MOCK 模式（目前）
        print(f"[StrikerBridge] MOCK execute: goto {stroke_dist:.1f}mm")

        # ── 實作模式 ─────────────────────────────────────────────
        # if not self._serial:
        #     self.connect()
        #
        # cmd = f"goto {int(stroke_dist)}\n"
        # self._serial.write(cmd.encode())
        #
        # # 等待回應
        # start = time.time()
        # while time.time() - start < self._timeout:
        #     line = self._serial.readline().decode().strip()
        #     if line == "DONE":
        #         return True
        #     elif line == "ERROR OUT_OF_RANGE":
        #         print("[StrikerBridge] 超出範圍")
        #         return False
        #
        # print("[StrikerBridge] 逾時")
        # return False
        # ─────────────────────────────────────────────────────────

        return True  # MOCK：永遠成功


# ══════════════════════════════════════════════════════════════════
# RobotBrain v2
# ══════════════════════════════════════════════════════════════════

class RobotBrainV2:
    """
    WSL 大腦 v2

    變更：
        - 移除 _handle_manual / _handle_break 等大型函式
        - 改為 Handler 映射，乾淨的 dispatch
        - 新增 AUTO 模式處理
        - striker_bridge 從 MOCK 變實作
    """

    def __init__(self):
        # 依賴元件
        from coord_manager import CoordinateManager
        from strategy_module import BilliardStrategy
        from break_module import BreakStrategy

        self._coord = CoordinateManager()
        self._strategy = BilliardStrategy()
        self._break_strategy = BreakStrategy()

        # ── Striker Bridge（MOCK → 實作）───────────────────────
        # TODO: 替換為 StrikerBridge("/dev/ttyUSB0")
        self._striker = StrikerBridge()   # MOCK
        # ────────────────────────────────────────────────────────

        # ── 物理驗證（Phase 2b）───────────────────────────────
        self._physics_validate = self._make_physics_validator()

        # ── Mode Handlers ──────────────────────────────────────
        self._handlers: dict[str, ModeHandler] = {
            "MANUAL": ManualModeHandler(
                self._coord, self._strategy, self._striker, self._physics_validate
            ),
            "BREAK": BreakModeHandler(
                self._coord, self._strategy, self._striker, self._physics_validate
            ),
            "AUTO": AutoModeHandler(
                self._coord, self._strategy, self._striker, self._physics_validate
            ),
            # "STRATEGY": StrategyModeHandler,  # 與 AUTO 整合
        }

    # ── 啟動（與 v1 相同）────────────────────────────────────────

    def start(self, host=None, port=None):
        import socket, json, config, protocol as P

        host = host or config.SOCKET_HOST
        port = port or config.SOCKET_PORT

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        print(f"[RobotBrain v2] 啟動，監聽 {host}:{port}")

        while True:
            conn, addr = server.accept()
            print(f"[RobotBrain v2] 連線：{addr}")
            self._serve(conn)
            conn.close()

    def _serve(self, conn):
        import json, protocol as P

        buf = ""
        while True:
            data = conn.recv(4096).decode("utf-8")
            if not data:
                break
            buf += data
            while P.TERMINATOR in buf:
                line, buf = buf.split(P.TERMINATOR, 1)
                if not line.strip():
                    continue
                try:
                    packet = json.loads(line)
                    response = self._dispatch(packet)
                    if response:
                        conn.send(
                            (json.dumps(response) + P.TERMINATOR).encode("utf-8")
                        )
                except json.JSONDecodeError:
                    pass

    # ── 分派 ─────────────────────────────────────────────────────

    def _dispatch(self, packet: dict) -> Optional[dict]:
        import protocol as P

        # 校正（無 mode 欄位）
        if P.FIELD_CAL_POINTS in packet:
            return self._handle_calibration(packet)

        mode = packet.get(P.FIELD_MODE, "")

        handler = self._handlers.get(mode)
        if handler:
            return handler.handle(packet)

        print(f"[RobotBrain v2] 未知模式：{mode}")
        return None

    def _handle_calibration(self, packet: dict) -> dict:
        import protocol as P

        pts = packet[P.FIELD_CAL_POINTS]
        self._coord.update_calibration(pts)

        pockets_mm = self._strategy.get_all_pockets_mm()
        pockets_pixel = self._coord.get_pockets_pixel(pockets_mm)

        return {
            P.FIELD_TYPE: P.MSG_TYPE_CALIBRATION_COMPLETE,
            "pockets": pockets_pixel,
        }

    # ── 物理驗證工廠 ─────────────────────────────────────────────

    def _make_physics_validator(self):
        """
        Phase 2b 物理驗證工廠

        閉包捕獲 self._strategy，用於 Handler 内部呼叫
        """
        import os, sys
        _physics_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        if _physics_root not in sys.path:
            sys.path.insert(0, _physics_root)
        from physics import simulate as physics_simulate

        def validate(cue_ball, target_ball, pocket_name, obstacles) -> bool:
            try:
                phys_input = self._strategy.get_shot_physics_input(
                    cue_ball, target_ball, pocket_name, obstacles
                )
                if phys_input is None:
                    return True  # 預設放行

                result = physics_simulate(
                    cue_pos=phys_input["cue_pos"],
                    cue_dir=phys_input["aim_dir"],
                    target_pos=phys_input["target_pos"],
                    pocket_pos=phys_input["pocket_pos"],
                    obstacles=phys_input["obstacles"],
                    speed=phys_input["speed"],
                    dt_ms=10,
                )

                for event in result.collision_events:
                    if event.ball1_id == "cue" and event.ball2_id == "target":
                        return True
                return False
            except Exception:
                return True  # 預設放行

        return validate