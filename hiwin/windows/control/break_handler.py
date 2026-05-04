"""
windows/control/break_handler.py
開球資料收集

開球模式只需要知道白球位置，其他都由 break_module 計算。

依賴：無外部依賴
輸出：get_packet() → dict
使用：StateMachine（BREAK 模式）
"""


class BreakHandler:
    """
    收集白球像素座標，組裝開球封包
    """

    def __init__(self, task_id: int = 2001):
        self.task_id = task_id
        self._cue = None   # {"u": int, "v": int}

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def add(self, u, v) -> bool:
        """
        設定白球位置
        回傳：是否完成（開球只需要白球，永遠 True）
        """
        self._cue = {"u": int(u), "v": int(v)}
        return True

    def is_complete(self) -> bool:
        """開球只需要白球，永遠已完成"""
        return self._cue is not None

    def next_label(self) -> str:
        if self._cue is None:
            return "白球位置"
        return "已完成"

    def get_packet(self) -> dict:
        return {
            "task_id": self.task_id,
            "mode":    "BREAK",
            "vision_data": [
                {"type": "CUE_BALL", "u": self._cue["u"], "v": self._cue["v"]},
            ],
        }

    def reset(self):
        self._cue = None
