"""
windows/control/state_machine.py
狀態機

依賴：CalibrationHandler, ShotDispatcher, SocketClient
輸出：set_mode(str) / handle_click(u,v) / handle_drag(type,u,v)
      on_prediction(callback) / 狀態標籤文字
"""


class State:
    IDLE     = "IDLE"
    INSTALL  = "INSTALL"
    TEST     = "TEST"
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
        self._prediction_cb = None

    # ── 模式控制 ─────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """切換模式（INSTALL / TEST / COMPETE）"""
        self._mode = mode
        self._cal.reset()
        self._shot.reset()
        print(f"[StateMachine] 模式切換 → {mode}")

    def current_mode(self) -> str:
        return self._mode

    # ── 事件處理 ─────────────────────────────────────────────────────────────

    def handle_click(self, u, v) -> dict | None:
        """
        處理點擊事件
        回傳：info dict {"label": str, "ready": bool} 或 None
        """
        if self._mode == State.INSTALL:
            return self._handle_install(u, v)
        elif self._mode == State.TEST:
            return self._handle_test(u, v)
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
            self._mode = State.IDLE
        return {"label": label, "ready": complete, "count": self._cal.point_count()}

    def _handle_test(self, u, v) -> dict:
        # 自動從 shot sequence 取下一個類型
        next_type = self._shot.next_label()
        if next_type == "已完成":
            return {"label": "已完成", "ready": True}
        complete = self._shot.add(next_type, u, v)
        if complete:
            self._socket.send(self._shot.get_packet())
        return {"label": self._shot.next_label(), "ready": complete, "count": self._shot.ball_count()}

    # ── 預測回調 ─────────────────────────────────────────────────────────────

    def on_prediction(self, callback):
        """註冊收到 WSL PREDICTION 時的回調"""
        self._prediction_cb = callback

    def notify_prediction(self, data: dict):
        """由 SocketClient 在收到 PREDICTION 時呼叫"""
        if self._prediction_cb:
            self._prediction_cb(data)
