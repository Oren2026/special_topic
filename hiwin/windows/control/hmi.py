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
        tk.Button(self._ctrl, text="開球模式（Break）", width=20, bg="#fff3e0",
                 command=lambda: self._on_mode_set(State.BREAK)).pack(pady=5)
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
            State.BREAK:   "開球模式",
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
            State.BREAK:   "請點擊白球位置（Break 將以最大力朝球堆方向擊出）",
            State.TEST:    "直接點擊：目標球 → 白球（口袋已顯示，可直接點選更換）",
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

        # TEST 模式：點擊口袋圓圈 → 自動選定該口袋
        if self._state.current_mode() == State.TEST:
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
        if self._state.current_mode() == State.TEST:
            ball_type = self._state._shot.next_label()
        elif self._state.current_mode() == State.BREAK:
            ball_type = "CUE_BALL"

        result = self._state.handle_click(u, v)
        if result:
            if ball_type and ball_type not in self._scene.balls:
                self._scene.add_or_update(ball_type, u, v)

            # TEST 模式：檢查是否點在球桌範圍外（空白處）
            if self._state.current_mode() == State.TEST and result.get("ready"):
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
        if self._selected_ball:
            u, v = event.x, event.y
            self._scene.add_or_update(self._selected_ball, u, v)
            if self._state.current_mode() == State.TEST:
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
            self._on_mode_set(State.TEST)
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

        # 場景物件繪圖
        self._scene.render_all(img)

        # 安裝模式：繪製校正點輔助線
        if self._state.current_mode() == State.INSTALL:
            self._draw_calibration_helper(img)

        # 預測線路繪圖
        if self._prediction_data:
            if self._state.current_mode() == State.BREAK:
                self._draw_break(img)
            elif len(self._scene.balls) == 3:
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
