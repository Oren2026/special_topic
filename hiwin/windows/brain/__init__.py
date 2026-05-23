"""
windows/brain/__init__.py
brain/ 套件初始化

匯出公開 API：
  RobotBrain    — 決策層核心，整合所有子模組
  HiwinArmBridge — HIWIN RA605 TCP/IP 控制
  StrikerBridge  — Arduino Serial 擊球指令
  CoordinateManager — 像素↔mm 座標轉換
  BilliardStrategy  — Ghost Ball + Bank Shot 策略

使用方式：
  from brain import RobotBrain
  brain = RobotBrain()
  brain.start()
"""
import sys, os
# 確保 brain/ 目錄在 sys.path 最前面（優於外層 windows/）
_brain_dir = os.path.dirname(os.path.abspath(__file__))
if _brain_dir not in sys.path:
    sys.path.insert(0, _brain_dir)
# 移除干擾：windows/ 目錄可能讓 Python 找到錯誤的 config.py
_windows_dir = os.path.dirname(_brain_dir)
while _windows_dir in sys.path:
    sys.path.remove(_windows_dir)

from robot_brain      import RobotBrain
from hiwin_arm       import HiwinArmBridge
from striker_bridge  import StrikerBridge
from coord_manager   import CoordinateManager
from strategy_module import BilliardStrategy
from break_module    import BreakStrategy
from config          import (
    ROBOT_IP, ROBOT_PORT,
    ARDUINO_PORT, ARDUINO_BAUD, ARDUINO_TIMEOUT, STRIKER_MOCK_MODE,
    Z_SAFE_HEIGHT, Z_CUE_ALIGN,
)

__all__ = [
    "RobotBrain",
    "HiwinArmBridge",
    "StrikerBridge",
    "CoordinateManager",
    "BilliardStrategy",
    "BreakStrategy",
    # config 常數
    "ROBOT_IP", "ROBOT_PORT",
    "ARDUINO_PORT", "ARDUINO_BAUD", "ARDUINO_TIMEOUT", "STRIKER_MOCK_MODE",
    "Z_SAFE_HEIGHT", "Z_CUE_ALIGN",
]