"""
lib/state.py
獨立狀態列舉（無 UI、無硬體依賴）

從 windows/control/state_machine.py 提取。
"""


class State:
    """
    應用程式狀態列舉。
    供 StateMachine 使用，與 UI 層和硬體層無關。
    """
    IDLE         = "IDLE"
    TABLE_CALIB  = "TABLE_CALIB"   # 檯球桌位置確認（4角校正）
    CIRCLE_CALIB = "CIRCLE_CALIB"  # 球形校正（點球取樣→YAML）
    COLOR_CALIB  = "COLOR_CALIB"   # 顏色校正（點球取樣→YAML）
    COLOR_VIEW   = "COLOR_VIEW"    # 顏色調整（拖曳 UI → YAML）
    SHAPE_VIEW   = "SHAPE_VIEW"    # 球形調整（拖曳 UI → YAML）
    PLAY_TEST    = "PLAY_TEST"     # 打球測試
    BREAK_TEST   = "BREAK_TEST"    # 開球測試
    COMPETE      = "COMPETE"       # 比賽模式（自動辨識）