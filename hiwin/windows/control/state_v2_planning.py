"""
windows/control/state_v2.py  [規劃中 - 未實施]
狀態機 v2 設計骨架

目的：用 Python 類別表達 UI 狀態機結構，尚未整合进專案
"""

from enum import Enum, auto
from typing import Optional, Callable


# ══════════════════════════════════════════════════════════════════
# 狀態列舉
# ══════════════════════════════════════════════════════════════════

class State(Enum):
    """8 個核心狀態"""
    # ── 校正區 ──
    IDLE        = auto()   # 待機
    TABLE_CAL   = auto()   # 球桌校正（4角 Homography）
    SHAPE_CAL   = auto()   # 球型校正（半徑取樣→scale）
    COLOR_CAL   = auto()   # 球色校正（HSV取樣→YAML）

    # ── 打擊區 ──
    MANUAL      = auto()   # 指定打擊（POCKET → TARGET → CUE）
    BREAK       = auto()   # 開球
    AUTO        = auto()   # 自動打擊（視覺偵測）
    STRATEGY    = auto()   # 策略打擊（compute_shot + striker）


class StateGroup(Enum):
    """狀態群組（用於 UI 區塊渲染）"""
    CALIBRATION = auto()   # 校正區
    STRIKE      = auto()   # 打擊區


# ══════════════════════════════════════════════════════════════════
# 狀態群組對應表
# ══════════════════════════════════════════════════════════════════

STATE_GROUPS = {
    # 校正區
    State.IDLE:       StateGroup.CALIBRATION,  # 開機時停留在這
    State.TABLE_CAL:  StateGroup.CALIBRATION,
    State.SHAPE_CAL:  StateGroup.CALIBRATION,
    State.COLOR_CAL:  StateGroup.CALIBRATION,
    # 打擊區
    State.MANUAL:     StateGroup.STRIKE,
    State.BREAK:      StateGroup.STRIKE,
    State.AUTO:       StateGroup.STRIKE,
    State.STRATEGY:   StateGroup.STRIKE,
}


# ══════════════════════════════════════════════════════════════════
# 狀態行為矩陣
# ══════════════════════════════════════════════════════════════════

class StateBehavior:
    """
    每個狀態的行為定義（純資料，無邏輯）
    """

    TABLE_CAL = {
        "name":         "球桌校正",
        "group":        StateGroup.CALIBRATION,
        "steps":        4,                        # 需點擊 4 個角
        "step_label":   ["左上", "右上", "右下", "左下"],
        "requires_cal": False,                   # TABLE_CAL 不依賴自身
        "on_complete":  "save_json",              # 完成後動作
        "output":       "calibration.json",
    }

    SHAPE_CAL = {
        "name":         "球型校正",
        "group":        StateGroup.CALIBRATION,
        "steps":        3,                        # 至少取 3 球
        "step_label":   None,                     # 無步驟標籤，連續取樣
        "requires_cal": True,                     # 需要 calibration.json
        "on_complete":  "save_yaml",              # 寫入 ball_geometry.yaml
        "output":       "ball_geometry.yaml",
    }

    COLOR_CAL = {
        "name":         "球色校正",
        "group":        StateGroup.CALIBRATION,
        "steps":        10,                       # 球號 0-9（0=白球）
        "step_label":   ["球0(白)", "球1", "球2", ...],  # 動態生成
        "requires_cal": True,
        "on_complete":  "save_yaml",
        "output":       "color_ranges.yaml",
    }

    MANUAL = {
        "name":         "指定打擊",
        "group":        StateGroup.STRIKE,
        "steps":        3,
        "step_label":   ["口袋", "目標球", "白球"],
        "requires_cal": True,
        "on_complete":  "send_to_wsl",            # TCP → robot_brain
        "output":       "PREDICTION",
    }

    BREAK = {
        "name":         "開球",
        "group":        StateGroup.STRIKE,
        "steps":        1,
        "step_label":   ["白球位置"],
        "requires_cal": True,
        "on_complete":  "send_to_wsl",
        "output":       "BREAK_RESULT + striker.execute()",
    }

    AUTO = {
        "name":         "自動打擊",
        "group":        StateGroup.STRIKE,
        "steps":        0,                        # 全自動，無需點擊
        "step_label":   None,
        "requires_cal": True,
        "on_complete":  "transition_to_STRATEGY", # 自動進入 STRATEGY
        "output":       "CompeteScene（所有球位置）",
    }

    STRATEGY = {
        "name":         "策略打擊",
        "group":        StateGroup.STRIKE,
        "steps":        0,                        # 若無需確認則全自動
        "step_label":   None,
        "requires_cal": True,
        "on_complete":  "striker.execute() + physics_validate",
        "output":       "PREDICTION + 執行結果",
    }


# ══════════════════════════════════════════════════════════════════
# StateMachine v2
# ══════════════════════════════════════════════════════════════════

class StateMachineV2:
    """
    狀態機 v2

    設計原則：
    - 單一職責：狀態機只管「狀態轉換」，不處理 UI 也不處理商業邏輯
    - 可插拔：handler 是獨立的物件，替換 handler = 替換行為
    - 事件驅動：handle_event() 是唯一對外 API
    """

    def __init__(self, socket_client, vision, hmi):
        self._mode = State.IDLE
        self._socket = socket_client
        self._vision = vision
        self._hmi = hmi

        # ── Handler 映射（狀態 → 處理物件）───────────────────────
        self._handlers: dict[State, "StateHandler"] = {}

        # ── 事件監聽器 ────────────────────────────────────────────
        self._listeners: list[Callable[[State, State, dict], None]] = []

    # ── 公開 API ─────────────────────────────────────────────────────

    def current_state(self) -> State:
        return self._mode

    def transition_to(self, new_state: State) -> None:
        """狀態切換（所有狀態變更的單一入口）"""
        old = self._mode
        if old == new_state:
            return

        # exit old state
        if old in self._handlers:
            self._handlers[old].on_exit()

        self._mode = new_state

        # enter new state
        if new_state in self._handlers:
            self._handlers[new_state].on_enter()

        # notify listeners
        for cb in self._listeners:
            cb(old, new_state, {})

    def handle_event(self, event_type: str, data: dict) -> dict:
        """
        統一事件處理
        event_type: "click" | "drag" | "wsla_response" | "cancel"
        data:       event payload
        """
        handler = self._handlers.get(self._mode)
        if handler is None:
            return {"status": "no_handler"}

        return handler.handle(event_type, data)

    def on_state_change(self, callback: Callable):
        """訂閱狀態變更事件"""
        self._listeners.append(callback)

    # ── Handler 註冊 ─────────────────────────────────────────────────

    def register(self, state: State, handler: "StateHandler"):
        self._handlers[state] = handler


# ══════════════════════════════════════════════════════════════════
# StateHandler 協定（所有 Handler 需實作）
# ══════════════════════════════════════════════════════════════════

class StateHandler:
    """
    狀態處理器介面

    每個 State 對應一個 Handler，Handler 知道：
    - 該狀態需要什麼資料
    - 資料收集夠了之後做什麼
    - 怎麼回復 IDLE
    """

    def __init__(self, sm: StateMachineV2, socket, vision):
        self._sm = sm
        self._socket = socket
        self._vision = vision

    # ── 狀態生命週期鉤子 ──────────────────────────────────────────

    def on_enter(self) -> None:
        """進入狀態時呼叫（例如：顯示提示、初始化內部狀態）"""
        pass

    def on_exit(self) -> None:
        """離開狀態時呼叫（例如：釋放資源、取消訂閱）"""
        pass

    # ── 事件處理 ──────────────────────────────────────────────────

    def handle(self, event_type: str, data: dict) -> dict:
        """
        處理事件
        回傳：{"status": "ok" | "pending" | "complete", "info": ...}
        """
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════
# Concrete Handlers（規劃中，待實作）
# ══════════════════════════════════════════════════════════════════

class TableCalHandler(StateHandler):
    """
    球桌校正處理器

    流程：
    1. on_enter() → 顯示「請依序點擊四個角」
    2. 收到 click → add_point()，追蹤第幾點
    3. 4點完成 → 發送 socket → 存 calibration.json → 回 IDLE
    """

    def __init__(self, sm, socket, vision):
        super().__init__(sm, socket, vision)
        self._points: list[tuple[int, int]] = []

    def on_enter(self) -> None:
        self._points = []

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type != "click":
            return {"status": "ignored"}

        u, v = data["u"], data["v"]
        self._points.append((u, v))

        if len(self._points) == 4:
            # 發送並儲存
            packet = {"calibration_points": self._points}
            self._socket.send(packet)

            # TODO: CalibrationHandler.save_json()
            return {"status": "complete", "state": "IDLE"}
        else:
            return {
                "status":       "pending",
                "progress":     f"第 {len(self._points)} / 4 點",
                "next_hint":    f"請點擊：{['左上','右上','右下','左下'][len(self._points)]}",
            }


class ManualStrikeHandler(StateHandler):
    """
    指定打擊處理器

    流程：
    1. on_enter() → 提示「請依序點擊：口袋 → 目標球 → 白球」
    2. 依序收集 POCKET / TARGET_BALL / CUE_BALL
    3. 3步完成 → socket.send() → 等待 PREDICTION → 回 IDLE
    """

    # 定義收集順序
    SHOT_SEQUENCE = ["POCKET", "TARGET_BALL", "CUE_BALL"]
    LABELS = {
        "POCKET":      "口袋",
        "TARGET_BALL": "目標球",
        "CUE_BALL":    "白球",
    }

    def __init__(self, sm, socket, vision):
        super().__init__(sm, socket, vision)
        self._collected: dict[str, tuple[int, int]] = {}
        self._shot_sent = False

    def on_enter(self) -> None:
        self._collected = {}
        self._shot_sent = False

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "wsla_response":
            return self._handle_wsl_response(data)

        if event_type != "click":
            return {"status": "ignored"}

        # 依序取下一個需要的類型
        next_type = self._next_required()
        if next_type is None:
            return {"status": "already_complete"}

        u, v = data["u"], data["v"]
        self._collected[next_type] = (u, v)

        if len(self._collected) == 3:
            # 發送
            packet = {
                "mode": "MANUAL",
                "vision_data": [
                    {"type": "POCKET",       "u": self._collected["POCKET"][0],       "v": self._collected["POCKET"][1]},
                    {"type": "TARGET_BALL",  "u": self._collected["TARGET_BALL"][0], "v": self._collected["TARGET_BALL"][1]},
                    {"type": "CUE_BALL",     "u": self._collected["CUE_BALL"][0],    "v": self._collected["CUE_BALL"][1]},
                ],
            }
            self._socket.send(packet)
            self._shot_sent = True
            return {"status": "waiting_response"}

        return {
            "status":     "pending",
            "next_label": self.LABELS[next_type],
        }

    def _next_required(self) -> Optional[str]:
        for t in self.SHOT_SEQUENCE:
            if t not in self._collected:
                return t
        return None

    def _handle_wsl_response(self, data: dict) -> dict:
        # WSL 回傳 PREDICTION
        return {"status": "complete", "state": "IDLE", "data": data}


class BreakHandler(StateHandler):
    """
    開球處理器
    """

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "wsla_response":
            return {"status": "complete", "state": "IDLE", "data": data}

        if event_type != "click":
            return {"status": "ignored"}

        if self._shot_sent:
            return {"status": "already_complete"}

        u, v = data["u"], data["v"]
        packet = {
            "mode": "BREAK",
            "vision_data": [{"type": "CUE_BALL", "u": u, "v": v}],
        }
        self._socket.send(packet)
        self._shot_sent = True
        return {"status": "waiting_response"}


class AutoStrikeHandler(StateHandler):
    """
    自動打擊處理器

    流程：
    1. on_enter() → 啟動 VisionBridge.capture_and_process()
    2. 偵測到球 → 自動進入 STRATEGY 狀態
    """

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type != "wsla_response":
            return {"status": "ignored"}

        # data = CompeteScene
        balls = data.get("balls", [])
        obstacles = [b for b in balls if b["type"] not in ("CUE_BALL", "TARGET_BALL")]

        if not balls:
            return {"status": "retry", "hint": "未偵測到球，重試中..."}

        # 自動進入 STRATEGY
        self._sm.transition_to(State.STRATEGY)
        # 注入障礙球資料到 STRATEGY handler
        return {"status": "transition", "next_state": "STRATEGY", "obstacles": obstacles}


class StrategyHandler(StateHandler):
    """
    策略打擊處理器

    接收 AUTO 的偵測結果：
    - 所有球位置（obstacles）
    - 使用者選的口袋（或自動選擇最佳口袋）

    執行：
    1. strategy_module.compute_shot(cue, target, pocket, obstacles)
    2. striker_bridge.execute()
    3. physics_simulate 驗證（可同步可異步）
    """

    def __init__(self, sm, socket, vision):
        super().__init__(sm, socket, vision)
        self._obstacles: list = []    # 從 AUTO 取得
        self._selected_pocket: str = "top_left"  # TODO: 需 UI 選擇或自動

    def on_enter(self, obstacles: list = None, pocket: str = None) -> None:
        """AUTO 進入 STRATEGY 時呼叫，帶入障礙球和口袋"""
        if obstacles is not None:
            self._obstacles = obstacles
        if pocket is not None:
            self._selected_pocket = pocket

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "execute":
            return self._do_strategy()
        return {"status": "pending"}

    def _do_strategy(self) -> dict:
        # TODO: 串接 strategy_module + striker_bridge + physics
        return {"status": "complete", "state": "IDLE"}


# ══════════════════════════════════════════════════════════════════
# 工廠函式（註冊所有 handler）
# ══════════════════════════════════════════════════════════════════

def build_state_machine(socket, vision, hmi) -> StateMachineV2:
    """建立並連接所有 handler"""
    sm = StateMachineV2(socket, vision, hmi)

    sm.register(State.TABLE_CAL,  TableCalHandler(sm, socket, vision))
    sm.register(State.MANUAL,     ManualStrikeHandler(sm, socket, vision))
    sm.register(State.BREAK,      BreakHandler(sm, socket, vision))
    sm.register(State.AUTO,       AutoStrikeHandler(sm, socket, vision))
    sm.register(State.STRATEGY,   StrategyHandler(sm, socket, vision))

    # SHAPE_CAL / COLOR_CAL → TODO（細節待確認）

    return sm