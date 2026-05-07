"""
windows/vision/camera.py
鏡頭影像讀取

依賴：cv2, config (CAM_TOP_ID, CAM_SIDE_ID, FOURCC, FRAME_WIDTH, FRAME_HEIGHT, CAMERA_FPS)
輸出：(ret_t, frame_t), (ret_s, frame_s)
"""
import cv2
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class BilliardVision:
    """
    雙鏡頭管理器
    使用 DSHOW 驅動開啟鏡頭，並設定 MJPEG 壓縮格式
    """

    def __init__(self, top_id=None, side_id=None):
        self.top_id = top_id if top_id is not None else config.CAM_TOP_ID
        self.side_id = side_id if side_id is not None else config.CAM_SIDE_ID

        self.cap_top = None
        self.cap_side = None
        self._open_camera(self.top_id, "Top")
        self._open_camera(self.side_id, "Side")

    def _open_camera(self, camera_id: int, name: str):
        """開啟單一鏡頭，失敗時優雅降級（不回傳 None，改寫入 None）"""
        try:
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            if not cap.isOpened():
                print(f"[BilliardVision] 無法開啟鏡頭: {name} (id={camera_id}) — 將使用 mock 模式")
                cap.release()
                return
            # 關鍵：MJPEG 壓縮，大幅降低 USB 頻寬需求
            cap.set(cv2.CAP_PROP_FOURCC,
                    cv2.VideoWriter_fourcc(*config.FOURCC))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS,         config.CAMERA_FPS)
            if name == "Top":
                self.cap_top = cap
            else:
                self.cap_side = cap
        except Exception as e:
            print(f"[BilliardVision] 開啟鏡頭 {name} (id={camera_id}) 時發生例外: {e} — 將使用 mock 模式")

    def get_raw_frames(self):
        """
        回傳：(ret_t, frame_t), (ret_s, frame_s)
        若鏡頭未開啟，回傳 (False, None)
        """
        ret_t, frame_t = (False, None), (False, None)
        ret_s, frame_s = (False, None), (False, None)
        if self.cap_top is not None:
            ret_t, frame_t = self.cap_top.read()
        if self.cap_side is not None:
            ret_s, frame_s = self.cap_side.read()
        return (ret_t, frame_t), (ret_s, frame_s)

    def release(self):
        if self.cap_top is not None:
            self.cap_top.release()
            self.cap_top = None
        if self.cap_side is not None:
            self.cap_side.release()
            self.cap_side = None
