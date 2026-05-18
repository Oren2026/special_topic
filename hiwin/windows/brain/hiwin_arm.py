"""
windows/brain/hiwin_arm.py
HIWIN RA605 手臂 TCP/IP 控制橋接

職責：
  - 建立並維護 TCP socket 連線至 HIWIN RA605（預設 192.168.50.200:4000）
  - 發送手臂運動指令（X, Y, Z, C 軸）
  - 查詢手臂狀態

指令格式（HIWIN RA605 通訊協定）：
  運動： POS=xxx,yyy,zzz,ccc\r\n  （X/Y/Z 單位 0.1mm，C 軸單位 0.001°）
  查詢： STA?\r\n  歸零： HOME\r\n  停止： STOP\r\n  速度： SPEED={value}\r\n  模式： G0 (快速) / G1 (直線插補)\r\n

回應：
  OK          — 指令接受
  BUSY        — 運動中
  ERR:{code}  — 錯誤
  READY       — 歸位完成

依賴：socket（Python 標準庫）
使用：robot_brain.py
"""

import socket
import time
import threading
from typing import Optional


class HiwinArmBridge:
    """
    HIWIN RA605 手臂 TCP/IP 控制

    使用方式：
        arm = HiwinArmBridge(ip="192.168.50.200", port=4000)
        arm.connect()
        arm.move_to(x=100.0, y=200.0, z=50.0, c=0.0)   # 單位：mm / degree
        arm.wait_until_ready()
        arm.close()
    """

    def __init__(
        self,
        ip: str = "192.168.50.200",
        port: int = 4000,
        timeout: float = 10.0,
        mock: bool = True,
    ):
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self._mock = mock

        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._connected = False
        self._busy = False

    # ── 連線管理 ──────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """建立 TCP 連線"""
        if self._mock:
            self._connected = True
            print("[HiwinArm] MOCK 模式（不實際連線手臂）")
            return True

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self._timeout)
            self._sock.connect((self._ip, self._port))
            self._connected = True
            print(f"[HiwinArm] 已連線 {self._ip}:{self._port}")
            return True
        except Exception as e:
            print(f"[HiwinArm] 連線失敗：{e}")
            self._connected = False
            return False

    def disconnect(self):
        """斷開 TCP 連線"""
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # ── 核心指令 ──────────────────────────────────────────────────────────────

    def move_to(
        self,
        x: float,
        y: float,
        z: float,
        c: float = 0.0,
        speed: float = 100.0,
        wait: bool = True,
    ) -> bool:
        """
        發送手臂定位指令（直線插補模式 G1）

        參數：
            x, y, z : 手臂座標（mm）
            c       : C 軸角度（度）
            speed   : 速度（%），1-100
            wait    : 是否等待 READY（封鎖直到手臂停止）

        回傳：True = 指令成功發送
        """
        if self._mock:
            print(f"[HiwinArm] MOCK move_to({x}, {y}, {z}, C={c})")
            self._busy = True
            time.sleep(0.5)   # 模擬運動時間
            self._busy = False
            return True

        if not self._connected:
            return False

        # 格式化：X/Y/Z 放大 10 倍（單位 0.1mm），C 放大 1000 倍（0.001°）
        cmd = f"G1 X{x*10:.0f} Y{y*10:.0f} Z{z*10:.0f} C{c*1000:.0f} F{speed:.0f}\r\n"

        with self._lock:
            try:
                self._sock.sendall(cmd.encode("ascii"))
                resp = self._read_line()
                print(f"[HiwinArm] → {cmd.strip()} | ← {resp}")
                if resp.startswith("ERR"):
                    return False
                self._busy = True
            except Exception as e:
                print(f"[HiwinArm] 發送失敗：{e}")
                return False

        if wait:
            self.wait_until_ready()

        return True

    def move_z_for_cue_alignment(
        self,
        x: float,
        y: float,
        z_target: float,
        c: float = 0.0,
    ) -> bool:
        """
        Z 軸對準白球：

        1. 手臂移到 (x, y, z_approach)：上方安全高度（接觸前）
        2. 手臂緩慢下移至 (x, y, z_target)：對準白球表面
        3. Arduino 擊球
        4. 手臂抬回安全高度

        參數：
            x, y        : TCP 位置（mm），y 應已扣掉桿頭偏移（ball_y - 50）
            z_target    : Z 軸對準白球的高度（mm，相對球檯面）
            c           : C 軸角度（度），對準打擊方向
        """
        z_approach = z_target + 90.0   # 上方 90mm 安全間距

        print(f"[HiwinArm] Z對準：({x}, {y}, z_approach={z_approach}) → ({x}, {y}, z_target={z_target}), C={c}")

        # Step 1: 移到上方安全高度
        ok = self.move_to(x=x, y=y, z=z_approach, c=c, wait=True)
        if not ok:
            return False

        # Step 2: 緩慢下移至對準高度（低速，給 Arduino 時間）
        ok = self.move_to(x=x, y=y, z=z_target, c=c, speed=10.0, wait=True)
        if not ok:
            return False

        return True

    def lift_after_shot(self, x: float, y: float, z_safe: float = 100.0, c: float = 0.0) -> bool:
        """擊球後抬起手臂至安全高度"""
        return self.move_to(x=x, y=y, z=z_safe, c=c, wait=True)

    def home(self, wait: bool = True) -> bool:
        """手臂歸零"""
        return self._send_cmd("HOME\r\n", wait=wait)

    def stop(self) -> bool:
        """緊急停止"""
        with self._lock:
            self._busy = False
            return self._send_cmd("STOP\r\n", wait=False)

    def query_status(self) -> str:
        """查詢手臂狀態"""
        return self._send_cmd("STA?\r\n", wait=True)

    def wait_until_ready(self, poll_interval: float = 0.2, timeout: float = 30.0) -> bool:
        """輪詢直到手臂 READY 或超時"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.query_status().strip()
            if "READY" in status or "OK" in status:
                self._busy = False
                return True
            time.sleep(poll_interval)
        print(f"[HiwinArm] 等候手臂 READY 超時（{timeout}s）")
        return False

    # ── 內部 ──────────────────────────────────────────────────────────────────

    def _send_cmd(self, cmd: str, wait: bool = True) -> bool:
        """發送指令（已取 lock）"""
        if self._mock:
            print(f"[HiwinArm] MOCK: {cmd.strip()}")
            return True

        if not self._connected:
            return False

        try:
            self._sock.sendall(cmd.encode("ascii"))
            if wait:
                resp = self._read_line()
                print(f"[HiwinArm] → {cmd.strip()} | ← {resp}")
                return "ERR" not in resp
            return True
        except Exception as e:
            print(f"[HiwinArm] 發送失敗：{e}")
            return False

    def _read_line(self) -> str:
        """讀取一行回應"""
        if not self._sock:
            return ""
        try:
            data = self._sock.recv(1024)
            return data.decode("ascii").strip()
        except socket.timeout:
            return "TIMEOUT"
