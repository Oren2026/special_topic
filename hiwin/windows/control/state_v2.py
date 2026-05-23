"""
windows/control/state_v2.py  [規劃中 - 未實施]
狀態機 v2（Windows-Only 版）

與 v1 差異：
- Handler 接管所有商業邏輯
- 不再需要 socket_client（WSL 移除後全在同一進程）
- StateMachine 只管狀態轉換，handle_event 是唯一對外 API
"""

from enum import Enum, auto
from typing import Optional, Callable


# ══════════════════════════════════════════════════════════════════
# 狀態列舉
# ══════════════════════════════════════════════════════════════════

class State(Enum):
    # ── 校正區 ──
    IDLE        = auto()
    TABLE_CAL   = auto()   # 球桌校正（4角 Homography）
    SHAPE_CAL   = auto()   # 球型校正（半徑→scale）
    COLOR_CAL   = auto()   # 球色校正（HSV→YAML）

    # ── 打擊區 ──
    MANUAL      = auto()   # 指定打擊（POCKET → TARGET → CUE）
    BREAK       = auto()   # 開球
    AUTO        = auto()   # 自動打擊（視覺偵測→STRATEGY）
    STRATEGY    = auto()   # 策略打擊（compute_shot + striker）


class Group(Enum):
    CALIBRATION = auto()   # 校正區
    STRIKE      = auto()   # 打擊區


# ══════════════════════════════════════════════════════════════════
# 狀態群組對應
# ══════════════════════════════════════════════════════════════════

STATE_GROUPS = {
    State.IDLE:       Group.CALIBRATION,
    State.TABLE_CAL:  Group.CALIBRATION,
    State.SHAPE_CAL:  Group.CALIBRATION,
    State.COLOR_CAL:  Group.CALIBRATION,
    State.MANUAL:     Group.STRIKE,
    State.BREAK:      Group.STRIKE,
    State.AUTO:       Group.STRIKE,
    State.STRATEGY:   Group.STRIKE,
}


# ══════════════════════════════════════════════════════════════════
# StateBehavior（純資料定義）
# ══════════════════════════════════════════════════════════════════

class Behavior:
    """每個狀態的行為參數（純資料）"""

    TABLE_CAL = dict(
        name="球桌校正",
        group=Group.CALIBRATION,
        steps=4,
        step_labels=["左上", "右上", "右下", "左下"],
        requires=None,
        on_complete="save_json",
    )

    SHAPE_CAL = dict(
        name="球型校正",
        group=Group.CALIBRATION,
        steps=3,
        step_labels=None,       # 連續取樣，無固定標籤
        requires="calibration.json",
        on_complete="save_yaml",
    )

    COLOR_CAL = dict(
        name="球色校正",
        group=Group.CALIBRATION,
        steps=10,
        step_labels=None,       # 動態顯示球號
        requires="calibration.json",
        on_complete="save_yaml",
    )

    MANUAL = dict(
        name="指定打擊",
        group=Group.STRIKE,
        steps=3,
        step_labels=["口袋", "目標球", "白球"],
        requires="calibration.json + YAML",
        on_complete="compute_and_execute",
    )

    BREAK = dict(
        name="開球",
        group=Group.STRIKE,
        steps=1,
        step_labels=["白球位置"],
        requires="calibration.json",
        on_complete="break_compute_and_execute",
    )

    AUTO = dict(
        name="自動打擊",
        group=Group.STRIKE,
        steps=0,               # 全自動，無需點擊
        step_labels=None,
        requires="calibration.json + YAML",
        on_complete="transition_to_STRATEGY",
    )

    STRATEGY = dict(
        name="策略打擊",
        group=Group.STRIKE,
        steps=0,
        step_labels=None,
        requires="obstacles from AUTO",
        on_complete="compute_and_execute",
    )


# ══════════════════════════════════════════════════════════════════
# StateHandler 協定
# ══════════════════════════════════════════════════════════════════

class StateHandler:
    """
    狀態處理器介面

    所有 Handler 的共同特性：
    - 接收事件（click / drag / wsl_response / execute / cancel）
    - 管理內部狀態（收集到的資料）
    - 完成後通知 StateMachine 切換
    """

    def __init__(self, sm: "StateMachineV2"):
        self._sm = sm

    # ── 狀態生命週期 ─────────────────────────────────────────────

    def on_enter(self) -> None:
        """進入狀態時呼叫"""
        pass

    def on_exit(self) -> None:
        """離開狀態時呼叫"""
        pass

    # ── 事件處理 ─────────────────────────────────────────────────

    def handle(self, event_type: str, data: dict) -> dict:
        """
        處理事件
        回傳：{"status": "ok" | "pending" | "complete" | "waiting"}
        """
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════
# StateMachine v2
# ══════════════════════════════════════════════════════════════════

class StateMachineV2:
    """
    狀態機 v2（Windows-Only）

    設計原則：
    - 單一職責：只管狀態轉換，不管商業邏輯
    - 所有 Handler 透過 register() 注入
    - 狀態變更時自動呼叫 old_handler.on_exit() / new_handler.on_enter()
    - 外部透過 handle_event() 注入事件
    """

    def __init__(self, vision, hmi, robot_brain):
        self._mode = State.IDLE
        self._vision = vision
        self._hmi = hmi
        self._robot_brain = robot_brain    # 注入 brain（計算核心）

        # handler registry
        self._handlers: dict[State, StateHandler] = {}

        # 狀態監聽器（UI 渲染用）
        self._listeners: list[Callable[[State, State], None]] = []

    # ── 公開 API ─────────────────────────────────────────────────

    def current_state(self) -> State:
        return self._mode

    def current_group(self) -> Group:
        return STATE_GROUPS.get(self._mode, Group.CALIBRATION)

    def transition_to(self, new_state: State) -> None:
        """狀態切換（所有狀態變更的單一入口）"""
        old = self._mode
        if old == new_state:
            return

        # exit
        if old in self._handlers:
            self._handlers[old].on_exit()

        self._mode = new_state

        # enter
        if new_state in self._handlers:
            self._handlers[new_state].on_enter()

        # notify
        for cb in self._listeners:
            cb(old, new_state)

    def handle_event(self, event_type: str, data: dict) -> dict:
        """
        統一事件入口
        event_type: "click" | "drag" | "cancel" | "execute"
        data:       事件資料
        """
        handler = self._handlers.get(self._mode)
        if handler is None:
            return {"status": "no_handler"}
        return handler.handle(event_type, data)

    def on_state_change(self, callback: Callable):
        """訂閱狀態變更"""
        self._listeners.append(callback)

    def register(self, state: State, handler: StateHandler):
        """註冊 handler"""
        self._handlers[state] = handler


# ══════════════════════════════════════════════════════════════════
# Concrete Handlers
# ══════════════════════════════════════════════════════════════════

class TableCalHandler(StateHandler):
    """
    球桌校正

    流程：
      1. on_enter() → 提示「依序點擊四個角」
      2. 點擊 → add_point()
      3. 4點完成 → 存 calibration.json → 回 IDLE
    """

    def __init__(self, sm):
        super().__init__(sm)
        self._points: list[tuple[int, int]] = []

    def on_enter(self) -> None:
        self._points = []

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type != "click":
            return {"status": "ignored"}

        u, v = data["u"], data["v"]
        self._points.append((u, v))

        if len(self._points) == 4:
            # 存檔
            ok, msg = self._save_json()
            print(f"[TableCalHandler] {msg}")
            self._sm.transition_to(State.IDLE)
            return {"status": "complete"}
        else:
            return {
                "status":   "pending",
                "count":    len(self._points),
                "next":     Behavior.TABLE_CAL["step_labels"][len(self._points)],
            }

    def _save_json(self) -> tuple:
        # TODO: 呼叫 CalibrationHandler.compute() → save_json()
        import os
        path = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            ),
            "calibration.json"
        )
        # 暫時 dummy
        return True, f"已存至 {path}"


class ManualHandler(StateHandler):
    """
    指定打擊

    流程：
      1. on_enter() → 提示「口袋 → 目標球 → 白球」
      2. 依序收集 POCKET / TARGET_BALL / CUE_BALL
      3. 3步完成 → robot_brain.compute_shot() → striker.execute()
      4. 回傳 PREDICTION
    """

    SEQUENCE = ["POCKET", "TARGET_BALL", "CUE_BALL"]
    LABELS = {"POCKET": "口袋", "TARGET_BALL": "目標球", "CUE_BALL": "白球"}

    def __init__(self, sm):
        super().__init__(sm)
        self._collected: dict[str, tuple[int, int]] = {}

    def on_enter(self) -> None:
        self._collected = {}

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "execute":
            return self._do_shot()

        if event_type != "click":
            return {"status": "ignored"}

        next_type = self._next_type()
        if next_type is None:
            return {"status": "already_complete"}

        u, v = data["u"], data["v"]
        self._collected[next_type] = (u, v)

        if len(self._collected) == 3:
            return self._do_shot()

        return {
            "status":  "pending",
            "next":    self.LABELS[next_type],
        }

    def _next_type(self) -> Optional[str]:
        for t in self.SEQUENCE:
            if t not in self._collected:
                return t
        return None

    def _do_shot(self) -> dict:
        # TODO: 呼叫 robot_brain.compute_shot(
        #   pixel_to_mm → compute_shot → striker.execute → physics_validate
        # )
        return {"status": "complete", "state": "IDLE"}


class BreakHandler(StateHandler):
    """
    開球
    """

    def __init__(self, sm):
        super().__init__(sm)
        self._cue_pos: Optional[tuple[int, int]] = None

    def on_enter(self) -> None:
        self._cue_pos = None

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "execute":
            return self._do_break()

        if event_type != "click":
            return {"status": "ignored"}

        if self._cue_pos is not None:
            return {"status": "already_complete"}

        self._cue_pos = (data["u"], data["v"])
        return self._do_break()

    def _do_break(self) -> dict:
        # TODO: robot_brain.break_compute(self._cue_pos) → striker.execute()
        return {"status": "complete", "state": "IDLE"}


class AutoHandler(StateHandler):
    """
    自動打擊

    流程：
      1. on_enter() → VisionBridge.capture_and_process()
      2. 偵測到足夠球 → 自動進入 STRATEGY
    """

    def __init__(self, sm):
        super().__init__(sm)
        self._scene = None

    def on_enter(self) -> None:
        self._scene = self._sm._vision.capture_and_process()

        if self._scene and self._scene.balls:
            self._sm.transition_to(State.STRATEGY)
        else:
            # 無法取得球，留在 AUTO
            pass

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "retry":
            self.on_enter()
            return {"status": "ok"}
        return {"status": "pending"}


class StrategyHandler(StateHandler):
    """
    策略打擊

    接收 AUTO 的偵測結果，執行完整 shot

    流程：
      1. 取出 obstacles（從 AUTO handler 或已儲存的 scene）
      2. 選擇口袋（使用者選 or 自動）
      3. compute_shot(obstacles)
      4. striker.execute()
      5. physics_validate
      6. 回 IDLE
    """

    def __init__(self, sm):
        super().__init__(sm)
        self._obstacles: list = []
        self._scene = None

    def inject_scene(self, scene) -> None:
        """由 AUTO handler 或 UI 注入 scene"""
        self._scene = scene
        if scene:
            self._obstacles = [
                b for b in scene.balls
                if b.get("type") not in ("CUE_BALL", "TARGET_BALL")
            ]

    def handle(self, event_type: str, data: dict) -> dict:
        if event_type == "execute":
            return self._do_strategy()
        return {"status": "pending"}

    def _do_strategy(self) -> dict:
        # TODO:
        #  1. robot_brain.compute_shot(
        #       cue_ball, target, pocket, self._obstacles
        #     )
        #  2. striker.execute(...)
        #  3. 回傳 STRATEGY_RESULT
        return {"status": "complete", "state": "IDLE"}
