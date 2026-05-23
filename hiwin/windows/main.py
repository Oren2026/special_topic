"""
windows/main.py — 啟動入口（Windows-Only 架構）

所有決策邏輯在同進程運行，不再依賴 WSL。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from control.hmi import HMI
from brain.robot_brain import RobotBrain


if __name__ == "__main__":
    brain = RobotBrain()
    brain.start()          # 連線手臂 + 擊球機構（MOCK 模式，馬上成功）
    app = HMI(brain)       # 傳入 brain
    app.run()