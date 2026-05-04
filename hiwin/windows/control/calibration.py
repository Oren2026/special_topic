"""
windows/control/calibration.py
校正點收集邏輯

依賴：無外部依賴
輸出：get_packet() → dict（符合 protocol.py）
使用：StateMachine（INSTALL 模式）
"""


class CalibrationHandler:
    """
    收集球桌四角像素座標，組裝校正封包
    """

    POINT_ORDER = [
        "左上",
        "右上",
        "右下",
        "左下",
    ]

    def __init__(self):
        self._points = []

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def add_point(self, u, v) -> bool:
        """
        加入一個校正點
        回傳：是否已收集滿 4 點（4點即完成）
        """
        if len(self._points) >= 4:
            return True
        self._points.append([int(u), int(v)])
        return len(self._points) == 4

    def is_ready(self) -> bool:
        return len(self._points) == 4

    def point_count(self) -> int:
        return len(self._points)

    def next_label(self) -> str:
        """下一個要點擊的位置提示"""
        if len(self._points) < 4:
            return self.POINT_ORDER[len(self._points)]
        return "已完成"

    def get_points(self):
        """取得目前已收集的點（副本）"""
        return list(self._points)

    def get_packet(self) -> dict:
        """
        組裝校正封包（符合 protocol.py 定義）
        """
        return {
            "calibration_points": list(self._points)
        }

    def reset(self):
        """清除所有點，重新開始"""
        self._points = []
