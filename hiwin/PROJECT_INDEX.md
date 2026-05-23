# HIWIN RA605 Pool Robot — Project Node Framework

**Created**: 2026-05-23
**Status**: 🟡 initializing
**Main Agent**: Hermes Researcher (黑皮)

---

## 目標

將 HIWIN RA605 9-Ball 撞球機器人的軟體系統拆解為節點化架構，
每個 node 是封閉的上下文單元，subagent 依賴 context.md 執行，不需主 agent 持續帶路。

---

## Node Map

```
node_vision ──→ node_strategy ──→ node_hardware
                    ↑
              node_physics（驗證）
                    ↑
              node_integration（協調）
```

---

## 節點狀態

| Node | 模組 | 狀態 | 輸出 |
|------|------|------|------|
| node_vision | `windows/control/ball_identifier.py` + `vision_pipeline.py` | ✅ 完成 | `balls`, `obstacles` |
| node_strategy | `windows/brain/strategy_module.py` + `bank_shot_planner.py` | ✅ 完成 | `ghost`, `robot_tcp`, `type` |
| node_physics | `physics/trajectory.py` + `collision.py` | ✅ 完成 | `TrajectoryResult`, `chain_simulate` |
| node_hardware | `windows/brain/hiwin_arm.py` + `striker_bridge.py` | 🔍 檢查中 | `execute_shot()` |
| node_integration | `windows/main.py` + `hmi.py` + `state_machine.py` | 🔄 遷移中 | 單一進程架構 |

## 今日目標（2026-05-23）：Windows-Only 重構

**目標**：移除 WSL 依賴，`windows/main.py` 同時啟動 HMI + RobotBrain

### node_integration 工作清單
1. ✅ `windows/main.py` — 新增 RobotBrain 啟動
2. ⏳ `hmi.py` — 接收 brain injection，移除 socket_client
3. ⏳ `state_machine.py` — 直接 call brain API
4. ⏳ `socket_client.py` — 移除

---

## 今日完成（2026-05-23）

### node_physics — advance_count bug ✅ 修復
- **問題**：`chain_simulate` while 迴圈先檢查 `spd < 0.5` 再 skip advance，損失最後一輪
- **修復**：`trajectory.py:622-632` 改為先 advance 再檢查停止
- **結果**：advance_count 1247 → **2000**（一致），stop position 差距 35mm → **< 5mm**
- **驗證**：10/10 PASS ✅

### node_strategy — obstacles 整合 ✅ 完成
- **`wsl/robot_brain._handle_manual`**：已呼叫 `compute_shot(obstacles=[...])`
- **protocol.py**：新增 `TYPE_OTHER_BALL` 定義
- **障礙物格式**：確認與 `vision_pipeline.get_obstacles()` 一致
- **驗證**：32/32 PASS ✅

---

## 已知問題（委派依據）

---

## Context Compression 安全閥

當 LLM context 被壓縮：
1. 讀 `PROJECT_INDEX.md` → 確認所有 node 進度
2. 依賴順序：`node_vision` → `node_strategy` → `node_hardware`
3. `node_physics` 是驗證層，可獨立執行
4. 維修時：spawn 修復 agent → 指向對應 node 資料夾

---

## 筆記

- 2026-05-16：確認 Windows-Only 架構（移除 WSL）
- 物理模組位置：`~/Desktop/special_topic/physics/`（與 hiwin 平行的獨立 repo）
- HIWIN RA605：TCP/IP `192.168.50.200:4000`
- Arduino Striker：`COM3, 9600 baud`，指令 `goto {dist}`

---

## 下一步

1. ✅ 建立 node 結構（完成）
2. 🔄 node_physics：修復 advance_count bug
3. 🔄 node_strategy：確認 bank shot 整合
4. ⏳ node_hardware：實現 execute_shot
5. ⏳ node_integration：串接所有 node