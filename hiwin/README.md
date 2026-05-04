# HIWIN RA605 9-Ball 撞球機器人

> 版本：2026-05-05
> 狀態：⚠️ `striker_bridge.py` MOCK 模式（`STRIKER_MOCK_MODE=True`），Arduino 通訊待實作

---

## 🖥️ 開發環境

| 端 | Python | 專案路徑 | 備註 |
|----|--------|----------|------|
| WSL | 3.12.3 (.venv) | `~/projects/hiwin_robot/wsl/` | 需設定 WSL IP 至 `windows/config.py` |
| Windows | 3.14.2 | `c:\hiwin_win_project\windows\` | 需設定 `WSL_IP` 環境變數或修改 `config.py` |

**注意**：`striker_bridge.py` 使用 `dict | None`（Python 3.10+），WSL 3.12 / Windows 3.14 皆支援。
`state_machine.py`、`hmi.py` 已修復為 `Optional[...]`（同時支援 Python 3.9+）。

---

## 🏗️ 系統架構

```
┌──────────────────────────────────────────────────────────────┐
│  Windows (感知層 / UI)                                       │
│                                                              │
│  鏡頭 ──▶ vision/camera.py ──▶ 原始影像                      │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  control/hmi.py — Tkinter 主視窗                         │ │
│  │    │                                                  │ │
│  │    ├── control/state_machine.py   (狀態機)              │ │
│  │    │     ├── calibration.py  (INSTALL 模式)           │ │
│  │    │     ├── shot_dispatcher.py (TEST 模式)            │ │
│  │    │     └── break_handler.py   (BREAK 模式)           │ │
│  │    │                                                  │ │
│  │    └── control/socket_client.py  (TCP 發送/接收)       │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │ :5005 TCP                       │
└───────────────────────────┼──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  WSL (決策層 / Brain)                                       │
│                                                              │
│  robot_brain.py ──── 分派模式                                │
│        │                                                   │
│        ├──▶ coord_manager.py   (pixel↔mm)                  │
│        ├──▶ strategy_module.py  (Ghost Ball)                │
│        ├──▶ break_module.py     (Break 開球)                 │
│        └──▶ striker_bridge.py  (→ Arduino，⚠️空殼)        │
└──────────────────────────────────────────────────────────────┘
```

---

## 📂 模組地圖

### Windows 端

| 檔案 | 模組 | 職責 | 主要API |
|------|------|------|---------|
| `windows/main.py` | — | 啟動入口 | `HMI()` → `.run()` |
| `windows/config.py` | — | 所有參數集中管理 | `BALL_DIAMETER`, `CAM_TOP_ID`, ... |
| `windows/vision/camera.py` | `BilliardVision` | 雙鏡頭讀取 + MJPEG設定 | `.get_raw_frames()` → `(ret_t,frame_t),(ret_s,frame_s)` |
| `windows/vision/objects.py` | `BilliardBall`, `SimulationScene` | 球體物件 + 場景渲染 | `.add_or_update(type,u,v)` / `.render_all(img)` / `.get_all_data()` |
| `windows/control/socket_client.py` | `SocketClient` | TCP收發 + 粘包處理 | `.connect()` / `.send(dict)` / `.on_message(cb)` |
|  `windows/control/calibration.py` | `CalibrationHandler` | 4點收集 | `.add_point(u,v)` / `.is_ready()` / `.get_packet()` |
|  `windows/control/shot_dispatcher.py` | `ShotDispatcher` | 3球資料收集 + striker_config | `.add(type,u,v)` / `.is_complete()` / `.get_packet()` |
|  `windows/control/break_handler.py` | `BreakHandler` | 開球白球座標收集 | `.add(u,v)` / `.get_packet()` |
|  `windows/control/state_machine.py` | `StateMachine` | 模式分派（IDLE/INSTALL/TEST/BREAK/COMPETE） | `.set_mode(str)` / `.handle_click(u,v)` / `.handle_drag(type,u,v)` |
| `windows/control/hmi.py` | `HMI` | Tkinter UI + 事件 + 視覺更新迴圈 | `.run()` |

### WSL 端

| 檔案 | 模組 | 職責 | 主要API |
|------|------|------|---------|
| `wsl/main.py` | — | 啟動入口 | `RobotBrain()` → `.start()` |
| `wsl/config.py` | — | WSL端參數（與windows/config.py同步值） | `TABLE_WIDTH`, `ROBOT_MAX_REACH`, ... |
| `wsl/protocol.py` | — | 通訊格式唯一事實來源 | 欄位常數 + 封包範例 |
|  `wsl/coord_manager.py` | `CoordinateManager` | 透視變換 + 座標系轉換 | `.update_calibration(pts)` / `.pixel_to_mm(u,v)` / `.mm_to_pixel(x,y)` |
|  `wsl/strategy_module.py` | `BilliardStrategy` | Ghost Ball + 可達性判斷 | `.get_best_shot(cue_ball, target_ball, pocket)` |
|  `wsl/break_module.py` | `BreakStrategy` | 開球計算（angle=固定, stroke=MAX） | `.compute_break(cue_ball_mm)` |
|  `wsl/striker_bridge.py` | `StrikerBridge` | → Arduino（⚠️待實作） | `.execute(robot_tcp, stroke_dist, angle)` |
| `wsl/robot_brain.py` | `RobotBrain` | Socket Server + 模式分派 | `.start()` |

---

## 🔌 通訊協定（`wsl/protocol.py`）

**Port**: `5005` | **格式**: JSON + `\n` 結尾（防粘包）

### Windows → WSL

#### 校正（INSTALL 模式觸發）
```json
{"calibration_points": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]}
```
順序：左上 → 右上 → 右下 → 左下（像素）

#### 擊球預測（TEST 模式）
```json
{
  "task_id": 1001,
  "mode": "MANUAL",
  "vision_data": [
    {"type": "POCKET",       "u": 100, "v": 200},
    {"type": "TARGET_BALL",  "u": 320, "v": 240},
    {"type": "CUE_BALL",    "u": 450, "v": 300}
  ],
  "striker_config": {
    "ball_diameter":    38.0,
    "pocket_diameter":  50.0,
    "accel_dist_limit": 150.0,
    "force_factor":     1.0
  }
}
```

#### 開球（BREAK 模式）
```json
{
  "task_id": 2001,
  "mode": "BREAK",
  "vision_data": [
    {"type": "CUE_BALL", "u": 400, "v": 80}
  ]
}
```

### WSL → Windows
```json
{
  "type": "PREDICTION",
  "ghost_pixel":  [gu, gv],
  "robot_pixel": [ru, rv],
  "is_reachable": true,
  "angle":       45.2
}
```

```json
{
  "type": "BREAK_RESULT",
  "robot_pixel": [ru, rv],
  "is_reachable": true,
  "angle":        90.0,
  "stroke_dist":   200.0
}
```

---

## 🔄 執行流程

```
1. WSL: python wsl/main.py
   └─▶ RobotBrain.start() 監聽 :5005

2. Windows: python windows/main.py
   └─▶ HMI() → .run()
   └─▶ SocketClient.connect() → 嘗試連線 WSL

3. INSTALL 模式（四角校正）
   使用者點擊4點
     → CalibrationHandler.add_point()
     → StateMachine.handle_click() → .get_packet()
     → SocketClient.send()
     → WSL: coord_manager.update_calibration()
     → 模式重置 IDLE，自動進入 TEST

4. BREAK 模式（開球）
   使用者點擊白球位置
     → BreakHandler.add(u, v)
     → StateMachine.handle_click() → .get_packet()
     → SocketClient.send()
     → WSL: break_module.compute_break()
     → striker.execute(angle=90°, stroke=MAX)
     → 回應 BREAK_RESULT
     → HMI._draw_break() 繪製擊球線

5. TEST 模式（擊球預測）
   校正完成後口袋已預填，使用者依序點擊：TARGET_BALL → CUE_BALL
     → ShotDispatcher.add()
     → StateMachine.handle_click() → .get_packet()
     → SocketClient.send()
     → WSL: robot_brain._handle_manual()
         → coord_manager.pixel_to_mm() × 3
         → strategy_module.get_best_shot()
     → 回應 PREDICTION
     → HMI._draw_prediction() 繪製 ghost ball + 擊球線

6. 拖曳即時更新
   使用者拖曳任一球
     → HMI._on_drag()
     → StateMachine.handle_drag()
     → SocketClient.send(task_id=9999)
     → 即時收到 PREDICTION → 即時繪圖
```

---

## ⚙️ 座標系定義

```
球檯：1200 × 630 mm
手臂原點 (0,0)：長邊中點，底座貼齊邊緣
X軸：[-600, +600]
Y軸：[0, 630]

pixel_to_mm:  像素 (u,v) → 手臂mm (arm_x, arm_y)
mm_to_pixel:  手臂mm (arm_x, arm_y) → 像素 (u,v)
```

---

## ⚠️ 待確認 / 待實作

|| 項目 | 優先級 | 說明 |
|------|--------|------|
| `striker_bridge.py` | 🔴 高 | WSL→Arduino 介面已定義，序列通訊待實作 |
| 口袋真實座標 | 🟡 中 | `strategy_module.POCKETS` 硬編碼，需與實際球檯對齊 |
| 多口袋候選線 | 🟡 中 | 一次顯示 6 條可行路徑，方案 A（見下方策略藍圖） |
| 開球多方向 | 🟡 中 | BREAK 目前 angle=90° 固定，未來支援多方向開球 |
| COMPETE 模式 | 🟡 中 | 尚未實作（自動辨識流程） |
| 校正資料持久化 | 🟡 中 | 矩陣存在記憶體，斷電消失 |
| 策略學習層 | 🟢 低 | 貝氏估計 / 強化學習權重，累積擊球資料訓練 |
| `win_ui_vision.py` | 🟢 低 | HSV 參數調校工具，可整合至 HMI |
| `find_cameras.py` | 🟢 低 | 鏡頭ID掃描工具，獨立使用 |

---

## 📋 策略藍圖（未來擴展）

### Phase 1：幾何優先（當前）
- 單一路徑計算（Ghost Ball）
- 6 口袋各自獨立計算

### Phase 2：多路徑展示
- `compute_all_shots(cue, target)` → 6 條候選線
- 依安全性評分（0~1）→ 顏色分組（紅/黃/綠）
- 使用者點選其中一條執行

### Phase 3：學習層（數據驅動）
- 每桿結果寫入 `ShotRecord` 資料庫
- 貝氏估計：每局後更新 `P(pocket | cue_pos, target_pos)`
- 訓練方向：安全 > 進攻 > 高風險犯規
- 最終目標：手臂越打越強

---

## 📦 參數同步

Windows 與 WSL 雙方共同依賴以下同步值（需保持一致）：

| 參數 | 值 | 說明 |
|------|-----|------|
| 球檯尺寸 | 1200×630 mm | |
| 球徑 | 38 mm | |
| 洞口徑 | 50 mm | |
| 手臂 OFFSET_X | 600 mm | 長邊中點對齊 |
| 手臂最大半徑 | 750 mm | |
| 固定擊球長度 | 200 mm | |
| 安全間隙 | 80 mm | |
