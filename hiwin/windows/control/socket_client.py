"""
windows/control/socket_client.py
TCP Socket 客戶端（連線 WSL）

依賴：socket, json, config (SOCKET_HOST, SOCKET_PORT)
輸出：send(data: dict) / on_message(callback)
使用：CalibrationHandler, ShotDispatcher 由 StateMachine 透過此模組發送
"""
import socket
import json
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

TERMINATOR = "\n"


class SocketClient:
    """
    TCP 客戶端，封裝 JSON 發送 + 粘包接收
    """

    def __init__(self, host=None, port=None):
        self.host = host or config.SOCKET_HOST
        self.port = port or config.SOCKET_PORT
        self._sock = None
        self._buf = ""
        self._callbacks = []
        self._running = False

    # ── 公開 API ─────────────────────────────────────────────────────────────

    def connect(self):
        """嘗試連線 WSL，失敗不拋例外（離線模式）"""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((self.host, self.port))
            print(f"[SocketClient] 已連線 {self.host}:{self.port}")
            self._running = True
            threading.Thread(target=self._recv_loop, daemon=True).start()
        except Exception as e:
            print(f"[SocketClient] 連線失敗（離線模式）: {e}")
            self._sock = None

    def send(self, data: dict):
        """
        發送 JSON 封包（自動附加換行符）
        """
        if self._sock is None:
            return
        try:
            msg = json.dumps(data) + TERMINATOR
            self._sock.sendall(msg.encode("utf-8"))
        except Exception as e:
            print(f"[SocketClient] 發送失敗: {e}")

    def on_message(self, callback):
        """
        註冊收到訊息時的回調（接收 dict）
        callback: callable(data: dict)
        """
        self._callbacks.append(callback)

    def close(self):
        self._running = False
        if self._sock:
            self._sock.close()
            self._sock = None

    # ── 內部 ─────────────────────────────────────────────────────────────────

    def _recv_loop(self):
        """接收執行緒，持續處理粘包"""
        while self._running:
            try:
                data = self._sock.recv(4096).decode("utf-8")
                if not data:
                    break
                self._buf += data
                while TERMINATOR in self._buf:
                    line, self._buf = self._buf.split(TERMINATOR, 1)
                    if line.strip():
                        try:
                            parsed = json.loads(line)
                            for cb in self._callbacks:
                                cb(parsed)
                        except json.JSONDecodeError:
                            pass
            except Exception:
                break
