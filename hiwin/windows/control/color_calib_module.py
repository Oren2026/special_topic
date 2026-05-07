"""
windows/control/color_calib_module.py
顏色校正模組（COLOR_CALIB 模式）

職責：
1. 點球取樣 HSV 值
2. 顯示數字鍵盤讓使用者選擇球號
3. 累積所有樣本後寫入 windows/calib/color_ranges.yaml

資源隔離：
- 只在 COLOR_CALIB 模式由 StateMachine 動態 import
- 不在 PLAY_TEST / COMPETE 的 import chain 中
"""

import cv2
import numpy as np
import yaml
import os
import datetime
from typing import Optional

# 取樣 ROI 半徑（pixel）
_SAMPLE_RADIUS = 5   # 11x11 正方形區域取中位數


class ColorCalibModule:
    """
    顏色校正控制邏輯

    流程：
    1. 使用者點擊畫面中的球
    2. 系統自動在點擊位置取樣 HSV（中位數）
    3. 彈出數字鍵盤，使用者選擇「這是 N 號球」
    4. 記錄該球號的 HSV 範圍
    5. 重複直到所有球都取樣完（或使用者提前結束）
    6. 寫入 windows/calib/color_ranges.yaml
    """

    def __init__(self, vision):
        """
        vision: BilliardVision 實例（用於取 frame）
        """
        self._vision = vision
        # 已取樣的球：{number: {h, s, v, radius, confidence, u, v}}
        self._samples: dict[int, dict] = {}
        # 等待數字鍵盤確認的暫存點
        self._pending_click: Optional[tuple[int, int, int, int]] = None  # (u, v, h, s, v)

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def handle_click(self, u: int, v: int) -> dict:
        """
        處理點擊：
        1. 取樣點擊位置的 HSV（中位數）
        2. 回傳 {pending: True, number: N} 觸發數字鍵盤
        3. 之後由 confirm_number() 確認球號
        """
        # 取 ROI HSV 中位數
        h_mean, s_mean, v_mean, radius = self._sample_hsv(u, v)
        if h_mean == 0 and s_mean == 0 and v_mean == 0:
            # 取樣失敗（超出範圍或無效區域）
            return {"pending": False, "error": "取樣失敗，請在球上點擊"}

        self._pending_click = (u, v, h_mean, s_mean, v_mean)
        return {
            "pending": True,
            "u": u, "v": v,
            "h": h_mean, "s": s_mean, "v": v_mean,
            "already_sampled": list(self._samples.keys()),
        }

    def confirm_number(self, number: int) -> dict:
        """
        數字鍵盤確認後呼叫：
        - number: 球號（0=白球, 1-9=有色球）
        - 寫入樣本，檢查是否完成
        """
        if self._pending_click is None:
            return {"error": "無待確認的取樣"}

        u, v, h, s, v_val = self._pending_click
        self._pending_click = None

        if number in self._samples:
            # 覆寫舊樣本
            pass

        self._samples[number] = {
            "h": h, "s": s, "v": v_val,
            "u": u, "v": v,
            "radius": 19,  # 預設，待 CIRCLE_CALIB 更新
        }

        done = len(self._samples) >= 10  # 0-9 全部取完
        if done:
            ok, msg = self._write_yaml()
            return {"complete": True, "saved": ok, "message": msg, "samples": self._samples}

        return {
            "complete": False,
            "number": number,
            "samples_count": len(self._samples),
            "remaining": [n for n in range(10) if n not in self._samples],
        }

    def get_samples(self) -> dict[int, dict]:
        return dict(self._samples)

    def reset(self):
        self._samples.clear()
        self._pending_click = None

    # ── 內部 ─────────────────────────────────────────────────────────────────

    def _sample_hsv(self, u: int, v: int):
        """
        在 (u, v) 周圍取 ROI，計算 HSV 中位數
        回傳：(h, s, v, radius_estimate)
        """
        (ret_t, frame_t), _ = self._vision.get_raw_frames()
        if not ret_t:
            return 0, 0, 0, 0

        hsv = cv2.cvtColor(frame_t, cv2.COLOR_BGR2HSV)
        h, w = hsv.shape[:2]

        x1 = max(0, u - _SAMPLE_RADIUS)
        x2 = min(w, u + _SAMPLE_RADIUS)
        y1 = max(0, v - _SAMPLE_RADIUS)
        y2 = min(h, v + _SAMPLE_RADIUS)

        roi = hsv[y1:y2, x1:x2]
        if roi.size == 0:
            return 0, 0, 0, 0

        h_med = int(np.median(roi[:, :, 0]))
        s_med = int(np.median(roi[:, :, 1]))
        v_med = int(np.median(roi[:, :, 2]))

        # 半徑估算：ROI 範圍內的亮度變化邊界
        radius = min(x2 - x1, y2 - y1) // 2

        return h_med, s_med, v_med, radius

    def _write_yaml(self) -> tuple[bool, str]:
        """
        將取樣結果寫入 windows/calib/color_ranges.yaml
        回傳：(ok, message)
        """
        try:
            path = self._yaml_path()
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}

            data["updated_at"] = datetime.datetime.now().isoformat()

            # 更新每個球的 HSV 範圍（以取樣為中心，±10 的範圍）
            BAND = 10
            for number, sample in self._samples.items():
                key = f"ball_{number}" if number > 0 else "cue_ball"
                if number == 0:
                    data["balls"]["cue_ball"] = {
                        "number": 0,
                        "name": "cue_ball",
                        "hue_low": 0,
                        "hue_high": 180,
                        "sat_low": 0,
                        "sat_high": 30,
                        "val_low": 180,
                        "val_high": 255,
                    }
                elif number == 8:
                    # 黑球：用亮度判斷
                    data["balls"][key] = {
                        "number": number,
                        "name": NUMBER_TO_NAME[number],
                        "hue_low": 0,
                        "hue_high": 180,
                        "sat_low": 0,
                        "sat_high": 255,
                        "val_low": 0,
                        "val_high": sample["v"],
                    }
                elif number == 9:
                    # 條紋球：記錄 base hue + stripe threshold
                    data["balls"][key] = {
                        "number": number,
                        "name": "stripe_yellow",
                        "base_hue_low": max(0, sample["h"] - BAND),
                        "base_hue_high": min(180, sample["h"] + BAND),
                        "stripe_threshold": 30,
                        "sat_low": max(0, sample["s"] - BAND),
                        "sat_high": min(255, sample["s"] + BAND),
                        "val_low": max(0, sample["v"] - BAND),
                        "val_high": min(255, sample["v"] + BAND),
                    }
                else:
                    # 有色球：記錄 Hue ± BAND（處理跨 0 邊界）
                    if sample["h"] <= BAND:
                        # 接近 Hue=0 邊界，可能是紅球/栗色球
                        data["balls"][key] = {
                            "number": number,
                            "name": NUMBER_TO_NAME[number],
                            "hue_low": 0,
                            "hue_high": sample["h"] + BAND,
                            "hue_low_2": 180 - (BAND - sample["h"]) if sample["h"] < BAND else None,
                            "hue_high_2": 180,
                            "sat_low": max(0, sample["s"] - BAND),
                            "sat_high": min(255, sample["s"] + BAND),
                            "val_low": max(0, sample["v"] - BAND),
                            "val_high": min(255, sample["v"] + BAND),
                        }
                    else:
                        data["balls"][key] = {
                            "number": number,
                            "name": NUMBER_TO_NAME[number],
                            "hue_low": max(0, sample["h"] - BAND),
                            "hue_high": min(180, sample["h"] + BAND),
                            "sat_low": max(0, sample["s"] - BAND),
                            "sat_high": min(255, sample["s"] + BAND),
                            "val_low": max(0, sample["v"] - BAND),
                            "val_high": min(255, sample["v"] + BAND),
                        }

            with open(path, "w") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

            return True, f"已寫入 {path}"
        except Exception as e:
            return False, f"寫入失敗: {e}"

    def _yaml_path(self) -> str:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "calib", "color_ranges.yaml")


# 球號 → 顏色名稱（用於 YAML 寫入）
NUMBER_TO_NAME = {
    1: "yellow",
    2: "blue",
    3: "red",
    4: "purple",
    5: "orange",
    6: "green",
    7: "maroon",
    8: "black",
    9: "stripe_yellow",
}
