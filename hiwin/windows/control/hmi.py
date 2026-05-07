"""
windows/control/hmi.py
Tkinter 人機介面

依賴：tkinter, cv2, PIL, StateMachine, SocketClient, BilliardVision, SimulationScene
輸出：Tkinter 視窗
"""
import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from .state_machine import StateMachine, State
from .socket_client import SocketClient
from .sim_table import SimTable, DEFAULT_TABLE
import vision
from vision import BilliardVision, SimulationScene


class HMI:
    """
    Tkinter 主視窗
    職責：事件 → StateMachine → Socket → 回應繪圖
    """

    def __init__(self):
        self._prediction_data = None
        self._selected_ball = None

        # ── 底層元件 ──────────────────────────────────────────────────────
        self._socket = SocketClient()
        self._socket.connect()
        self._socket.on_message(self._on_wsl_message)

        self._state = StateMachine(self._socket, vision=self._vision, hmi=self)
        self._state.on_prediction(self._on_prediction)

        # ── Tkinter 視窗 ─────────────────────────────────────────────────
        self._root = tk.Tk()
        self._root.title("HIWIN RA605 9-Ball Robot Control System")

        self._scene = SimulationScene()
        self._vision = BilliardVision()

        # ── 建立 UI ───────────────────────────────────────────────────────
        self._setup_ui()
        self._setup_events()

        # ── 啟動視覺更新迴圈 ──────────────────────────────────────────────
        self._update_frame()

    # ── 公開 API ───────────────────────────────────────────────────────────

    def run(self):
        self._root.mainloop()

    # ── UI 布局 ─────────────────────────────────────────────────────────────

    def _setup_ui(self):
        # 左：控制面板
        self._ctrl = tk.Frame(self._root, padx=10, pady=10, relief=tk.RIDGE, bd=2)
        self._ctrl.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(self._ctrl, text="控制面板", font=('Arial', 16, 'bold')).pack(pady=(10, 5))

        # ── 設定區 ────────────────────────────────────────────────────────
        tk.Label(self._ctrl, text="【設定區】", font=('Arial', 11, 'bold')).pack()

        tk.Button(self._ctrl, text="檯球桌位置確認", width=18, bg="#f0f0f0",
                 command=lambda: self._on_mode_set(State.TABLE_CALIB)).pack(pady=2)
        tk.Button(self._ctrl, text="球形校正", width=18, bg="#e8f5e9",
                 command=lambda: self._on_mode_set(State.CIRCLE_CALIB)).pack(pady=2)
        tk.Button(self._ctrl, text="顏色校正", width=18, bg="#e3f2fd",
                 command=lambda: self._on_mode_set(State.COLOR_CALIB)).pack(pady=2)

        # ── 參數微調區（獨立按鈕）──────────────────────────────────────────────
        tk.Label(self._ctrl, text="【參數微調】", font=('Arial', 11, 'bold')).pack(pady=(10, 0))

        tk.Button(self._ctrl, text="球形調整", width=18, bg="#e8f5e9",
                 command=lambda: self._on_mode_set(State.SHAPE_VIEW)).pack(pady=2)
        tk.Button(self._ctrl, text="顏色調整", width=18, bg="#e3f2fd",
                 command=lambda: self._on_mode_set(State.COLOR_VIEW)).pack(pady=2)

        # ── 測試區 ────────────────────────────────────────────────────────
        tk.Label(self._ctrl, text="【測試區】", font=('Arial', 11, 'bold')).pack(pady=(10, 0))

        tk.Button(self._ctrl, text="打球測試", width=18, bg="#fff3e0",
                 command=lambda: self._on_mode_set(State.PLAY_TEST)).pack(pady=2)
        tk.Button(self._ctrl, text="開球測試", width=18, bg="#fce4ec",
                 command=lambda: self._on_mode_set(State.BREAK_TEST)).pack(pady=2)
        tk.Button(self._ctrl, text="比賽模式", width=18, bg="#ffcdd2",
                 command=lambda: self._on_mode_set(State.COMPETE)).pack(pady=2)

        self._status_lbl = tk.Label(self._ctrl, text="目前狀態: 待機中", fg="blue")
        self._status_lbl.pack(pady=15)

        self._info_lbl = tk.Label(self._ctrl, text="請依序執行設定區項目", justify=tk.LEFT)
        self._info_lbl.pack(side=tk.BOTTOM, pady=5)

        # ── 主畫面區域 ────────────────────────────────────────────────────
        self._canvas_top = tk.Canvas(self._root, width=config.TOP_CANVAS_W,
                                     height=config.TOP_CANVAS_H, bg="black")
        self._canvas_top.pack(side=tk.LEFT, padx=5)

        self._canvas_side = tk.Canvas(self._root, width=config.SIDE_CANVAS_W,
                                      height=config.SIDE_CANVAS_H, bg="black")
        self._canvas_side.pack(side=tk.TOP, padx=10, pady=(20, 0))

    def _setup_events(self):
        # 點擊 → 狀態機處理
        self._canvas_top.bind("<Button-1>", self._on_click)
        # 拖曳 → 即時更新
        self._canvas_top.bind("<B1-Motion>", self._on_drag)
        self._canvas_top.bind("<ButtonRelease-1>", self._on_release)

    # ── 模式切換 ─────────────────────────────────────────────────────────────

    def _on_mode_set(self, mode: str):
        # ── Guard 檢查 ─────────────────────────────────────────────────────
        if mode in (State.CIRCLE_CALIB, State.COLOR_CALIB,
                    State.COLOR_VIEW, State.SHAPE_VIEW):
            if not self._has_calibration_json():
                messagebox.showwarning("尚無校正檔",
                    "請先執行「檯球桌位置確認」")
                return

        if mode == State.PLAY_TEST:
            missing = self._get_missing_configs()
            if missing:
                messagebox.showwarning("設定檔不完整",
                    f"缺少：{', '.join(missing)}\n請先完成設定區項目")
                return

        self._state.set_mode(mode)

        # 非 CALIB 模式重建 Scene，CALIB 模式保留（用於輔助線繪製）
        if mode not in (State.TABLE_CALIB, State.CIRCLE_CALIB,
                         State.COLOR_CALIB, State.COLOR_VIEW, State.SHAPE_VIEW):
            self._scene = SimulationScene()

        self._prediction_data = None

        # 模式初始化
        if mode == State.TABLE_CALIB:
            pass  # 直接進流程，4角收集完成後自動儲存
        elif mode == State.COLOR_CALIB:
            self._state._vision = self._vision  # 注入 vision（延遲 import 後需要）
        elif mode == State.CIRCLE_CALIB:
            self._state._vision = self._vision
        elif mode == State.COLOR_VIEW:
            # 開啟 COLOR_VIEW Toplevel 視窗（阻斷式）
            view = self._state.get_color_view_module()
            view.start_view()
            self._state.set_mode(State.IDLE)  # VIEW 開窗後回到 IDLE
            return
        elif mode == State.SHAPE_VIEW:
            # 開啟 SHAPE_VIEW Toplevel 視窗（阻斷式）
            view = self._state.get_shape_view_module()
            view.start_view()
            self._state.set_mode(State.IDLE)
            return
        elif mode == State.PLAY_TEST:
            self._load_calibration_for_test()

        labels = {
            State.TABLE_CALIB:  "檯球桌位置確認",
            State.CIRCLE_CALIB: "球形校正",
            State.COLOR_CALIB:  "顏色校正",
            State.COLOR_VIEW:   "顏色調整",
            State.SHAPE_VIEW:   "球形調整",
            State.PLAY_TEST:    "打球測試",
            State.BREAK_TEST:   "開球測試",
            State.COMPETE:      "比賽模式",
        }
        self._status_lbl.config(text=f"狀態: {labels.get(mode, mode)}")
        self._info_lbl.config(text=self._get_mode_hint(mode))

        if mode == State.TABLE_CALIB:
            messagebox.showinfo("檯球桌位置確認",
                "請在頂視畫面依序點擊球桌四個角：\n1. 左上 2. 右上 3. 右下 4. 左下")
        elif mode == State.CIRCLE_CALIB:
            messagebox.showinfo("球形校正",
                "請點擊檯面上任意一顆球（建議白球）\n"
                "系統會量測半徑並計算 pixel↔mm 比例\n"
                "至少取 3 個不同球後自動完成")
        elif mode == State.COLOR_CALIB:
            messagebox.showinfo("顏色校正",
                "請依序點擊檯面上的球：\n"
                "點球後，選擇該球的號碼（1-9）\n"
                "系統會取樣 HSV 範圍\n"
                "完成後自動寫入 YAML")

    def _get_mode_hint(self, mode) -> str:
        hints = {
            State.TABLE_CALIB:  "請依序點擊：左上 → 右上 → 右下 → 左下",
            State.CIRCLE_CALIB: "點擊球取樣（至少3球），自動計算比例尺",
            State.COLOR_CALIB:  "點擊球後選擇球號（0-9），完成後自動寫入YAML",
            State.COLOR_VIEW:   "拖曳滑桿微調，關閉視窗自動儲存",
            State.SHAPE_VIEW:   "拖曳滑桿微調，關閉視窗自動儲存",
            State.PLAY_TEST:    "請先完成設定區項目",
            State.BREAK_TEST:   "點擊白球位置（將以最大力朝球堆方向擊出）",
            State.COMPETE:      "自動辨識模式（待實作）",
        }
        return hints.get(mode, "")

    # ── TEST 模式初始化（讀取 JSON → 設定檯面 + 口袋）───────────────────────

    def _calibration_json_path(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "calibration.json"
        )

    def _has_calibration_json(self) -> bool:
        return os.path.exists(self._calibration_json_path())

    def _get_missing_configs(self) -> list:
        """檢查 PLAY_TEST 所需的設定檔，回傳缺少的項目"""
        missing = []
        if not self._has_calibration_json():
            missing.append("calibration.json")
        return missing

    def _load_calibration_for_test(self):
        """
        切入 TEST 模式時：
        1. 嘗試讀取 calibration.json
        2. 若有紀錄 → 注入 4 角校正點 + 計算口袋 pixel 位置
        3. 若無檔案 → 提示使用者先執行檯球桌位置確認
        """
        json_path = self._calibration_json_path()
        if not os.path.exists(json_path):
            self._info_lbl.config(
                text="無 calibration.json，請先執行「檯球桌位置確認」"
            )
            return

        ok, msg = self._state._cal.load_json(json_path)
        if not ok:
            self._info_lbl.config(text=f"校正檔載入失敗：{msg}")
            return

        # 注入 4 角校正點 → 繪製 felt + rails 邊框
        calib_pts = self._state._cal.get_points()
        self._scene.set_calibration_points(calib_pts)

        # 用 SimTable 的口袋 mm 座標，透過 Homography 轉換為 pixel
        table = DEFAULT_TABLE
        pockets_for_scene = {}
        for pocket in table.get_all_pockets():
            u, v = self._state._cal.mm_to_pixel(pocket.x_mm, pocket.y_mm)
            if u == float('inf') or v == float('inf'):
                continue
            pockets_for_scene[pocket.name] = [u, v]

        self._scene.set_pockets(pockets_for_scene)

        self._info_lbl.config(
            text=f"已讀取校正（{len(calib_pts)}點），口袋{len(pockets_for_scene)}個\n"
                 "請點擊：目標球 → 白球（口袋可直接點選更換）"
        )
        print(f"[HMI] 已載入校正 + 口袋：{pockets_for_scene}")

    # ── 點擊 / 拖曳 ──────────────────────────────────────────────────────────

    def _on_click(self, event):
        u, v = event.x, event.y

        # 球體碰撞檢測（僅 PLAY_TEST 模式）
        if self._state.current_mode() == State.PLAY_TEST:
            hit = self._hit_test(u, v)
            if hit:
                self._selected_ball = hit
                return

        # PLAY_TEST 模式：點擊口袋圓圈 → 自動選定該口袋
        if self._state.current_mode() == State.PLAY_TEST:
            pkt_hit = self._hit_pocket(u, v)
            if pkt_hit:
                # 寫入 scene.balls（用於預測線繪圖）同時保持 scene._pockets（用於顯示）
                self._scene.add_or_update("POCKET", pkt_hit["u"], pkt_hit["v"])
                result = self._state.handle_click(pkt_hit["u"], pkt_hit["v"])
                if result:
                    if result.get("ready"):
                        self._info_lbl.config(
                            text="擊球任務已發送！\n可直接拖曳調整路徑。"
                            if not result.get("already_sent") else
                            "已完成。可拖曳球調整路線，或點空白處重新布置。"
                        )
                    else:
                        self._info_lbl.config(text=f"已記錄: {result.get('label')}")
                return

        # 否則交給狀態機處理
        ball_type = None
        if self._state.current_mode() == State.PLAY_TEST:
            ball_type = self._state._shot.next_label()
        elif self._state.current_mode() == State.BREAK_TEST:
            ball_type = "CUE_BALL"

        result = self._state.handle_click(u, v)
        if result:
            # 防止 "已完成" 被當成 ball_type 加入 scene（bug fix）
            if ball_type and ball_type != "已完成" and ball_type not in self._scene.balls:
                self._scene.add_or_update(ball_type, u, v)

            # ── COLOR_CALIB：顯示數字鍵盤 ───────────────────────────────────
            if result.get("pending"):
                self._show_number_keypad(
                    h=result.get("h"), s=result.get("s"), v=result.get("v"),
                    u=result.get("u"), v_pos=result.get("v"),
                    already_sampled=result.get("already_sampled", [])
                )
                self._info_lbl.config(text=result.get("label", ""))
                return

            # PLAY_TEST 模式：檢查是否點在球桌範圍外（空白處）
            if self._state.current_mode() == State.PLAY_TEST and result.get("ready"):
                is_off_table = not self._is_on_table(u, v)
                if is_off_table and result.get("already_sent"):
                    # 球桌外 + 已完成 → 重置 scene，重新布置
                    self._reset_test_scene()
                    self._info_lbl.config(text="已清除，請重新布置：目標球 → 白球")
                    return

            if result.get("ready"):
                self._info_lbl.config(
                    text="擊球任務已發送！\n可直接拖曳調整路徑。"
                    if not result.get("already_sent") else
                    "已完成。可拖曳球調整路線，或點空白處重新布置。"
                )
            else:
                self._info_lbl.config(text=f"已記錄: {result.get('label')}")

    def _on_drag(self, event):
        if self._state.current_mode() != State.PLAY_TEST:
            return
        if self._selected_ball:
            u, v = event.x, event.y
            self._scene.add_or_update(self._selected_ball, u, v)
            self._state.handle_drag(self._selected_ball, u, v)

    def _on_release(self, event):
        self._selected_ball = None

    def _hit_test(self, u, v) -> Optional[str]:
        """回傳被點中的球類型，或 None"""
        for ball_type, ball in self._scene.balls.items():
            if ((ball.u - u)**2 + (ball.v - v)**2) ** 0.5 < 20:
                return ball_type
        return None

    def _hit_pocket(self, u, v):
        """回傳被點中的口袋dict，或 None"""
        for pkt in self._scene._pockets:
            if ((pkt["u"] - u)**2 + (pkt["v"] - v)**2) ** 0.5 < 20:
                return pkt
        return None

    def _is_on_table(self, u, v) -> bool:
        """
        判斷點 (u, v) 是否在球桌範圍內（使用校正4點構成的矩形）。
        使用 cv2.pointPolygonTest：>0 表示在內部。
        若尚未校正（無4點），回傳 True（不主動阻擋）。
        """
        points = self._state._cal.get_points()
        if len(points) < 4:
            return True  # 未校正，不阻擋
        pts = [tuple(map(int, p)) for p in points]
        # cv2.pointPolygonTest 回傳：>0 在內部，=0 在邊界，<0 在外部
        return cv2.pointPolygonTest(np.array(pts, dtype=np.int32), (float(u), float(v))) >= 0

    # ── 數字鍵盤（COLOR_CALIB 用）────────────────────────────────────────────

    def _show_number_keypad(self, h, s, v, u, v_pos, already_sampled: list):
        """
        彈出 Toplevel 數字鍵盤，選擇球號（0=白球, 1-9=有色球）
        選擇後呼叫 confirm_color_number
        """
        win = tk.Toplevel(self._root)
        win.title("選擇球號")
        win.geometry("320x420")
        win.resizable(False, False)
        win.transient(self._root)
        win.grab_set()

        # HSV 資訊標題
        tk.Label(win, text=f"HSV=({h},{s},{v})",
                 font=("Arial", 12, "bold"), fg="#333").pack(pady=(15, 5))
        tk.Label(win, text="這是幾號球？", font=("Arial", 13)).pack(pady=(0, 15))

        # 已取樣的球（顯示為灰色）
        sampled_set = set(already_sampled)

        def on_number(num: int):
            win.destroy()
            result = self._state.confirm_color_number(num)
            if result.get("ready"):
                self._info_lbl.config(text=result.get("label", ""))
                messagebox.showinfo("完成", result.get("label", ""))
            elif result.get("error"):
                self._info_lbl.config(text=f"錯誤: {result['error']}")
            else:
                self._info_lbl.config(text=result.get("label", ""))

        # 數字按鈕 0-9（3x3 + 0）
        btn_frame = tk.Frame(win)
        btn_frame.pack()

        _BALL_COLORS = {
            0: "#cccccc", 1: "#e6cc00", 2: "#0066cc", 3: "#cc0000",
            4: "#660099", 5: "#ff6600", 6: "#009933", 7: "#800000",
            8: "#333333", 9: "#e6cc00",
        }
        _BALL_NAMES = {
            0: "白球", 1: "1號黃", 2: "2號藍", 3: "3號紅",
            4: "4號紫", 5: "5號橙", 6: "6號綠", 7: "7號褐",
            8: "8號黑", 9: "9號條紋",
        }

        for i in range(1, 10):
            row = (i - 1) // 3
            col = (i - 1) % 3
            already = i in sampled_set
            bg = "#aaaaaa" if already else _BALL_COLORS[i]
            fg = "white"
            label = f"{i}號" if not already else f"{i}號✓"
            b = tk.Button(btn_frame, text=label, width=8, height=2,
                          bg=bg, fg=fg,
                          state=tk.DISABLED if already else tk.NORMAL,
                          command=lambda n=i: on_number(n))
            b.grid(row=row, column=col, padx=4, pady=4)

        # 0號按鈕（白球）置中
        row0 = tk.Frame(btn_frame)
        row0.grid(row=3, column=0, columnspan=3, pady=(4, 0))
        already_0 = 0 in sampled_set
        bg0 = "#aaaaaa" if already_0 else _BALL_COLORS[0]
        b0 = tk.Button(row0, text="白球(0)", width=22, height=2,
                       bg=bg0, fg="black",
                       state=tk.DISABLED if already_0 else tk.NORMAL,
                       command=lambda: on_number(0))
        b0.pack()

        # 取消
        tk.Button(win, text="取消", width=20, bg="#ffdddd",
                  command=win.destroy).pack(pady=(10, 5))

        # 提示
        tk.Label(win, text="✓ 表示已完成取樣",
                 fg="gray", font=("Arial", 9)).pack()

    def _reset_test_scene(self):
        """
        重置 TEST 模式場景（清除球，保留口袋），以便重新布置。
        """
        pockets = {p["name"]: [p["u"], p["v"]] for p in self._scene._pockets}
        self._scene = SimulationScene()
        self._scene.set_pockets(pockets)
        self._state._shot.reset()
        self._state._shot_sent = False
        self._prediction_data = None
        # 預設第一個口袋
        if pockets:
            first_name, first_uv = next(iter(pockets.items()))
            pu, pv = int(first_uv[0]), int(first_uv[1])
            self._scene.add_or_update("POCKET", pu, pv)
            self._state.set_pocket(pu, pv)

    # ── Socket 回應 ──────────────────────────────────────────────────────────

    def _on_wsl_message(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "PREDICTION":
            self._prediction_data = data
        elif msg_type == "BREAK_RESULT":
            self._prediction_data = data
        elif msg_type == "CALIBRATION_COMPLETE":
            pockets = data.get("pockets", {})
            self._on_mode_set(State.PLAY_TEST)
            self._scene.set_pockets(pockets)
            # 預設使用第一個口袋，讓 TEST 流程只需 TARGET + CUE（2步）
            first_pocket = next(iter(pockets.values()), None)
            if first_pocket:
                pu, pv = int(first_pocket[0]), int(first_pocket[1])
                self._scene.add_or_update("POCKET", pu, pv)
                self._state.set_pocket(pu, pv)
            self._info_lbl.config(text=f"口袋已設定（{len(pockets)}個）\n請點擊：目標球 → 白球")
            self._root.after(100, lambda: messagebox.showinfo(
                "校正完成",
                f"已辨識 {len(pockets)} 個口袋。\n"
                "請依序點擊：①目標球 ②白球\n（口袋可直接點擊重新選擇）"))

    def _on_prediction(self, data: dict):
        self._prediction_data = data

    # ── 視覺更新迴圈 ─────────────────────────────────────────────────────────

    def _update_frame(self):
        self._render_top()
        self._render_side()
        self._root.after(config.UI_UPDATE_MS, self._update_frame)

    def _render_top(self):
        (ret_t, frame_t), _ = self._vision.get_raw_frames()
        if not ret_t:
            return

        img = cv2.resize(cv2.cvtColor(frame_t, cv2.COLOR_BGR2RGB),
                         (config.TOP_CANVAS_W, config.TOP_CANVAS_H))

        # 注入校正點（用於繪製球桌 felt + rails 邊框）
        calib_pts = self._state._cal.get_points()
        if len(calib_pts) == 4:
            self._scene.set_calibration_points(calib_pts)

        # 場景物件繪圖（僅 PLAY_TEST 模式：felt/口袋/球/預測線）
        if self._state.current_mode() == State.PLAY_TEST:
            self._scene.render_all(img)

        # 校正模式：繪製校正點輔助線
        if self._state.current_mode() == State.TABLE_CALIB:
            self._draw_calibration_helper(img)

        # COLOR_VIEW：繪製 HSV 符合範圍的球 Preview
        if self._state.current_mode() == State.COLOR_VIEW:
            try:
                view = self._state.get_color_view_module()
                img = view.get_overlay(img)
            except Exception:
                pass

        # SHAPE_VIEW：繪製 HoughCircles 偵測範圍 Preview
        if self._state.current_mode() == State.SHAPE_VIEW:
            try:
                view = self._state.get_shape_view_module()
                img = view.get_overlay(img)
            except Exception:
                pass

        # 預測線路繪圖（僅 PLAY_TEST + BREAK_TEST）
        if self._prediction_data:
            if self._state.current_mode() == State.BREAK_TEST:
                self._draw_break(img)
            elif self._state.current_mode() == State.PLAY_TEST and len(self._scene.balls) == 3:
                self._draw_prediction(img)

        self._photo_t = ImageTk.PhotoImage(image=Image.fromarray(img))
        self._canvas_top.create_image(0, 0, image=self._photo_t, anchor=tk.NW)

    def _render_side(self):
        _, (ret_s, frame_s) = self._vision.get_raw_frames()
        if ret_s:
            img_s = cv2.resize(cv2.cvtColor(frame_s, cv2.COLOR_BGR2RGB),
                              (config.SIDE_CANVAS_W, config.SIDE_CANVAS_H))
            self._photo_s = ImageTk.PhotoImage(image=Image.fromarray(img_s))
            self._canvas_side.create_image(0, 0, image=self._photo_s, anchor=tk.NW)

    def _draw_prediction(self, img):
        """在 img 上繪製 ghost ball + 擊球線（普通擊球）"""
        try:
            g_u, g_v = map(int, self._prediction_data["ghost_pixel"])
            r_u, r_v = map(int, self._prediction_data["robot_pixel"])
            cue  = self._scene.get("CUE_BALL")
            tgt  = self._scene.get("TARGET_BALL")
            pkt  = self._scene.get("POCKET")

            if cue and tgt and pkt:
                # 擊球線（藍）：手臂 → 白球
                cv2.line(img, (r_u, r_v), (int(cue.u), int(cue.v)), (255, 0, 0), 2)
                # 瞄準線（白）：白球 → 鬼球
                cv2.line(img, (int(cue.u), int(cue.v)), (g_u, g_v), (255, 255, 255), 1)
                # 進球線（綠）：目標球 → 袋口
                cv2.line(img, (int(tgt.u), int(tgt.v)), (int(pkt.u), int(pkt.v)),
                             (0, 255, 0), 1)

            # 標記
            cv2.drawMarker(img, (r_u, r_v), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)
            cv2.circle(img, (g_u, g_v), 15, (0, 255, 255), 2)
        except Exception as e:
            print(f"線路繪圖錯誤: {e}")

    def _draw_break(self, img):
        """在 img 上繪製開球線（無 ghost ball，只有機器人 → 白球）"""
        try:
            r_u, r_v = map(int, self._prediction_data["robot_pixel"])
            cue = self._scene.get("CUE_BALL")

            if cue:
                # 擊球線（藍）：手臂 → 白球
                cv2.line(img, (r_u, r_v), (int(cue.u), int(cue.v)), (255, 128, 0), 3)
                # 白球標記
                cv2.circle(img, (int(cue.u), int(cue.v)), 15, (255, 255, 0), 2)
                cv2.putText(img, "BREAK", (int(cue.u) - 30, int(cue.v) - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

            # 機器人 TCP 位置
            cv2.drawMarker(img, (r_u, r_v), (255, 128, 0), cv2.MARKER_CROSS, 20, 2)
            cv2.putText(img, f"angle={self._prediction_data.get('angle', 0)}° "
                            f"stroke={self._prediction_data.get('stroke_dist', 0)}mm",
                            (r_u - 80, r_v - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 128, 0), 1)
        except Exception as e:
            print(f"開球繪圖錯誤: {e}")

    def _draw_calibration_helper(self, img):
        """在 INSTALL 模式下繪製校正點：已收集的點 + 序號標記 + 順序連線"""
        points = self._state._cal.get_points()
        labels = ["左上", "右上", "右下", "左下"]
        h, w = img.shape[:2]

        # 繪製操作提示（左上角）
        cv2.putText(img, f"校正: {len(points)}/4", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # 已收集的點：畫編號圓圈 + 標籤
        for i, (u, v) in enumerate(points):
            u, v = int(u), int(v)
            color = (0, 255, 0)
            cv2.circle(img, (u, v), 12, color, 2)
            cv2.putText(img, str(i + 1), (u - 6, v + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 依序連線（1→2→3→4→1）
        if len(points) >= 2:
            pts = [tuple(map(int, p)) for p in points]
            for i in range(len(pts) - 1):
                cv2.line(img, pts[i], pts[i + 1], (0, 200, 255), 1)
        if len(points) == 4:
            # 閉合最後一邊
            cv2.line(img, pts[3], pts[0], (0, 200, 255), 1)
            # 畫對角線協助確認視角變換是否合理
            cv2.line(img, pts[0], pts[2], (80, 80, 255), 1)  # 左上→右下
            cv2.line(img, pts[1], pts[3], (80, 80, 255), 1)  # 右上→左下
