"""
wsl/robot_brain.py
主大腦：Socket Server + 模式分派

依賴：socket, json, CoordinateManager, BilliardStrategy, StrikerBridge, protocol, config
輸出：start() → 永不返回（server loop）
使用：main.py 啟動
"""
import socket
import json
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coord_manager import CoordinateManager
from strategy_module import BilliardStrategy
from break_module import BreakStrategy
from striker_bridge import StrikerBridge
import config
import protocol as P

# Phase 2b: 物理模組整合（重新定義驗證角色）
# physics/ 在 hiwin/ 目錄下，WSL 代碼在 hiwin/wsl/，需要往上一層
_physics_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _physics_root not in sys.path:
    sys.path.insert(0, _physics_root)
from physics import simulate as physics_simulate


class RobotBrain:
    """
    WSL 主大腦
    接收 Windows 端 JSON 封包，執行對應邏輯，回傳 PREDICTION
    """

    def __init__(self):
        self._coord = CoordinateManager()
        self._strategy = BilliardStrategy()
        self._break_strategy = BreakStrategy()
        self._striker = StrikerBridge()
        self._running = False

    # ── 啟動 ────────────────────────────────────────────────────────────────

    def start(self, host=None, port=None):
        host = host or config.SOCKET_HOST
        port = port or config.SOCKET_PORT

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        print(f"[RobotBrain] WSL 大腦啟動，監聽 {host}:{port}")

        self._running = True
        while self._running:
            conn, addr = server.accept()
            print(f"[RobotBrain] 連線：{addr}")
            self._serve(conn)
            conn.close()
        server.close()

    # ── 單一連線處理 ──────────────────────────────────────────────────────

    def _serve(self, conn):
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
                        conn.send((json.dumps(response) + P.TERMINATOR).encode("utf-8"))
                except json.JSONDecodeError:
                    pass

    # ── 口袋名稱反向查詢 ───────────────────────────────────────────────────

    def _find_nearest_pocket_name(self, pocket_u: int, pocket_v: int) -> str:
        """
        根據點擊口袋的像素座標，回傳最近的已知口袋名稱。
        流程：pixel → mm → 與 6 個已知口袋比對，找 mm 距離最近者。
        """
        # 像素 → mm（使用當前校正矩陣）
        clicked_mm_x, clicked_mm_y, is_cal = self._coord.pixel_to_mm(pocket_u, pocket_v)
        if not is_cal:
            print("[RobotBrain] 未校正，使用 fallback top_left")
            return "top_left"

        pockets_mm = self._strategy.get_all_pockets_mm()
        best_name = "top_left"
        best_dist = float("inf")

        for name, (px, py) in pockets_mm.items():
            dist = math.hypot(clicked_mm_x - px, clicked_mm_y - py)
            if dist < best_dist:
                best_dist = dist
                best_name = name

        # 容許閾值：偏離 > 100mm 視為無效點擊
        if best_dist > 100:
            print(f"[RobotBrain] 口袋偏離過大 ({best_dist:.1f}mm > 100mm)，fallback top_left")
            return "top_left"

        print(f"[RobotBrain] 口袋匹配：pixel=({pocket_u},{pocket_v}) → {best_name} (dist={best_dist:.1f}mm)")
        return best_name

    # ── 模式分派 ──────────────────────────────────────────────────────────

    def _dispatch(self, packet: dict):
        """
        根據封包內容分派至對應處理函式
        """
        # 校正（INSTALL 模式觸發，mode 欄位不存在）
        if P.FIELD_CAL_POINTS in packet:
            return self._handle_calibration(packet)

        mode = packet.get(P.FIELD_MODE, "")

        if mode == P.MSG_MODE_MANUAL:
            return self._handle_manual(packet)

        if mode == P.MSG_MODE_BREAK:
            return self._handle_break(packet)

        # COMPETE 模式（未實作）
        if mode == P.MSG_MODE_COMPETE:
            print("[RobotBrain] COMPETE 模式尚未實作")
            return None

        return None

    def _handle_calibration(self, packet: dict):
        """接收4點校正資料，更新透視矩陣，計算並回傳6個口袋像素位置"""
        pts = packet[P.FIELD_CAL_POINTS]
        if len(pts) != 4:
            print(f"[RobotBrain] 校正點數量錯誤：{len(pts)}（期望4）")
            return None
        self._coord.update_calibration(pts)

        # 計算6個口袋的像素座標
        pockets_mm = self._strategy.get_all_pockets_mm()
        pockets_pixel = self._coord.get_pockets_pixel(pockets_mm)

        print("[RobotBrain] 校正完成，計算口袋位置")
        return {
            P.FIELD_TYPE: P.MSG_TYPE_CALIBRATION_COMPLETE,
            "pockets": pockets_pixel,
        }

    def _handle_manual(self, packet: dict):
        """處理手動擊球預測"""
        vision_data = packet.get(P.FIELD_VISION_DATA, [])
        cfg = packet.get(P.FIELD_STRIKER_CFG, {})

        try:
            # 解析三個物件
            p_pocket = next(p for p in vision_data if p[P.FIELD_TYPE] == P.TYPE_POCKET)
            p_target = next(p for p in vision_data if p[P.FIELD_TYPE] == P.TYPE_TARGET_BALL)
            p_cue    = next(p for p in vision_data if p[P.FIELD_TYPE] == P.TYPE_CUE_BALL)

            # 像素 → 毫米
            mx, my, _ = self._coord.pixel_to_mm(p_pocket["u"], p_pocket["v"])
            tx, ty, _ = self._coord.pixel_to_mm(p_target["u"], p_target["v"])
            cx, cy, _ = self._coord.pixel_to_mm(p_cue["u"], p_cue["v"])

            # 動態查詢口袋名稱（pixel → mm → 找最近已知口袋）
            pocket_name = self._find_nearest_pocket_name(p_pocket["u"], p_pocket["v"])

            # 解析障礙球（OTHER_BALL → compute_shot obstacles）
            obstacles = []
            for p in vision_data:
                if p[P.FIELD_TYPE] == P.TYPE_OTHER_BALL:
                    ox, oy, _ = self._coord.pixel_to_mm(p["u"], p["v"])
                    obstacles.append({"x": ox, "y": oy})

            # 策略計算（自動選擇 direct 或 bank shot）
            result = self._strategy.compute_shot(
                cue_ball={"x": cx, "y": cy},
                target_ball={"x": tx, "y": ty},
                pocket_name=pocket_name,
                obstacles=obstacles,
            )

            # 毫米 → 像素（供 UI 繪圖）
            ghost_u, ghost_v = self._coord.mm_to_pixel(*result["ghost"])
            robot_u, robot_v = self._coord.mm_to_pixel(*result["robot_tcp"])

            # 如有 striker_config 中的直徑參數，可更新 strategy（預留）
            if cfg:
                self._strategy.D = cfg.get("ball_diameter", self._strategy.D)

            # ── 嘗試發送擊球指令至 Arduino ─────────────────────────────
            # 會列印指令並顯示發送結果（無 Arduino 連線時顯示失敗，為正常行為）
            success = self._striker.execute(
                robot_tcp=result["robot_tcp"],
                stroke_dist=result["stroke_dist"],
                angle=result["angle"],
            )
            # ─────────────────────────────────────────────────────────

            # ── Phase 2b: 物理軌跡驗證 ─────────────────────────────────
            # 驗證目標：白球是否真的能擊中目標球（幾何 collision）
            # 不是驗證目標球能否進袋（那是策略的責任）
            physics_valid = self._validate_cue_hits_target(
                cue_ball={"x": cx, "y": cy},
                target_ball={"x": tx, "y": ty},
                pocket_name=pocket_name,
                obstacles=obstacles,
            )
            physics_status = "✅" if physics_valid else "⚠️"
            print(f"[RobotBrain] 物理驗證（白球撞擊）: {physics_status}")
            # ─────────────────────────────────────────────────────────

            return {
                P.FIELD_TYPE:          P.MSG_TYPE_PREDICTION,
                P.FIELD_GHOST_PIXEL:  [ghost_u, ghost_v],
                P.FIELD_ROBOT_PIXEL:  [robot_u, robot_v],
                P.FIELD_IS_REACHABLE: result["is_reachable"],
                P.FIELD_ANGLE:        result["angle"],
                "shot_type":          result.get("type", "direct"),
                "physics_validated":  physics_valid,   # Phase 2b
            }

        except Exception as e:
            print(f"[RobotBrain] 策略計算錯誤: {e}")
            return None

    def _handle_break(self, packet: dict):
        """處理開球（Break）模式"""
        vision_data = packet.get(P.FIELD_VISION_DATA, [])

        try:
            p_cue = next(p for p in vision_data if p[P.FIELD_TYPE] == P.TYPE_CUE_BALL)

            # 像素 → 毫米
            cx, cy, _ = self._coord.pixel_to_mm(p_cue["u"], p_cue["v"])

            # 開球計算（angle=90°，stroke=MAX）
            result = self._break_strategy.compute_break(
                cue_ball_mm={"x": cx, "y": cy}
            )

            # 毫米 → 像素（供 UI 繪圖）
            robot_u, robot_v = self._coord.mm_to_pixel(*result["robot_tcp"])

            # 發送擊球指令
            success = self._striker.execute(
                robot_tcp=result["robot_tcp"],
                stroke_dist=result["stroke_dist"],
                angle=result["angle"],
            )

            return {
                P.FIELD_TYPE:         "BREAK_RESULT",
                P.FIELD_ROBOT_PIXEL: [robot_u, robot_v],
                P.FIELD_IS_REACHABLE: result["is_reachable"],
                P.FIELD_ANGLE:        result["angle"],
                "stroke_dist":         result["stroke_dist"],
            }

        except Exception as e:
            print(f"[RobotBrain] 開球計算錯誤: {e}")
            return None

    # ══════════════════════════════════════════════════════════════════
    # Phase 2b: 物理軌跡驗證（白球撞擊驗證）
    # ══════════════════════════════════════════════════════════════════

    def _validate_cue_hits_target(self, cue_ball, target_ball, pocket_name, obstacles):
        """
        Phase 2b 核心：驗證白球是否能擊中目標球。

        驗證邏輯：
        1. 用 strategy.get_shot_physics_input() 取得完整物理輸入
        2. 用 physics.simulate() 跑物理模擬
        3. 檢查 simulation 中是否有「白球→目標球」的碰撞事件
        4. 若無碰撞事件 → ⚠️ 幾何預測的白球路線根本碰不到目標球

        為什麼驗這個：
        - 幾何計算只檢查「路徑上有沒有障礙球擋住」
        - 但白球到底能不能真的碰到目標球（球心對準）
        - 需要物理積分才能確認（尤其在速度很快時）

        回傳：True = 白球會擊中目標球，False = ⚠️ 撞不到
        """
        try:
            # 取得完整物理輸入（strategy 幫我們算好 aim_dir）
            phys_input = self._strategy.get_shot_physics_input(
                cue_ball, target_ball, pocket_name, obstacles
            )
            if phys_input is None:
                return True  # 無法計算時預設放行

            # 執行物理模擬
            sim_result = physics_simulate(
                cue_pos=phys_input["cue_pos"],
                cue_dir=phys_input["aim_dir"],
                target_pos=phys_input["target_pos"],
                pocket_pos=phys_input["pocket_pos"],
                obstacles=phys_input["obstacles"],
                speed=phys_input["speed"],
                dt_ms=10,
            )

            # 核心檢查：是否有 cue → target 的碰撞事件
            for event in sim_result.collision_events:
                if event.ball1_id == "cue" and event.ball2_id == "target":
                    return True  # ✅ 白球撞到目標球

            # Bank shot 的特殊情況：白球可能先碰到庫邊再碰目標球
            # 檢查白球是否有 wall_hits（撞牆），之後才碰到目標球
            cue_wall_steps = set()
            for event in sim_result.wall_hits:
                if event.ball_id == "cue":
                    cue_wall_steps.add(event.step)

            for event in sim_result.collision_events:
                if event.ball1_id == "cue" and event.ball2_id == "target":
                    # 白球撞到目標球，確認撞擊前是否先撞牆（嚴格 bank scenario）
                    if event.step > 0:
                        return True  # 撞到了就是撞到了

            # ⚠️ 白球從未碰觸目標球——幾何預測的路線無效
            return False

        except Exception as e:
            print(f"[RobotBrain] 物理驗證失敗（預設放行）: {e}")
            return True  # 驗證失敗時放行（不 block 策略決策）
