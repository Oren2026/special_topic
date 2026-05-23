# HIWIN RA605 軟體架構設計文件
> 版本：v2.0（Windows-Only 重構）
> 日期：2026-05-16

---

## 1. 架構變更：移除 WSL

```
舊架構（Windows + WSL）：
  Windows（HMI + 視覺） ──TCP:5005──▶ WSL（robot_brain + 策略 + striker MOCK）

新架構（Windows-Only）：
  Windows（HMI + 視覺 + 策略 + striker）
```

**優點：**
- 移除網路層，调试直連
- 一個 repo 管理所有程式碼
- striker_bridge 對接 Arduino 直連（不再經過 WSL）
- 物理模組（`physics/`）在同一進程直接呼叫

**缺點：**
- Windows 負載增加（相機 + UI + 策略同機）
- 但 Mac Mini 性能足夠，影響可忽略

---

## 2. UI 結構

```
┌──────────────────────────────────────────────────────────────┐
│  HIWIN RA605 9-Ball 控制系統                                  │
├─────────────────┬────────────────────────────────────────────┤
│  【校正區】      │                                            │
│  球桌校正        │                                            │
│  球色校正        │         頂視相機畫面 (Canvas)               │
│  球型校正        │         + 模擬覆蓋層                      │
│                 │                                            │
│  【打擊區】      ├────────────────────────────────────────────┤
│  指定打擊        │                                            │
│  開球            │         側視相機畫面 (Canvas)               │
│  自動打擊        │                                            │
│  策略打擊        │                                            │
│                 │                                            │
│  狀態列          │                                            │
│  提示列          │                                            │
└─────────────────┴────────────────────────────────────────────┘
```

---

## 3. 狀態機設計

### 3.1 狀態定義

| 狀態 | 名稱 | 輸入 | 流程 | 輸出 |
|------|------|------|------|------|
| `IDLE` | 待機 | — | — | — |
| `TABLE_CAL` | 球桌校正 | 4 個角點 | 左上→右上→右下→左下 | `calibration.json` |
| `SHAPE_CAL` | 球型校正 | 球體點擊取樣 | 點擊≥3球，取半徑平均→scale | `ball_geometry.yaml` |
| `COLOR_CAL` | 球色校正 | 球體點擊取樣 | 點球→選球號→HSV統計 | `color_ranges.yaml` |
| `MANUAL` | 指定打擊 | POCKET → TARGET → CUE | 三步確認 | `PREDICTION` + striker.execute() |
| `BREAK` | 開球 | CUE_BALL 位置 | 單點確認 | `BREAK_RESULT` + striker.execute() |
| `AUTO` | 自動打擊 | 視覺偵測球 | Vision 取得所有球 | 進入 STRATEGY |
| `STRATEGY` | 策略打擊 | 球位置 + 口袋 | compute_shot(obstacles) + striker.execute() | `STRATEGY_RESULT` |

### 3.2 狀態轉換圖

```
                      IDLE
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
點擊球桌校正        點擊球色校正         點擊自動打擊
    │                   │                   │
    ▼                   ▼                   ▼
TABLE_CAL           COLOR_CAL            AUTO
    │                   │                   │
    └─────────┬─────────┘                   ▼
              │                         STRATEGY
         完成→IDLE                           │
              │                    完成→IDLE
點擊球型校正  │
    │         │
    ▼         │
SHAPE_CAL ────┘
              │
         完成→IDLE
              │
         點擊指定打擊 ──▶ MANUAL ──▶ 完成→IDLE
              │
         點擊開球 ─────▶ BREAK ────▶ 完成→IDLE
```

### 3.3 StateBehavior（純資料定義）

```python
BEHAVIORS = {
    State.TABLE_CAL: {
        "name":       "球桌校正",
        "group":      Group.CALIBRATION,
        "steps":      4,
        "step_label": ["左上", "右上", "右下", "左下"],
        "requires":   None,
        "on_complete":"save_json",
        "output":     "calibration.json",
    },
    State.SHAPE_CAL: {
        "name":       "球型校正",
        "group":      Group.CALIBRATION,
        "steps":      3,       # 至少3球
        "step_label": None,     # 連續取樣
        "requires":   "calibration.json",
        "on_complete":"save_yaml",
        "output":     "ball_geometry.yaml",
    },
    State.COLOR_CAL: {
        "name":       "球色校正",
        "group":      Group.CALIBRATION,
        "steps":      10,      # 球號0-9
        "step_label": ["球0(白)", "球1", ..., "球9"],
        "requires":   "calibration.json",
        "on_complete":"save_yaml",
        "output":     "color_ranges.yaml",
    },
    State.MANUAL: {
        "name":       "指定打擊",
        "group":      Group.STRIKE,
        "steps":      3,
        "step_label": ["口袋", "目標球", "白球"],
        "requires":   "calibration.json + YAML",
        "on_complete":"strategy_compute + striker.execute",
        "output":     "PREDICTION",
    },
    State.BREAK: {
        "name":       "開球",
        "group":      Group.STRIKE,
        "steps":      1,
        "step_label": ["白球位置"],
        "requires":   "calibration.json",
        "on_complete":"break_compute + striker.execute",
        "output":     "BREAK_RESULT",
    },
    State.AUTO: {
        "name":       "自動打擊",
        "group":      Group.STRIKE,
        "steps":      0,       # 全自動
        "requires":   "calibration.json + YAML",
        "on_complete":"transition_to_STRATEGY",
        "output":     "CompeteScene",
    },
    State.STRATEGY: {
        "name":       "策略打擊",
        "group":      Group.STRIKE,
        "steps":      0,
        "requires":   "obstacles from AUTO",
        "on_complete":"compute_shot + striker.execute + physics_validate",
        "output":     "STRATEGY_RESULT",
    },
}
```

---

## 4. 模組結構（Windows-Only）

```
windows/
├── main.py                          # 啟動入口
├── config.py                        # 全域參數
│
├── control/
│   ├── state_machine.py             # 狀態機（重構 v2）
│   ├── hmi.py                       # Tkinter UI
│   ├── socket_client.py             # ⚠️ 廢除（WSL 移除後不需要 TCP client）
│   │
│   ├── calib/
│   │   ├── color_ranges.yaml        # HSV 範圍
│   │   └── ball_geometry.yaml       # 球徑 + scale
│   │
│   └── handlers/                    # [新增] 各狀態 Handler
│       ├── __init__.py
│       ├── table_cal_handler.py     # TABLE_CAL
│       ├── shape_cal_handler.py     # SHAPE_CAL
│       ├── color_cal_handler.py     # COLOR_CAL
│       ├── manual_handler.py         # MANUAL
│       ├── break_handler.py         # BREAK
│       ├── auto_handler.py          # AUTO → STRATEGY
│       └── strategy_handler.py      # STRATEGY
│
├── vision/
│   ├── camera.py                    # USB 雙鏡頭
│   ├── objects.py                   # 球體 + SimulationScene
│   ├── ball_identifier.py           # HoughCircles + HSV
│   ├── vision_pipeline.py           # 整合 pipeline
│   ├── vision_bridge.py             # 相機/mock 介面
│   ├── calibration_control.py       # 4角 Homography
│   └── table_geometry.py            # 幾何計算
│
├── brain/                           # [新增] 決策層（原 WSL）
│   ├── __init__.py
│   ├── robot_brain.py               # 主大腦（整合進 Windows）
│   ├── coord_manager.py             # pixel↔mm（從 WSL 移入）
│   ├── strategy_module.py           # Ghost Ball（從 WSL 移入）
│   ├── bank_shot_planner.py         # 庫邊反彈（從 WSL 移入）
│   ├── break_module.py              # 開球（從 WSL 移入）
│   └── striker_bridge.py            # Arduino 直連（實作取代 MOCK）
│
└── physics/                         # [現有] 獨立物理工具鏈
    ├── __init__.py
    ├── parameters.py
    ├── collision.py
    ├── trajectory.py
    └── calibrator.py                # 空框架
```

### 與舊架構差異

| 項目 | 舊（Windows + WSL） | 新（Windows-Only） |
|------|--------------------|--------------------|
| 策略運算 | WSL robot_brain | `brain/robot_brain.py` |
| 座標轉換 | WSL coord_manager | `brain/coord_manager.py` |
| Ghost Ball | WSL strategy_module | `brain/strategy_module.py` |
| Bank Shot | WSL bank_shot_planner | `brain/bank_shot_planner.py` |
| 擊球執行 | WSL striker（MOCK） | `brain/striker_bridge.py`（實作） |
| 網路通訊 | `socket_client.py` TCP | 廢除，整個流程同程序 |
| 測試模式 | 需要兩端同時運行 | 單端即可測試 |

---

## 5. 資料流

### 5.1 打擊流程（MANUAL）

```
HMI 點擊
   │
   ▼
StateMachine.handle_click()
   │
   ▼
ManualHandler.handle("click", u, v)
   │
   ├── 收集 POCKET / TARGET / CUE
   │
   ▼ 完成後
RobotBrain.compute_shot(
   cue_ball_mm, target_ball_mm, pocket_name, obstacles
)
   │
   ├── CoordManager.pixel_to_mm()      # Windows 內部呼叫
   ├── StrategyModule.compute_shot()   # Ghost Ball + Bank Shot
   ├── PhysicsSimulate.validate()      # Phase 2b 驗證
   └── StrikerBridge.execute()          # Arduino 直連
   │
   ▼
回傳 PREDICTION → HMI._draw_prediction()
```

### 5.2 打擊流程（AUTO → STRATEGY）

```
HMI 點擊「自動打擊」
   │
   ▼
AutoHandler.handle("enter")
   │
   ├── VisionBridge.capture_and_process()
   │        │
   │        ▼
   │   VisionPipeline.run() → CompeteScene
   │        │
   │        ▼
   │   get_obstacles() → [球1, 球2, ...]
   │
   ▼ 偵測足夠球後
StrategyHandler.handle("execute")
   │
   ├── StrategyModule.compute_shot(
   │     cue_ball, target, pocket, obstacles
   │   )
   ├── PhysicsSimulate.validate()
   └── StrikerBridge.execute()
   │
   ▼
回傳 STRATEGY_RESULT
```

---

## 6. StrikerBridge 實作

```python
class StrikerBridge:
    """
    Windows 直連 Arduino（Serial）
    鮑率：9600
    指令：goto {dist} / home / move {dist} / speed {delay} / stop
    回應：DONE / HOME DONE / ERROR OUT_OF_RANGE / UNKNOWN COMMAND
    """

    def __init__(self, port="COM3", baud=9600, timeout=30):
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._serial = None

    def connect(self) -> bool:
        import serial
        self._serial = serial.Serial(self._port, self._baud, timeout=5)
        return True

    def execute(self, robot_tcp, stroke_dist, angle) -> bool:
        cmd = f"goto {int(stroke_dist)}\n"
        self._serial.write(cmd.encode())
        # 等待 DONE
        ...
```

---

## 7. 待確認事項

### 校正區
- [ ] TABLE_CAL 完成後是否自動提示「下一步：球形校正」？
- [ ] 白球（球號 0）是否強制取樣？

### 打擊區
- [ ] MANUAL 完成後「只預測」還是「預測後自動執行」？
- [ ] AUTO 模式下，口袋由使用者選還是系統自動選？
- [ ] STRATEGY 執行完要等人確認，還是連續打完全部球？

### 實作順序
- [ ] Step 1：建立 `brain/` 目錄，搬移 WSL 模組
- [ ] Step 2：StrikerBridge 實作（擺脫 MOCK）
- [ ] Step 3：重構 StateMachine v2 + Handlers
- [ ] Step 4：AUTO → STRATEGY 串接
- [ ] Step 5：物理模組整合 + chain_simulate bug 修復

---

## 8. 版本規劃

```
v1.0（目前）    → Windows + WSL 分離架構，存在網路層
v2.0（目標）    → Windows-Only，移除 WSL
v2.1            → StrikerBridge 實作
v2.2            → StateMachine v2 + Handlers
v2.3            → AUTO → STRATEGY 全鏈路
v2.4            → 物理整合 + chain_simulate bug 修復
```