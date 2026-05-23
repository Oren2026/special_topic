"""
wsl/striker_bridge.py
WSL → Arduino 擊球指令橋接

職責：
  - 接收 strategy_module.get_best_shot() 的輸出
  - 手臂座標直接送至上銀（此模組不處理，由 robot_brain 負責）
  - 本模組將 stroke_dist 轉換為 `goto {dist}` 指令送至 Arduino

命令格式（與 Arduino sketch 對應）：
  home              — 回原點（歸零）
  goto {dist}       — 絕對移動至擊球距離（mm）
  move {dist}       — 相對移動（mm）
  speed {delay}     — 設定速度（越大越慢）
  status            — 查詢狀態
  stop              — 立即停止

Arduino 回應：
  "HOME DONE"       — 歸位完成
  "DONE"            — 移動完成
  "ERROR OUT_OF_RANGE" — 超出範圍
  "UNKNOWN COMMAND"  — 不認識的指令

依賴：serial（pyserial）, config (ARDUINO_DEVICE, ARDUINO_BAUD, ARDUINO_TIMEOUT, STRIKER_MOCK_MODE)
使用：robot_brain.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


class StrikerBridge:
    """
    擊球執行器

    模式切換（config）：
        STRIKER_MOCK_MODE = True  → 只列印指令（測試用）
        STRIKER_MOCK_MODE = False → 實際發送至 Arduino Serial
    """

    def __init__(self):
        self._serial = None
        self._mock = config.STRIKER_MOCK_MODE

        if not self._mock:
            try:
                import serial
                self._serial = serial.Serial(
                    config.ARDUINO_DEVICE,
                    baudrate=config.ARDUINO_BAUD,
                    timeout=config.ARDUINO_TIMEOUT,
                )
                print(f"[StrikerBridge] 已連線 {config.ARDUINO_DEVICE} @ {config.ARDUINO_BAUD} baud")
            except Exception as e:
                print(f"[StrikerBridge] 序列連線失敗：{e}，降級至 MOCK 模式")
                self._mock = True
        else:
            print("[StrikerBridge] MOCK 模式（不實際發送至 Arduino）")

    def execute(self, robot_tcp: tuple, stroke_dist: float, angle: float) -> bool:
        """
        發送擊球指令

        Parameters
        ----------
        robot_tcp : tuple[float, float]
            手臂 TCP 停泊座標 (arm_x, arm_y)，單位 mm
            （此參數由 robot_brain 決定是否用於其他用途）
        stroke_dist : float
            擊球行程（加速距離），單位 mm
        angle : float
            擊球方向（度）

        Returns
        -------
        bool
            執行是否成功
        """
        cmd = f"goto {stroke_dist:.1f}\n"

        if self._mock:
            print(f"[StrikerBridge] MOCK → {cmd.strip()}")
            return True

        try:
            self._serial.write(cmd.encode("utf-8"))
            resp = self._serial.readline()
            resp_str = resp.strip()
            print(f"[StrikerBridge] Arduino 回應：{resp_str}")
            return resp_str == "DONE"
        except Exception as e:
            print(f"[StrikerBridge] 發送失敗：{e}")
            return False

    def close(self):
        if self._serial and not self._mock:
            self._serial.close()
            print("[StrikerBridge] 序列連線已關閉")
