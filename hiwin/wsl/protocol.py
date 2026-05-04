"""
protocol.py — HIWIN 系統共享通訊格式定義
所有 Socket 封包格式以此檔案為唯一事實來源（Single Source of Truth）
Windows 端與 WSL 端共同參考此定義
"""

# =============================================================================
# 傳輸層
# =============================================================================
HOST = "127.0.0.1"
PORT = 5005
# JSON 封包以換行符號 '\n' 結尾（防止粘包）
TERMINATOR = "\n"

# =============================================================================
# 訊息類型
# =============================================================================
MSG_CALIBRATION  = "calibration_points"   # Windows → WSL
MSG_MODE_MANUAL  = "MANUAL"               # Windows → WSL
MSG_MODE_INSTALL = "INSTALL"              # Windows → WSL（內部用，INSTALL 觸發時送的是 CALIBRATION）
MSG_MODE_COMPETE = "COMPETE"             # Windows → WSL
MSG_TYPE_PREDICTION = "PREDICTION"        # WSL → Windows

# =============================================================================
# JSON 欄位名稱
# =============================================================================
FIELD_MODE         = "mode"
FIELD_TASK_ID      = "task_id"
FIELD_VISION_DATA  = "vision_data"
FIELD_TYPE         = "type"
FIELD_U            = "u"
FIELD_V            = "v"
FIELD_CAL_POINTS   = "calibration_points"
FIELD_STRIKER_CFG  = "striker_config"
FIELD_GHOST_PIXEL = "ghost_pixel"
FIELD_ROBOT_PIXEL  = "robot_pixel"
FIELD_IS_REACHABLE = "is_reachable"
FIELD_ANGLE        = "angle"

# =============================================================================
# 物件類型（vision_data 內使用）
# =============================================================================
TYPE_POCKET       = "POCKET"
TYPE_TARGET_BALL  = "TARGET_BALL"
TYPE_CUE_BALL     = "CUE_BALL"

# =============================================================================
# striker_config 預設值（由 config.py 同步）
# =============================================================================
DEFAULT_BALL_DIAMETER    = 38.0   # mm
DEFAULT_POCKET_DIAMETER  = 45.0   # mm
DEFAULT_ACCEL_DIST_LIMIT  = 150.0  # mm
DEFAULT_FORCE_FACTOR     = 1.0

# =============================================================================
# 封包範例（方便對照）
# =============================================================================

# Windows → WSL：校正（INSTALL 模式觸發）
CALIBRATION_PACKET_EXAMPLE = {
    # 順序：左上 → 右上 → 右下 → 左下（像素座標）
    # 例：FIELD_CAL_POINTS: [[100,100], [900,100], [900,500], [100,500]]
}

# Windows → WSL：手動擊球（TEST 模式 / 拖曳更新）
MANUAL_PACKET_EXAMPLE = {
    FIELD_TASK_ID: 1001,
    FIELD_MODE: MSG_MODE_MANUAL,
    FIELD_VISION_DATA: [
        {FIELD_TYPE: TYPE_POCKET,       FIELD_U: 100, FIELD_V: 200},
        {FIELD_TYPE: TYPE_TARGET_BALL, FIELD_U: 320, FIELD_V: 240},
        {FIELD_TYPE: TYPE_CUE_BALL,    FIELD_U: 450, FIELD_V: 300},
    ],
    FIELD_STRIKER_CFG: {
        "ball_diameter":    DEFAULT_BALL_DIAMETER,
        "pocket_diameter":  DEFAULT_POCKET_DIAMETER,
        "accel_dist_limit": DEFAULT_ACCEL_DIST_LIMIT,
        "force_factor":     DEFAULT_FORCE_FACTOR,
    }
}

# WSL → Windows：擊球預測回應
PREDICTION_PACKET_EXAMPLE = {
    FIELD_TYPE:         MSG_TYPE_PREDICTION,
    # 例：FIELD_GHOST_PIXEL:  [320, 240]
    # 例：FIELD_ROBOT_PIXEL:   [450, 300]
    FIELD_IS_REACHABLE: True,
    FIELD_ANGLE:        45.2,        # 擊球角度（度）
}
