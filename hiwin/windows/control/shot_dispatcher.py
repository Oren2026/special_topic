"""
windows/control/shot_dispatcher.py
擊球資料收集與組裝

依賴：config (BALL_DIAMETER, POCKET_DIAMETER, ACCEL_DIST_LIMIT, FORCE_FACTOR)
輸出：get_packet() → dict（符合 protocol.py）
使用：StateMachine（TEST 模式）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# 期望的物件類型順序（第一個為 POCKET）
SHOT_SEQUENCE = ["POCKET", "TARGET_BALL", "CUE_BALL"]


class ShotDispatcher:
    """
    收集三個球（POCKET / TARGET_BALL / CUE_BALL）的像素座標，
    組裝成 striker_config 完整的擊球封包
    """

    def __init__(self, task_id: int = 1001):
        self.task_id = task_id
        self._balls = {}  # {"POCKET": {"u":..., "v":...}, ...}

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def add(self, ball_type: str, u, v) -> bool:
        """
        加入一顆球
        回傳：是否已收集完整（3顆）
        """
        if ball_type not in SHOT_SEQUENCE:
            return False
        self._balls[ball_type] = {"u": int(u), "v": int(v)}
        return self.is_complete()

    def get(self, ball_type: str):
        return self._balls.get(ball_type)

    def is_complete(self) -> bool:
        """三顆球都已記錄"""
        return all(bt in self._balls for bt in SHOT_SEQUENCE)

    def ball_count(self) -> int:
        return len(self._balls)

    def next_label(self) -> str:
        """下一個要點擊的球類型"""
        for bt in SHOT_SEQUENCE:
            if bt not in self._balls:
                return bt
        return "已完成"

    def get_all_data(self):
        """
        格式化為 vision_data（符合 protocol.py 定義）
        """
        result = []
        for bt in SHOT_SEQUENCE:
            if bt in self._balls:
                result.append({
                    "type": bt,
                    "u":    self._balls[bt]["u"],
                    "v":    self._balls[bt]["v"],
                })
        return result

    def get_packet(self) -> dict:
        """
        組裝完整擊球封包（符合 protocol.py）
        """
        return {
            "task_id":    self.task_id,
            "mode":       "MANUAL",
            "vision_data": self.get_all_data(),
            "striker_config": {
                "ball_diameter":    config.BALL_DIAMETER,
                "pocket_diameter":  config.POCKET_DIAMETER,
                "accel_dist_limit": config.ACCEL_DIST_LIMIT,
                "force_factor":    config.FORCE_FACTOR,
            }
        }

    def reset(self):
        self._balls = {}
