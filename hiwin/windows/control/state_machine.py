"""
windows/control/state_machine.py
狀態機（Windows-Only 架構）

依賴：CalibrationHandler, ShotDispatcher, BreakHandler, RobotBrain
輸出：set_mode(str) / handle_click(u,v) / handle_drag(type,u,v)
      狀態標籤文字

資源隔離原則：
- COLOR_CALIB / CIRCLE_CALIB / COLOR_VIEW / SHAPE_VIEW 模組
  只在對應模式由 StateMachine 動態 import，PLAY_TEST / COMPETE 不會載入。
- 正常運行時，只依賴：CalibrationHandler, ShotDispatcher, BreakHandler, RobotBrain
  + 純資料的 YAML dict（windows/calib/*.yaml）
"""

from typing import Optional
import os
from .calibration import CalibrationHandler
from .shot_dispatcher import ShotDispatcher
from .break_handler import BreakHandler


class State:
    IDLE         = "IDLE"
    TABLE_CALIB  = "TABLE_CALIB"   # 檯球桌位置確認（4角校正）
    CIRCLE_CALIB = "CIRCLE_CALIB"  # 球形校正（點球取樣→YAML）
    COLOR_CALIB  = "COLOR_CALIB"   # 顏色校正（點球取樣→YAML）
    COLOR_VIEW   = "COLOR_VIEW"    # 顏色調整（拖曳 UI → YAML）
    SHAPE_VIEW   = "SHAPE_VIEW"    # 球形調整（拖曳 UI → YAML）
    PLAY_TEST    = "PLAY_TEST"     # 打球測試
    BREAK_TEST   = "BREAK_TEST"    # 開球測試
    COMPETE      = "COMPETE"       # 比賽模式（自動辨識）


class StateMachine:
    """
    狀態協調器（Windows-Only）

    接收 HMI 的點擊事件，根據當前模式分派至 CalibrationHandler 或 ShotDispatcher，
    並透過 RobotBrain 執行擊球（同一程序，無 socket）。

    資源隔離：COLOR_CALIB / CIRCLE_CALIB / COLOR_VIEW / SHAPE_VIEW 模組
    只在對應 mode 才 import，PLAY_TEST / COMPETE 的 import chain 不包含這些模組。
    """

    # 校正模組（延遲載入，只在 CALIB / VIEW 模式实例化）
    _color_calib: Optional[object] = None
    _shape_calib: Optional[object] = None
    _color_view: Optional[object] = None
    _shape_view: Optional[object] = None

    def __init__(self, brain, vision=None, hmi=None):
        """
        brain: RobotBrain 實例（用於校正與擊球執行）
        vision: BilliardVision 實例（用於 COLOR_CALIB / CIRCLE_CALIB 取樣）
        hmi: HMI 實例（用於 COLOR_VIEW / SHAPE_VIEW 開啟 Toplevel 視窗）
        """
        self._mode = State.IDLE
        self._brain = brain
        self._vision = vision
        self._hmi = hmi
        self._cal = CalibrationHandler()
        self._shot = ShotDispatcher()
        self._break = BreakHandler()
        self._prediction_cb = None
        self._shot_sent = False  # True：初始擊球封包已發送（區分「剛完成」vs「已完成」）
        self._last_pockets = {}  # TABLE_CALIB 完成後的口袋結果

    def set_vision(self, vision):
        """注入 vision 實例（供 CALIB 模組取樣用）"""
        self._vision = vision

    def set_hmi(self, hmi):
        """注入 hmi 實例（供 VIEW 模組開窗用）"""
        self._hmi = hmi

    # ── 模式控制 ─────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """切換模式"""
        # 卸載舊的 CALIB / VIEW 模組（釋放記憶體）
        if mode not in (State.COLOR_CALIB, State.CIRCLE_CALIB,
                        State.COLOR_VIEW, State.SHAPE_VIEW):
            self._color_calib = None
            self._shape_calib = None
            self._color_view = None
            self._shape_view = None

        self._mode = mode
        self._cal.reset()
        self._shot.reset()
        self._break.reset()
        self._shot_sent = False
        print(f"[StateMachine] 模式切換 → {mode}")

    def set_pocket(self, u: int, v: int):
        """
        預先設定口袋（由 HMI 在校正完成後呼叫，避免使用者需手動再點一次口袋）
        """
        self._shot._balls["POCKET"] = {"u": u, "v": v}

    def current_mode(self) -> str:
        return self._mode

    def get_last_pockets(self) -> dict:
        """取得最近一次 TABLE_CALIB 完成後的口袋資料"""
        return self._last_pockets

    # ── 事件處理 ─────────────────────────────────────────────────────────────

    def handle_click(self, u, v) -> Optional[dict]:
        """
        處理點擊事件
        回傳：info dict {"label": str, "ready": bool} 或 None
        """
        if self._mode == State.TABLE_CALIB:
            return self._handle_table_calib(u, v)
        elif self._mode == State.CIRCLE_CALIB:
            return self._handle_circle_calib(u, v)
        elif self._mode == State.COLOR_CALIB:
            return self._handle_color_calib(u, v)
        elif self._mode == State.PLAY_TEST:
            return self._handle_test(u, v)
        elif self._mode == State.BREAK_TEST:
            return self._handle_break(u, v)
        elif self._mode == State.COMPETE:
            # COMPETE 模式由自動辨識主導，此處暫不處理
            return {"label": "自動模式", "ready": False}
        else:
            return None

    def handle_drag(self, ball_type, u, v):
        """
        拖曳球體 → 即時更新並重新計算路徑
        """
        if self._mode != State.PLAY_TEST:
            return
        self._shot._balls[ball_type] = {"u": int(u), "v": int(v)}
        # 重新計算（不走硬體，只更新預測顯示）
        result = self._recompute_shot()
        if result and self._prediction_cb:
            self._prediction_cb(result)

    def _recompute_shot(self) -> Optional[dict]:
        """根據當前球位置重新計算（不執行硬體）"""
        balls = self._shot._balls
        if not all(k in balls for k in ("POCKET", "TARGET_BALL", "CUE_BALL")):
            return None
        pkt  = balls["POCKET"]
        tgt  = balls["TARGET_BALL"]
        cue  = balls["CUE_BALL"]
        candidates = self._brain.compute_shot_only(
            cue_pixel=(cue["u"], cue["v"]),
            target_pixel=(tgt["u"], tgt["v"]),
            pocket_pixel=(pkt["u"], pkt["v"]),
        )
        if not candidates:
            return None
        # 取第一個候選
        return candidates[0]

    # ── 校正模式處理 ─────────────────────────────────────────────────────────

    def _lazy_color_calib(self):
        """延遲載入 COLOR_CALIB 模組"""
        if self._color_calib is None:
            from .color_calib_module import ColorCalibModule
            self._color_calib = ColorCalibModule(self._vision)
        return self._color_calib

    def _lazy_shape_calib(self):
        """延遲載入 SHAPE_CALIB 模組"""
        if self._shape_calib is None:
            from .shape_calib_module import ShapeCalibModule
            self._shape_calib = ShapeCalibModule(self._vision)
        return self._shape_calib

    def _lazy_color_view(self):
        """延遲載入 COLOR_VIEW 模組"""
        if self._color_view is None:
            from .color_view_module import ColorViewModule
            self._color_view = ColorViewModule(self._vision, self._hmi)
        return self._color_view

    def _lazy_shape_view(self):
        """延遲載入 SHAPE_VIEW 模組"""
        if self._shape_view is None:
            from .shape_view_module import ShapeViewModule
            self._shape_view = ShapeViewModule(self._vision, self._hmi)
        return self._shape_view

    # ── 內部 ─────────────────────────────────────────────────────────────────

    def _handle_table_calib(self, u, v) -> dict:
        complete = self._cal.add_point(u, v)
        label = self._cal.next_label()
        if complete:
            points = self._cal.get_points()
            # 呼叫 RobotBrain 校正（計算 Homography + 口袋 pixel 座標）
            calib_result = self._brain.calibrate(points)
            self._last_pockets = calib_result.get("pockets", {})
            # 儲存校正結果（覆寫 JSON）
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "calibration.json"
            )
            ok, msg = self._cal.save_json(json_path)
            print(f"[StateMachine] {msg}")
            self._mode = State.IDLE
        return {"label": label, "ready": complete, "count": self._cal.point_count()}

    def _handle_circle_calib(self, u, v) -> dict:
        """球形校正（CIRCLE_CALIB）：點球取樣，計算 scale，寫入 YAML"""
        mod = self._lazy_shape_calib()
        result = mod.handle_click(u, v)
        if result.get("complete"):
            return {"label": "球形校正完成", "ready": True, "message": result.get("message")}
        if result.get("error"):
            return {"label": f"取樣失敗: {result['error']}", "ready": False,
                    "count": result.get("count", 0)}
        return {
            "label": f"半徑: {result.get('radius_pixel', 0):.1f}px  "
                     f"平均: {result.get('avg_radius', 0):.1f}px  "
                     f"scale={result.get('scale_mm_per_pixel', 0):.4f}mm/px",
            "ready": False,
            "count": result.get("count", 0),
        }

    def _handle_color_calib(self, u, v) -> dict:
        """顏色校正（COLOR_CALIB）：點球取樣 HSV，彈出數字鍵盤"""
        mod = self._lazy_color_calib()
        result = mod.handle_click(u, v)
        if result.get("pending"):
            # 回傳時攜帶 hsv 資訊，HMI 據此彈出數字鍵盤
            return {
                "label": f"請選擇球號  HSV=({result['h']},{result['s']},{result['v']})",
                "pending": True,
                "h": result["h"], "s": result["s"], "v": result["v"],
                "u": result["u"], "v": result["v"],
                "already_sampled": result.get("already_sampled", []),
            }
        if result.get("error"):
            return {"label": f"錯誤: {result['error']}", "ready": False}
        if result.get("complete"):
            return {"label": f"顏色校正完成（{result.get('samples_count', 0)}球）",
                    "ready": True, "message": result.get("message")}
        return {
            "label": f"已記錄 #{result.get('number')}（{result.get('samples_count', 0)}球）",
            "ready": False,
        }

    def _handle_test(self, u, v) -> dict:
        """打球測試（PLAY_TEST）：三球齊後呼叫 brain 計算並執行"""
        # 自動從 shot sequence 取下一個類型
        next_type = self._shot.next_label()
        if next_type == "已完成":
            # 已完成：區分「剛完成（已發送過）」vs「已經完成（重複點擊）」
            return {"label": "已完成", "ready": True, "already_sent": self._shot_sent}
        complete = self._shot.add(next_type, u, v)
        if not complete:
            return {"label": self._shot.next_label(), "ready": False, "already_sent": self._shot_sent}

        # 三球齊了，呼叫 brain 計算並執行
        balls = self._shot._balls
        pkt  = balls["POCKET"]
        tgt  = balls["TARGET_BALL"]
        cue  = balls["CUE_BALL"]

        result = self._brain.compute_and_execute_shot(
            cue_pixel=(cue["u"], cue["v"]),
            target_pixel=(tgt["u"], tgt["v"]),
            pocket_pixel=(pkt["u"], pkt["v"]),
        )

        self._shot_sent = True
        self._prediction_cb(result)  # 通知 HMI 繪製預測線
        return {"label": "已完成", "ready": True, "already_sent": False, **result}

    def _handle_break(self, u, v) -> dict:
        """處理 BREAK 模式：只需要白球位置"""
        # 防止重複點擊（已完成後不再發送）
        if self._shot_sent:
            return {"label": "已完成", "ready": True, "already_sent": True}
        self._break.add(u, v)
        result = self._brain.compute_and_execute_break(cue_pixel=(u, v))
        self._shot_sent = True
        self._prediction_cb(result)  # 通知 HMI 繪製預測線
        return {"label": "已完成", "ready": True, "already_sent": False, **result}

    # ── 顏色校正確認（數字鍵盤回調）────────────────────────────────────────────

    def confirm_color_number(self, number: int) -> dict:
        """
        由 HMI 數字鍵盤確認後呼叫（COLOR_CALIB 模式）
        number: 球號（0=白球, 1-9=有色球）
        """
        if self._mode != State.COLOR_CALIB:
            return {"error": "不在顏色校正模式"}
        mod = self._lazy_color_calib()
        result = mod.confirm_number(number)
        if result.get("complete"):
            return {"label": f"顏色校正完成（{len(result.get('samples', {}))}球）",
                    "ready": True, "message": result.get("message")}
        return {
            "label": f"已記錄 #{number}（{result.get('samples_count', 0)}球）"
                      f"  剩餘: {result.get('remaining', [])}",
            "ready": False,
        }

    # ── VIEW 模組存取（供 HMI 呼叫）───────────────────────────────────────────

    def get_color_view_module(self):
        """取得 COLOR_VIEW 模組（延遲創建）"""
        return self._lazy_color_view()

    def get_shape_view_module(self):
        """取得 SHAPE_VIEW 模組（延遲創建）"""
        return self._lazy_shape_view()

    # ── 預測回調 ─────────────────────────────────────────────────────────────

    def on_prediction(self, callback):
        """註冊收到計算結果時的回調（用於更新預測線顯示）"""
        self._prediction_cb = callback

    def notify_prediction(self, data: dict):
        """內部呼叫：通知 prediction 回調"""
        if self._prediction_cb:
            self._prediction_cb(data)