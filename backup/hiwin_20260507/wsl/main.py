"""
wsl/main.py — 啟動入口
"""
from robot_brain import RobotBrain


if __name__ == "__main__":
    brain = RobotBrain()
    brain.start()
