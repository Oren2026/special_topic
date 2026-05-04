"""
windows/main.py — 啟動入口
"""
from control.hmi import HMI


if __name__ == "__main__":
    app = HMI()
    app.run()
