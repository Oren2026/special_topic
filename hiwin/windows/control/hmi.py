"""
windows/control/hmi.py
Tkinter 人機介面

依賴：tkinter, cv2, PIL, StateMachine, SocketClient, BilliardVision, SimulationScene
輸出：Tkinter 視窗
"""
import tkinter as tk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from .state_machine import StateMachine, State
from .socket_client import SocketClient
from ..vision import BilliardVision, SimulationScene


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

        self._state = StateMachine(self._socket)
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

        tk.Label(self._ctrl, text="控制面板", font=('Arial', 16, 'bold')).pack(pady=10)

        tk.Button(self._ctrl, text="安裝模式（四角標定）", width=20, bg="#f0f0f0",
                 command=lambda: self._on_mode_set(State.INSTALL)).pack(pady=5)
        tk.Button(self._ctrl, text="測試模式（模擬擊球）", width=20, bg="#e1f5fe",
                 command=lambda: self._on_mode_set(State.TEST)).pack(pady=5)
        tk.Button(self._ctrl, text="比賽模式（自動辨識）", width=20, bg="#ffcdd2",
                 command=lambda: self._on_mode_set(State.COMPETE)).pack(pady=5)

        self._status_lbl = tk.Label(self._ctrl, text="目前狀態: 待機中", fg="blue")
        self._status_lbl.pack(pady=20)

        self._info_lbl = tk.Label(self._ctrl, text="請先執行安裝模式", justify=tk.LEFT)
        self._info_lbl.pack(side=tk.BOTTOM, pady=10)

        # 中：頂視主畫面
        self._canvas_top = tk.Canvas(self._root, width=config.TOP_CANVAS_W,
                                      height=config.TOP_CANVAS_H, bg="black")
        self._canvas_top.pack(side=tk.LEFT, padx=5)

        # 右：側視監控
        self._canvas_side = tk.Canvas(self._root, width=config.SIDE_CANVAS_W,
                                       height=config.SIDE_CANVAS_H, bg="black")
        self._canvas_side.pack(side=tk.TOP, padx=10, pady=20)

    def _setup_events(self):
        # 點擊 → 狀態機處理
        self._canvas_top.bind("<Button-1>", self._on_click)
        # 拖曳 → 即時更新
        self._canvas_top.bind("<B1-Motion>", self._on_drag)
        self._canvas_top.bind("<ButtonRelease-1>", self._on_release)

    # ── 模式切換 ─────────────────────────────────────────────────────────────

    def _on_mode_set(self, mode: str):
        self._state.set_mode(mode)
        self._scene = SimulationScene()  # 清除舊場景
        self._prediction_data = None

        labels = {
            State.INSTALL: "安裝模式",
            State.TEST:    "測試模式",
            State.COMPETE: "比賽模式",
        }
        self._status_lbl.config(text=f"狀態: {labels.get(mode, mode)}")
        self._info_lbl.config(text=self._get_mode_hint(mode))

        if mode == State.INSTALL:
            messagebox.showinfo("安裝指引",
                "請在頂視畫面依序點擊球桌四個角：\n1. 左上 2. 右上 3. 右下 4. 左下")

    def _get_mode_hint(self, mode) -> str:
        hints = {
            State.INSTALL: "請依序點擊：左上 → 右上 → 右下 → 左下",
            State.TEST:    "請依序點擊：袋口 → 目標球 → 白球",
            State.COMPETE: "自動辨識模式（待實作）",
        }
        return hints.get(mode, "")

    # ── 點擊 / 拖曳 ──────────────────────────────────────────────────────────

    def _on_click(self, event):
        u, v = event.x, event.y

        # 球體碰撞檢測（優先於狀態機處理）
        hit = self._hit_test(u, v)
        if hit:
            self._selected_ball = hit
            return

        # 否則交給狀態機處理
        result = self._state.handle_click(u, v)
        if result:
            ball_type = self._selected_ball  # 可能已被 handle_click 內部加入
            if result.get("ready"):
                self._info_lbl.config(text="擊球任務已發送！\n可直接拖曳調整路徑。")
            else:
                self._info_lbl.config(text=f"已記錄: {result.get('label')}")

    def _on_drag(self, event):
        if self._selected_ball:
            u, v = event.x, event.y
            self._scene.add_or_update(self._selected_ball, u, v)
            if self._state.current_mode() == State.TEST:
                self._state.handle_drag(self._selected_ball, u, v)

    def _on_release(self, event):
        self._selected_ball = None

    def _hit_test(self, u, v) -> str | None:
        """回傳被點中的球類型，或 None"""
        for ball_type, ball in self._scene.balls.items():
            if ((ball.u - u)**2 + (ball.v - v)**2) ** 0.5 < 20:
                return ball_type
        return None

    # ── Socket 回應 ──────────────────────────────────────────────────────────

    def _on_wsl_message(self, data: dict):
        if data.get("type") == "PREDICTION":
            self._prediction_data = data

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

        # 場景物件繪圖
        self._scene.render_all(img)

        # 預測線路繪圖
        if self._prediction_data and len(self._scene.balls) == 3:
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
        """在 img 上繪製 ghost ball + 擊球線"""
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
