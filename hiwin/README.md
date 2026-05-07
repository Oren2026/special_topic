# HIWIN RA605 9-Ball 撞球機器人

> 版本：2026-05-07
> 狀態：✅ Ghost Ball D 偏移 + Bank Shot Planner + 物理模組 + 71 tests + 校正系統（顏色/球形 + VIEW）
> 測試：**71/71 PASS** ✅

---

## 📑 目錄

1. [開發環境](#開發環境)
2. [系統架構圖](#系統架構圖)
3. [模組關係圖](#模組關係圖)
4. [Windows 端模組](#windows-端模組)
5. [WSL 端模組](#wsl-端模組)
6. [物理模組](#物理模組)
7. [通訊協定](#通訊協定)
8. [執行流程](#執行流程)
9. [座標系定義](#座標系定義)
10. [待辦追蹤](#待辦追蹤)
11. [策略藍圖](#策略藍圖)

---

## 開發環境

| 端 | Python | 專案路徑 | 備註 |
|----|--------|----------|------|
| WSL | 3.12.3 (.venv) | `~/projects/hiwin_robot/wsl/` | 需設定 WSL IP 至 `windows/config.py` |
| Windows | 3.14.2 | `c:\hiwin_win_project\windows\` | 需設定 `WSL_IP` 環境變數或修改 `config.py` |

> Python 版本：Windows / WSL 兩端皆使用 `Optional[...]`（Python 3.9+ 相容），`dict | None` 語法（Python 3.10+）僅用於 WSL 內部模組。

---

## 系統架構圖

```
┌─────────────────────────────────────────────────────────────────────┐
│  Windows 端（感知層 / UI）                                            │
│                                                                     │
│  ┌──────────────┐      ┌─────────────────────────────────────────┐  │
│  │  USB Camera  │─────▶│  vision/camera.py  (雙鏡頭擷取)          │  │
│  └──────────────┘      │   BilliardVision.get_raw_frames()       │  │
│                        └──────────────────┬──────────────────────┘  │
│                                             │                       │
│                        ┌────────────────────▼──────────────────────┐  │
│                        │     windows/control/                      │  │
│                        │                                         │  │
│                        │  hmi.py ────── Tkinter 主視窗             │  │
│                        │      │                                   │  │
│                        │      ├─▶ state_machine.py  (模式分派)     │  │
│                        │      │       │                            │  │
│                        │      │       ├─▶ calibration.py  (INSTALL) │  │
│                        │      │       ├─▶ shot_dispatcher.py(TEST) │  │
│                        │      │       ├─▶ break_handler.py(BREAK)  │  │
│                        │      │       └─▶ [COMPETE] → VisionBridge │  │
│                        │      │                                   │  │
│                        │      └─▶ socket_client.py  (TCP 收发)    │  │
│                        │                                         │  │
│                        │  ── Vision 視覺模組 ──────────────────── │  │
│                        │      ├─▶ vision_bridge.py   (相機/mock)  │  │
│                        │      ├─▶ vision_pipeline.py (整合 pipeline)│  │
│                        │      ├─▶ ball_identifier.py (HoughCircles│  │
│                        │      │              + HSV 顏色分類)        │  │
│                        │      ├─▶ calibration_control.py (4角校正)│  │
│                        │      ├─▶ table_geometry.py  (幾何計算)   │  │
│                        │      └─▶ sim_table.py      (模擬球檯)   │  │
│                        └─────────────────────────────────────────┘  │
│                                    │ :5005 TCP                      │
└────────────────────────────────────┼────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  WSL 端（決策層 / Brain）                                            │
│                                                                     │
│  robot_brain.py ──── 模式分派                                        │
│       │                                                              │
│       ├─▶ coord_manager.py    (pixel↔mm 透視變換)                   │
│       ├─▶ strategy_module.py  (Ghost Ball 演算法)                   │
│       ├─▶ bank_shot_planner.py (庫邊反彈計算)                        │
│       ├─▶ break_module.py     (Break 開球)                          │
│       └─▶ striker_bridge.py  (→ Arduino，⚠️ MOCK)                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  物理驗證工具鏈（獨立於決策流程）                                │   │
│  │  physics/                                                      │   │
│  │   ├─ collision.py  (BallState, 碰撞偵測, 彈性碰撞, 庫邊反射)   │   │
│  │   └─ trajectory.py (軌跡預測, TrajectoryResult)                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 模組關係圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           模組關係圖 / Module Map                            │
│                                                                             │
│  Windows 端                                                                 │
│  ══════════                                                                 │
│                                                                             │
│   camera.py                                                                 │
│       │                                                                     │
│       ▼                                                                     │
│   vision_bridge.py  ◄─── VisionBridge (相機/mock 統一介面)                   │
│       │                              · start_camera() / start_mock()       │
│       │                              · capture_and_process() → scene        │
│       ▼                                                                     │
│   vision_pipeline.py  ◄─── VisionPipeline (整合層)                            │
│       │                              · set_frame() / run() → CompeteScene   │
│       │                              · get_obstacles() → [{"x","y"},...]   │
│       │                              · get_next_target()                    │
│   ┌───┴────────────────────────────────────────┐                            │
│   │                                         │                             │
│   ▼                                         ▼                             │
│   ball_identifier.py              calibration_control.py                    │
│   · HoughCircles 偵測圓形           · 4角點收集 → pixel↔mm 矩陣          │
│   · HSV 顏色分類                    · is_valid() / pixel_to_mm()          │
│   · _ball_confidence()             · get_points() / get_matrix()            │
│   │                                 └──────────────────────────┐            │
│   ▼                                                    │                    │
│   table_geometry.py  ◄─────────────────────────────────┘                    │
│   · 球徑估算 (pixel)                    · set_calibration()                │
│   · scale_x() / scale_y()               · expected_ball_radius_pixel()       │
│   · pixel_to_mm_2d()                   · hough_radius_range()               │
│   · distance_mm() / ball_to_pocket_mm()                                  │
│                                                                             │
│   hmi.py  ──── Tkinter UI                                                 │
│       │                                                                     │
│       ▼                                                                     │
│   state_machine.py  ◄─── 模式分派                                          │
│   ┌────────┬─────────┬──────────┬──────────┬─────────────┬────────────────┐│
│   ▼        ▼         ▼          ▼          ▼              ▼                │
│   INSTALL  TEST      BREAK    COMPETE    COLOR_VIEW      SHAPE_VIEW        │
│   (calib)  (shot)   (break)   (auto)     (顏色微調)      (球形微調)        │
│       │                                                        │            │
│       ▼                                                        ▼            │
│   calibration.py                                    vision_bridge.py         │
│                                                     capture_and_process()     │
│                                                     ↓                        │
│   shot_dispatcher.py                                robot_brain.compute_shot()│
│   break_handler.py                                  (障礙球已接入)          │
│                                                                             │
│       ▼                                                                     │
│   socket_client.py  ──── TCP :5005 ──────────────────────────────▶ WSL     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  WSL 端                                                                     │
│  ═════                                                                  │
│                                                                             │
│   robot_brain.py  ◄───── 接收 Windows 封包，模式分派                         │
│        │                                                                   │
│        ├─▶ coord_manager.py                                               │
│        │      · update_calibration(pts) → 建立 Homography                  │
│        │      · pixel_to_mm() / mm_to_pixel()                             │
│        │                                                                   │
│        ├─▶ strategy_module.py                                             │
│        │      · get_best_shot() → Ghost Ball 瞄準點                        │
│        │      · compute_shot() → 支援 obstacles 障礙球參數                  │
│        │                                                                   │
│        ├─▶ bank_shot_planner.py                                           │
│        │      · plan_bank_shot() → 鏡像法計算庫邊反彈                      │
│        │      · direct_vs_bank() → 直接/反彈 選擇                          │
│        │                                                                   │
│        ├─▶ break_module.py                                                │
│        │      · compute_break() → 開球角度/力道                            │
│        │                                                                   │
│        └─▶ striker_bridge.py                                              │
│               · execute() → ⚠️ MOCK（Arduino 待實作）                       │
│                                                                             │
│  物理驗證工具鏈（獨立模組，不參與決策）                                        │
│  ═════════════════════════════════════════════                              │
│   physics/collision.py     — BallState, collision_detect, resolve_elastic   │
│   physics/trajectory.py   — simulate() → TrajectoryResult                  │
│   physics/parameters.py   — RESTITUTION=0.95, DT_MS=10, BALL_RADIUS=19mm  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 資料流向（擊球預測流程）

```
使用者點擊球檯
    │
    ▼
hmi.py handle_click()
    │
    ▼
state_machine.py ──▶ INSTALL / TEST / BREAK / COMPETE
    │
    ▼
socket_client.send(json)
    │
    ▼  TCP :5005
robot_brain.py (WSL)
    │
    ├── INSTALL ──▶ coord_manager.update_calibration()
    │
    ├── TEST ─────▶ coord_manager.pixel_to_mm()
    │                   │
    │                   ▼
    │              strategy_module.compute_shot(obstacles=[...])
    │                   │
    │                   ▼
    │              bank_shot_planner.plan_bank_shot()
    │                   │
    │                   ▼
    │              PREDICTION {ghost_pixel, robot_pixel, angle}
    │
    ├── BREAK ─────▶ break_module.compute_break()
    │                   │
    │                   ▼
    │              BREAK_RESULT {robot_pixel, angle, stroke_dist}
    │
    └── COMPETE ───▶ vision_bridge.capture_and_process()
                        │
                        ▼
                   vision_pipeline.run()
                        │
                        ▼
                   vision_pipeline.get_obstacles()
                        │
                        ▼
                   robot_brain.compute_shot(obstacles=[...])

物理驗證（獨立流程，不走 robot_brain）：
physics.simulate(cue_pos, cue_dir, target_pos, pocket_pos, obstacles)
    →
    TrajectoryResult {cue_path, target_path, collision_events, wall_events, pocket_sunk}
```

---

## Windows 端模組

### 視覺 Vision

| 檔案 | 模組 | 職責 | 主要 API |
|------|------|------|---------|
| `vision/camera.py` | `BilliardVision` | USB 雙鏡頭讀取 + MJPEG 設定 | `.get_raw_frames()` → `(ret_t, frame_t), (ret_s, frame_s)` |
| `vision/objects.py` | `BilliardBall`, `SimulationScene` | 球體物件 + 模擬場景渲染 | `.add_or_update(type, u, v)` / `.render_all(img)` / `.get_all_data()` |
| `control/ball_identifier.py` | `BallIdentifier` | HoughCircles 圓形偵測 + HSV 顏色分類 | `.detect_all()` → `[DetectedBall, ...]` / `.classify_color(u,v,r)` |
| `control/calibration_control.py` | `CalibrationControl` | 4角校正點收集 + pixel↔mm Homography | `.add_click()` / `.compute()` / `.pixel_to_mm()` / `.is_valid()` |
| `control/table_geometry.py` | `TableGeometry` | 球檯幾何計算、球徑估算、比例尺 | `.scale_x/y()` / `.expected_ball_radius_pixel()` / `.pixel_to_mm_2d()` |
| `control/vision_pipeline.py` | `VisionPipeline` | 視覺整合層：圓形→顏色→排序→mm座標 | `.set_frame()` / `.run()` → `CompeteScene` / `.get_obstacles()` |
| `control/vision_bridge.py` | `VisionBridge` | 相機/mock 統一介面 → robot_brain 串接 | `.start_camera()` / `.start_mock()` / `.capture_and_process()` |
| `control/sim_table.py` | `SimTable` | 模擬球檯（無硬體測試用） | `.add_ball()` / `.render()` / `.get_mock_scene()` |

### 控制 Control

| 檔案 | 模組 | 職責 | 主要 API |
|------|------|------|---------|
| `control/socket_client.py` | `SocketClient` | TCP 收發 + 粘包處理 | `.connect()` / `.send(dict)` / `.on_message(cb)` |
| `control/calibration.py` | `CalibrationHandler` | INSTALL 模式：4點收集 | `.add_point(u, v)` / `.is_ready()` / `.get_packet()` |
| `control/shot_dispatcher.py` | `ShotDispatcher` | TEST 模式：3球資料收集 | `.add(type, u, v)` / `.is_complete()` / `.get_packet()` |
| `control/break_handler.py` | `BreakHandler` | BREAK 模式：白球座標收集 | `.add(u, v)` / `.get_packet()` |
| `control/state_machine.py` | `StateMachine` | 模式分派（9態）| `.set_mode()` / `.handle_click(u, v)` / `.handle_drag()` |
| `control/hmi.py` | `HMI` | Tkinter UI + 事件 + 視覺更新迴圈 | `.run()` |
| `control/color_calib_module.py` | `ColorCalibModule` | 顏色校正：點擊球 → HSV 取樣 → 數字鍵盤 → YAML | `run()` / `get_overlay()` |
| `control/shape_calib_module.py` | `ShapeCalibModule` | 球形校正：點擊球 → HoughCircles → 半徑平均 → scale → YAML | `run()` / `get_overlay()` |
| `control/color_view_module.py` | `ColorViewModule` | 顏色微調：YAML → 滑桿 → 即時 HSV 疊加預覽 → 自動儲存 | `run()` / `get_overlay()` |
| `control/shape_view_module.py` | `ShapeViewModule` | 球形微調：YAML → 滑桿 → HoughCircles 覆寫預覽 → 自動儲存 | `run()` / `get_overlay()` |

### 校正資料 Calibration Data

| 檔案 | 內容 |
|------|------|
| `calib/color_ranges.yaml` | 各球 HSV 範圍（cue_ball, ball_1~9 + name） |
| `calib/ball_geometry.yaml` | 球徑 38mm、scale_x/y、Hough 半徑範圍（13~35px）|

---

## WSL 端模組

| 檔案 | 模組 | 職責 | 主要 API |
|------|------|------|---------|
| `wsl/main.py` | — | 啟動入口 | `RobotBrain()` → `.start()` |
| `wsl/config.py` | — | WSL 端參數（與 windows/config.py 同步） | `TABLE_WIDTH`, `ROBOT_MAX_REACH`, ... |
| `wsl/protocol.py` | — | 通訊格式唯一事實來源 | 欄位常數 + 封包範例 |
| `wsl/coord_manager.py` | `CoordinateManager` | 透視變換 + 座標系轉換 | `.update_calibration(pts)` / `.pixel_to_mm(u,v)` / `.mm_to_pixel(x,y)` |
| `wsl/strategy_module.py` | `BilliardStrategy` | Ghost Ball + 可達性判斷 | `.get_best_shot()` / `.compute_shot(obstacles=[])` |
| `wsl/bank_shot_planner.py` | `BankShotPlanner` | 庫邊反彈計算（鏡像法） | `.plan_bank_shot()` / `.direct_vs_bank()` |
| `wsl/break_module.py` | `BreakStrategy` | 開球計算（angle=固定, stroke=MAX） | `.compute_break(cue_ball_mm)` |
| `wsl/striker_bridge.py` | `StrikerBridge` | → Arduino（⚠️ MOCK） | `.execute(robot_tcp, stroke_dist, angle)` |
| `wsl/robot_brain.py` | `RobotBrain` | Socket Server + 模式分派 | `.start()` |

---

## 物理模組

獨立於決策流程的物理驗證工具鏈，用於軌跡預測、碰撞模擬、策略回測。

### 檔案

| 檔案 | 職責 |
|------|------|
| `physics/parameters.py` | 常數：`BALL_RADIUS=19mm`, `RESTITUTION=0.95`, `DT_MS=10`, `POCKET_RADIUS=25mm` |
| `physics/collision.py` | `BallState`, `collision_detect`, `resolve_elastic`, `reflect_wall`, `is_in_pocket` |
| `physics/trajectory.py` | `simulate()` → `TrajectoryResult`（完整軌跡 + 事件日誌）|

### API 速查

```python
from physics import simulate, BallState, TrajectoryResult

result = simulate(
    cue_pos   = (200, 315),      # 白球 mm
    cue_dir   = (1, 0),           # 瞄準方向單位向量
    target_pos= (550, 315),      # 目標球 mm
    pocket_pos= (575, 315),      # 口袋 mm
    obstacles = [(400, 315)],    # 障礙球列表
    speed     = 3000,            # 擊球初速 mm/s
    dt_ms     = 10,              # 模擬步長
)
# result.cue_path / result.target_path    → [(x,y), ...]
# result.collision_events                 → [CollisionEvent, ...]
# result.wall_events                      → [WallEvent, ...]
# result.pocket_sunk                     → bool
# result.pocket_sunk_ball                → "cue" | "target" | None
```

### 設計原則

- 速度單位：mm/s，長度單位：mm
- `RESTITUTION = 0.95`（初始值，來自撞球檯文獻）
- 未來透過 `shot_database` 實際數據回推修正
- 不引入牆壁穿透修正——用「沿反彈路徑行走」概念
- `dt = 10ms`：球速 1000mm/s 每步移動 10mm（不到一個球徑）

---

## 通訊協定

**Port**: `5005` | **格式**: JSON + `\n` 結尾（防粘包）

### Windows → WSL

#### 校正（INSTALL 模式）
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

#### 預測結果
```json
{
  "type": "PREDICTION",
  "ghost_pixel":  [gu, gv],
  "robot_pixel": [ru, rv],
  "is_reachable": true,
  "angle":       45.2
}
```

#### 開球結果
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

## 執行流程

```
1. WSL: python wsl/main.py
   └─▶ RobotBrain.start() 監聽 :5005

2. Windows: python windows/main.py
   └─▶ HMI() → .run()
   └─▶ SocketClient.connect() → 嘗試連線 WSL

3. INSTALL 模式（四角校正）
   使用者點擊4點（左上→右上→右下→左下）
     → CalibrationHandler.add_point()
     → StateMachine.handle_click() → .get_packet()
     → SocketClient.send()
     → WSL: coord_manager.update_calibration()
     → 模式重置 IDLE，自動進入 TEST

4. BREAK 模式（開球）
   使用者點擊白球位置
     → BreakHandler.add(u, v)
     → SocketClient.send()
     → WSL: break_module.compute_break()
     → striker.execute(angle=90°, stroke=MAX)
     → 回應 BREAK_RESULT

5. TEST 模式（模擬擊球）
   使用者依序點擊：TARGET_BALL → CUE_BALL
     → ShotDispatcher.add()
     → SocketClient.send()
     → WSL: robot_brain._handle_manual()
         → _find_nearest_pocket_name() 動態比對6口袋
         → coord_manager.pixel_to_mm() × 3
         → strategy_module.compute_shot(obstacles=[...])
         → bank_shot_planner.plan_bank_shot()
     → 回應 PREDICTION
     → HMI._draw_prediction() 繪製 ghost ball + 擊球線

   互動：
     · 點擊口袋 → 重新試算
     · 拖曳任一球 → 即時更新路線（task_id=9999）

6. COMPETE 模式（自動視覺）
   VisionBridge 接入狀態機
     → vision_bridge.capture_and_process()
     → vision_pipeline.get_obstacles()
     → robot_brain.compute_shot(obstacles=[...])
     → 自動擊球（待實作）
```

---

## 座標系定義

```
球檯外框：1200 × 630 mm（含庫邊）
手臂原點 (0,0)：長邊中點，底座貼齊邊緣
X軸：[-600, +600]
Y軸：[0, 630]

⚠️ 外框含庫邊，內部 playable area 會更小
   口袋位於庫邊內側，座標需由「洞口直徑」+「庫邊夾角」推算

pixel_to_mm:  像素 (u,v) → 手臂mm (arm_x, arm_y)
mm_to_pixel:  手臂mm (arm_x, arm_y) → 像素 (u,v)
```

---

## 待辦追蹤

> 更新：2026-05-07｜71 tests ✅

| # | 項目 | 優先級 | 說明 |
|---|------|--------|------|
| 1 | Ghost Ball D 偏移 | ✅ 已完成 | G = T + normalize(P-T) × D |
| 2 | 擊球後多餘點擊修復 | ✅ 已完成 | `_shot_sent` flag + 球桌外重置 |
| 3 | Bank Shot Planner | ✅ 已完成 | 鏡像法計算4條庫邊反彈點，32 tests ✅ |
| 4 | 視覺 Phase 1 核心 | ✅ 已完成 | Hue/Orange/maroon 分類修復、confidence、VisionBridge |
| 5 | Vision Unit Tests | ✅ 已完成 | 14/14 tests ✅ |
| 6 | 物理模組 collision + trajectory | ✅ 已完成 | 25 tests ✅ |
| 7 | 校正系統（顏色/球形 + VIEW）| ✅ 已完成 | COLOR_CALIB + SHAPE_CALIB + COLOR_VIEW + SHAPE_VIEW，lazy import + 資源隔離，YAML 持久化 |
| 8 | COMPETE 模式狀態機整合 | 🔴 高 | `state_machine.py` + VisionBridge 串接 |
| 9 | HMI 相機捕獲 | 🔴 高 | Tkinter 定時 polling 或事件驅動 |
| 10 | 真實相機測試 | 🔴 高 | 720p USB camera 實測 |
| 11 | 口袋真實 mm 座標 | 🔴 高 | `strategy_module.POCKETS` 硬編碼，需實地測量 |
| 12 | WSL IP 更新 | 🔴 高 | `windows/config.py` 的 `SOCKET_HOST` 待確認 |
| 13 | striker_bridge Arduino | 🟡 中 | 實機擊球控制（目前 MOCK 模式）|
| 14 | 策略學習層 | 🟢 低 | 貝氏估計 / 強化學習權重 |

---

## 策略藍圖

### Phase 1：幾何優先（當前 ✅）

- 單一路徑計算（Ghost Ball）
- 6 口袋各自獨立計算

### Ghost Ball 演算法

```
已知：白球 C (cx, cy)、目標球 T (tx, ty)、口袋 P (px, py)
目標：找到 Ghost Ball G 位置，驗證擊球路線

1. 計算方向向量
   dir = normalize(T - P)           # 從口袋指向目標球
   gx = tx + dir.x × D              # D = 球徑 38mm
   gy = ty + dir.y × D
   G = T + normalize(P - T) × D     # G 在目標球前方（口袋方向）

2. 驗證 T 在口袋範圍內
   dist(T, P) < POCKET_RADIUS + BALL_RADIUS   # 否則不可能進袋

3. 擊球方向（dot product）— 區分 direct / bank，不禁止任何方向
   dot = (C→G 方向) · (G→T 方向)
   dot > 0 → 擊中 Ghost 前端（direct shot，白球在 G 這側）
   dot < 0 → 擊中 Ghost 尾端（bank shot，白球在 G 另一側繞過來）

4. 第一個碰到的球（障礙球判斷）
   從 C 到 G 的路徑上，白球第一個碰到的球是誰？
   → 求路徑上每個障礙球 O 與線段 [C, G] 的交點
   → 如果交點存在且在 G 之前 → O 是第一個碰到的球
   → 如果第一個碰到的不是 G 本身 → 路徑無效，換 direct/bank 或放棄

5. 庫邊約束（direct shot）
   直線 [C, G] 不能穿越 felt 邊界
   → 與邊界求交：交點在線段內部（非延長線）→ 阻斷

6. 銀行球（Bank Shot）
   M = reflect(T, rail)             # 目標球對庫邊做鏡像
   直線 [C, M] 與庫邊的交點 = 反彈點 B
   驗證 B 在庫邊有效區間（去除角落緩衝）
   擊球線：C → B → reflect(B, rail) → T → P
   驗證：整條路徑無障礙

7. 選擇最佳策略
   direct 可達 → direct
   direct 被阻但 bank 可達 → bank（雙條件 trigger）
   兩者都不行 → 回傳失敗（is_reachable = false）
```

**備註**：
- G 在 T 和口袋之間（不是 T 的後方）
- 步驟 3 的 dot 不是禁止條件，只是用來區分 direct / bank shot
- 步驟 4 的邏輯是「誰第一個被撞」，不是「垂直距離小於 threshold」
- 障礙球半徑用 `×1.5` 緩衝（考慮球半徑疊加）
- Bank shot 雙條件 trigger：Condition A (C→G blocked) OR Condition B (T→P blocked)

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

## 參數同步

| 參數 | 值 | 說明 |
|------|-----|------|
| 球檯尺寸 | 1200×630 mm | |
| 球徑 | 38 mm | D = BALL_DIAMETER |
| 洞口徑 | 50 mm | |
| 手臂 OFFSET_X | 600 mm | 長邊中點對齊 |
| 手臂最大半徑 | 750 mm | |
| 固定擊球長度 | 200 mm | |
| 安全間隙 | 80 mm | |
| Ghost Ball 偏移量 | D（38mm） | G = T + normalize(P-T) × D |
| RESTITUTION | 0.95 | 彈性係數（初始值） |
| 模擬步長 | 10 ms | dt_ms |
