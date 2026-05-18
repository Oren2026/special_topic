"""
windows/brain/striker_bridge.py
Arduino 擊球指令橋接（Windows Serial）

從 wsl/striker_bridge.py 移入，改為 Windows COM Port

職責：
  - 接收策略層輸出的 stroke_dist
  - 將擊球指令發送至 Arduino 驅動步進馬達

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

依賴：serial（pyserial）, config (ARDUINO_PORT, ARDUINO_BAUD, ARDUINO_TIMEOUT, STRIKER_MOCK_MODE)
使用：robot_brain.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


class StrikerBridge:
    """
    擊球執行器（Windows COM Port）

    模式切換（config）：
        STRIKER_MOCK_MODE = True  → 只列印指令（測試用）
        STRIKER_MOCK_MODE = False → 實際發送至 Arduino Serial
    """

    def __init__(
        self,
        port: str = None,
        baud: int = None,
        timeout: float = None,
        mock: bool = None,
    ):
        self._port    = port    or config.ARDUINO_PORT
        self._baud    = baud    or config.ARDUINO_BAUD
        self._timeout = timeout or config.ARDUINO_TIMEOUT
        self._mock    = mock    if mock is not None else config.STRIKER_MOCK_MODE

        self._serial    = None
        self._connected = False

        if not self._mock:
            self._connect()

    def _connect(self) -> bool:
        """建立 Serial 連線"""
        try:
            import serial
            self._serial = serial.Serial(
                self._port,
                baudrate=self._baud,
                timeout=self._timeout,
            )
            self._connected = True
            print(f"[StrikerBridge] 已連線 {self._port} @ {self._baud} baud")
            return True
        except Exception as e:
            print(f"[StrikerBridge] 序列連線失敗：{e}，降級至 MOCK 模式")
            self._mock    = True
            self._connected = False
            return False

    def connect(self) -> bool:
        """手動建立連線（MOCK 模式下略過）"""
        if self._mock:
            self._connected = True
            return True
        return self._connect()

    def disconnect(self):
        """關閉 Serial 連線"""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def execute(self, robot_tcp: tuple, stroke_dist: float, angle: float) -> bool:
        """
        發送擊球指令（`goto {dist}`）

        Parameters
        ----------
        robot_tcp : tuple[float, float]
            手臂 TCP 停泊座標 (arm_x, arm_y)，單位 mm（此參數此處未使用）
        stroke_dist : float
            擊球行程（mm），傳給 Arduino 驅動步進馬達
        angle : float
            擊球方向（度）（此參數此處未使用）

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
            resp_str = resp.strip().decode("utf-8", errors="replace")
            print(f"[StrikerBridge] Arduino 回應：{resp_str}")
            return resp_str == "DONE"
        except Exception as e:
            print(f"[StrikerBridge] 發送失敗：{e}")
            return False

    def home(self) -> bool:
        """回原點"""
        if self._mock:
            print("[StrikerBridge] MOCK → home")
            return True
        try:
            self._serial.write(b"home\n")
            resp = self._serial.readline().strip().decode("utf-8", errors="replace")
            return resp == "HOME DONE"
        except Exception as e:
            print(f"[StrikerBridge] home 失敗：{e}")
            return False

    def stop(self) -> bool:
        """立即停止"""
        if self._mock:
            print("[StrikerBridge] MOCK → stop")
            return True
        try:
            self._serial.write(b"stop\n")
            return True
        except Exception as e:
            print(f"[StrikerBridge] stop 失敗：{e}")
            return False

    def query_status(self) -> str:
        """查詢 Arduino 狀態"""
        if self._mock:
            return "MOCK OK"
        try:
            self._serial.write(b"status\n")
            resp = self._serial.readline().strip().decode("utf-8", errors="replace")
            return resp
        except Exception as e:
            return f"ERROR: {e}"

    def close(self):
        """關閉連線（proxy for disconnect）"""
        self.disconnect()