# Node: node_physics

**父節點**: —  
**子節點**: node_strategy（驗證輸出）  
**創建日期**: 2026-05-23

---

## 職責

物理軌跡模擬引擎，負責：
- 單球停止預測（`predict_single`）
- 多球碰撞鏈式模擬（`chain_simulate`）
- 庫邊反彈 + 進袋判定

---

## 邊界

**負責**:
- 摩擦損耗（ROLLING_FRICTION）
- 球-球彈性碰撞（RESTITUTION）
- 庫邊反射（WallHit 記錄）
- 進袋偵測（is_in_pocket）

**不負責**:
- 策略決策（Ghost Ball 由 node_strategy 提供）
- 硬體控制
- 視覺辨識

---

## 輸入格式

```python
# 來源：node_strategy 的驗證需求
predict_single(x, y, vx, vy, obstacles, max_steps=2000)
chain_simulate(primary_x, primary_y, primary_vx, primary_vy, balls, max_steps=2000)

# 障礙球格式：[(x, y), ...] 或 [BallState, ...]
```

---

## 輸出格式

```python
# predict_single 回傳
StopPrediction:
  - stop_x, stop_y: 停止位置（mm）
  - total_dist: 累計移動距離（mm）
  - wall_bounces: 庫邊反彈次數
  - collision_before_stop: 碰撞發生與否
  - advance_count: 執行的 advance 步數

# chain_simulate 回傳
TrajectoryResult:
  - cue_path: [(x,y), ...]
  - target_path: [(x,y), ...]
  - wall_hits: [WallHit, ...]
  - collision_events: [CollisionEvent, ...]
  - pocket_sunk: bool
  - pocket_sunk_ball: "cue" | "target" | None
```

---

## 觸發條件

- node_strategy 需要驗證「白球能否擊中目標球」時呼叫
- 獨立測試：`python -m pytest tests/test_physics_validation.py`

---

## 錯誤處理

- **失敗時找誰**: 回歸主 agent（Hermes Researcher）
- **重試次數**: 3 次
- **備用方案**: 若 chain_simulate 失敗，predict_single 可獨立使用

---

## 已知 Bug（委派維修依據）

**advance_count 差距**（2026-05-09 已確認）:
- `predict_single`: stop=(819.8,315), dist=18980mm, bounces=17, advance_count=**2000**
- `chain_simulate`: stop=(784.6,315), dist=14615mm, bounces=13, advance_count=**1247**
- 差距：35mm / 753 步未執行

**根因**：`trajectory.py:619-640` while 迴圈中，`spd < 0.5` 時先 skip advance 才設 any_moving=False，損失最後一輪

**正確邏輯**（predict_single 行 177-180）：
```python
# advance → 檢查 spd<0.5 → break（advance 後才檢查，輸出 advanced 後位置）
```

**錯誤邏輯**（chain_simulate 行 629-632）：
```python
# 先檢查 spd<0.5 → skip advance → any_moving=False（損失最後一輪）
```

**修復方向**：改為「先 advance，紀錄 new_spd，再根據 new_spd 判斷是否停止」

---

## 驗證方法

```bash
cd ~/Desktop/special_topic/hiwin
python -m pytest tests/test_physics_validation.py -v
# 目標：predict_single 和 chain_simulate 的 advance_count 差距 < 50 步
```