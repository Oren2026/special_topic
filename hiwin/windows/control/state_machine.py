"""
windows/control/state_machine.py
狀態機

依賴：CalibrationHandler, ShotDispatcher, SocketClient
輸出：set_mode(str) / handle_click(u,v) / handle_drag(type,u,v)
      on_prediction(callback) / 狀態標籤文字
"""
from typing import Optional
import os
from .calibration import CalibrationHandler
from .shot_dispatcher import ShotDispatcher
from .break_handler import BreakHandler


class State:
    IDLE     = "IDLE"
    INSTALL  = "INSTALL"
    TEST     = "TEST"
    BREAK    = "BREAK"
    COMPETE  = "COMPETE"


class StateMachine:
    """
    狀態協調器
    接收 HMI 的點擊事件，根據當前模式分派至 CalibrationHandler 或 ShotDispatcher，
    並透過 SocketClient 發送最終封包
    """

    def __init__(self, socket_client):
        self._mode = State.IDLE
        self._socket = socket_client
        self._cal = CalibrationHandler()
        self._shot = ShotDispatcher()
        self._break = BreakHandler()
        self._prediction_cb = None
        self._shot_sent = False  # True：初始擊球封包已發送（區分「剛完成」vs「已完成」）

    # ── 模式控制 ─────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """切換模式（INSTALL / TEST / BREAK / COMPETE）"""
        self._mode = mode
        self._cal.reset()
        self._shot.reset()
        self._break.reset()
        self._shot_sent = False  # 重置
        print(f"[StateMachine] 模式切換 → {mode}")

    def set_pocket(self, u: int, v: int):
        """
        預先設定口袋（由 HMI 在校正完成後呼叫，避免使用者需手動再點一次口袋）
        """
        self._shot._balls["POCKET"] = {"u": u, "v": v}

    def current_mode(self) -> str:
        return self._mode

    # ── 事件處理 ─────────────────────────────────────────────────────────────

    def handle_click(self, u, v) -> Optional[dict]:
        """
        處理點擊事件
        回傳：info dict {"label": str, "ready": bool} 或 None
        """
        if self._mode == State.INSTALL:
            return self._handle_install(u, v)
        elif self._mode == State.TEST:
            return self._handle_test(u, v)
        elif self._mode == State.BREAK:
            return self._handle_break(u, v)
        elif self._mode == State.COMPETE:
            # COMPETE 模式由自動辨識主導，此處暫不處理
            return {"label": "自動模式", "ready": False}
        else:
            return None

    def handle_drag(self, ball_type, u, v):
        """
        拖曳球體 → 即時發送更新（task_id=9999）
        """
        if self._mode != State.TEST:
            return
        self._shot._balls[ball_type] = {"u": int(u), "v": int(v)}
        packet = self._shot.get_packet()
        packet["task_id"] = 9999
        self._socket.send(packet)

    # ── 內部 ─────────────────────────────────────────────────────────────────

    def _handle_install(self, u, v) -> dict:
        complete = self._cal.add_point(u, v)
        label = self._cal.next_label()
        if complete:
            self._socket.send(self._cal.get_packet())
            # 儲存校正結果（覆寫 JSON）
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "calibration.json"
            )
            ok, msg = self._cal.save_json(json_path)
            print(f"[StateMachine] {msg}")
            self._mode = State.IDLE
        return {"label": label, "ready": complete, "count": self._cal.point_count()}

    def _handle_test(self, u, v) -> dict:
        # 自動從 shot sequence 取下一個類型
        next_type = self._shot.next_label()
        if next_type == "已完成":
            # 已完成：區分「剛完成（已發送過）」vs「已經完成（重複點擊）」
            return {"label": "已完成", "ready": True, "already_sent": self._shot_sent}
        complete = self._shot.add(next_type, u, v)
        if complete:
            self._socket.send(self._shot.get_packet())
            self._shot_sent = True  # 標記已發送
        return {"label": self._shot.next_label(), "ready": complete, "already_sent": self._shot_sent}

    def _handle_break(self, u, v) -> dict:
        """處理 BREAK 模式：只需要白球位置"""
        # 防止重複點擊（已完成後不再發送）
        if self._shot_sent:
            return {"label": "已完成", "ready": True, "already_sent": True}
        self._break.add(u, v)
        self._socket.send(self._break.get_packet())
        self._shot_sent = True
        return {"label": "已完成", "ready": True, "already_sent": False}

    # ── 預測回調 ─────────────────────────────────────────────────────────────

    def on_prediction(self, callback):
        """註冊收到 WSL PREDICTION 時的回調"""
        self._prediction_cb = callback

    def notify_prediction(self, data: dict):
        """由 SocketClient 在收到 PREDICTION 時呼叫"""
        if self._prediction_cb:
            self._prediction_cb(data)
