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

        self.cap_top = cv2.VideoCapture(self.top_id, cv2.CAP_DSHOW)
        self.cap_side = cv2.VideoCapture(self.side_id, cv2.CAP_DSHOW)

        for name, cap in [("Top", self.cap_top), ("Side", self.cap_side)]:
            if not cap.isOpened():
                print(f"[BilliardVision] 無法開啟鏡頭: {name}")
                continue

            # 關鍵：MJPEG 壓縮，大幅降低 USB 頻寬需求
            cap.set(cv2.CAP_PROP_FOURCC,
                    cv2.VideoWriter_fourcc(*config.FOURCC))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS,         config.CAMERA_FPS)

    def get_raw_frames(self):
        """
        回傳：(ret_t, frame_t), (ret_s, frame_s)
        """
        ret_t, frame_t = self.cap_top.read()
        ret_s, frame_s = self.cap_side.read()
        return (ret_t, frame_t), (ret_s, frame_s)

    def release(self):
        self.cap_top.release()
        self.cap_side.release()
